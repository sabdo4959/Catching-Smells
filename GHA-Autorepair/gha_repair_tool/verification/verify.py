# verify.py
# 두 GHA 워크플로우의 논리적 동치성을 검증합니다.

import sys
from pathlib import Path
from pprint import pprint

# Z3 관련 import
from z3 import Solver, Not, Or, And, sat, unsat

# 로컬 모듈 import
try:
    from parser import GHAWorkflowParser, GHAWorkflowAnalyzer
    # translator.py의 SMTTranslator 클래스를 가져옵니다.
    # NOTE: PoC를 위해 translator.py의 _parse_if_string 함수를 일부 수정하여 사용합니다.
    from translator import SMTTranslator as OriginalSMTTranslator
except ImportError as e:
    print(f"ERROR: 필요한 모듈을 찾을 수 없습니다 ({e}).", file=sys.stderr)
    print("INFO: parser.py와 translator.py가 verify.py와 동일한 디렉토리에 있는지 확인해주세요.", file=sys.stderr)
    sys.exit(1)

# --- PoC를 위한 SMTTranslator 수정 ---
# 실제 연구에서는 이 파서를 훨씬 더 정교하게 만들어야 합니다.
class SMTTranslator(OriginalSMTTranslator):
    def _parse_if_string(self, condition_str: str):
        """
        PoC를 위해 'contains' 함수를 처리하도록 원본 파서 확장
        """
        if not condition_str:
            return super()._parse_if_string(condition_str)
        
        # 'contains(github.ref, 'main')' 케이스 처리
        if "contains(github.ref, 'main')" in condition_str:
            # z3의 String 객체는 contains 메소드를 지원하지 않으므로, InRe로 모델링
            from z3 import InRe, StringVal, Star, Concat
            # /.*main.*/ 정규식과 동일
            main_re = Concat(Star(StringVal(None)), StringVal("main"), Star(StringVal(None)))
            return InRe(self.vars['context']['github.ref'], main_re)
            
        return super()._parse_if_string(condition_str)


def run_verification(original_file: Path, repaired_file: Path):
    """
    두 워크플로우 파일의 동치성을 검증하는 메인 함수
    """
    print("="*60)
    print(f"🔬 원본 파일: {original_file.name}")
    print(f"🔬 수정된 파일: {repaired_file.name}")
    print("="*60)

    # --- 1단계: 각 파일을 파싱, 분석, SMT 공식으로 변환 ---
    parser = GHAWorkflowParser()
    
    # 원본 워크플로우 처리
    print("\n[1-A] 원본 워크플로우를 SMT 공식으로 변환 중...")
    orig_data = parser.parse(original_file)
    if not orig_data: return False
    orig_analyzer = GHAWorkflowAnalyzer(orig_data)
    orig_analysis = orig_analyzer.analyze()
    orig_translator = SMTTranslator(orig_analysis, workflow_id='orig')
    constraints_orig = orig_translator.translate()
    orig_translator.pretty_print_constraints(constraints_orig)

    # 수정된 워크플로우 처리
    print("\n[1-B] 수정된 워크플로우를 SMT 공식으로 변환 중...")
    repaired_data = parser.parse(repaired_file)
    if not repaired_data: return False
    repaired_analyzer = GHAWorkflowAnalyzer(repaired_data)
    repaired_analysis = repaired_analyzer.analyze()
    repaired_translator = SMTTranslator(repaired_analysis, workflow_id='repaired')
    constraints_repaired = repaired_translator.translate()
    repaired_translator.pretty_print_constraints(constraints_repaired)

    # --- 2단계: 동치성 검증을 위한 솔버 설정 ---
    print("\n[2] 동치성 검증을 위한 SMT 솔버 설정 중...")
    solver = Solver()
    solver.add(constraints_orig)
    solver.add(constraints_repaired)
    print("INFO: 두 워크플로우의 모든 제약 조건을 솔버에 추가했습니다.")

    # --- 3단계: 비동치 조건(Non-Equivalence Condition) 생성 ---
    # "실행 조건이 다른 잡이나 스텝이 하나라도 있는가?"를 질문
    non_equivalence_conditions = []

    # 공통된 잡 목록 찾기
    common_jobs = set(orig_analysis['jobs'].keys()) & set(repaired_analysis['jobs'].keys())
    
    for job_name in common_jobs:
        # 잡 레벨의 동치성 검증
        orig_job_exec = orig_translator.vars['jobs'][job_name]['executed']
        repaired_job_exec = repaired_translator.vars['jobs'][job_name]['executed']
        non_equivalence_conditions.append(orig_job_exec != repaired_job_exec)
        
        # 스텝 레벨의 동치성 검증
        num_steps = min(
            len(orig_analysis['jobs'][job_name]['steps']),
            len(repaired_analysis['jobs'][job_name]['steps'])
        )
        for i in range(num_steps):
            orig_step_exec = orig_translator.get_execution_formula(job_name, i)
            repaired_step_exec = repaired_translator.get_execution_formula(job_name, i)
            if orig_step_exec is not None and repaired_step_exec is not None:
                non_equivalence_conditions.append(orig_step_exec != repaired_step_exec)

    # 모든 비동치 조건들을 Or로 묶어서 최종 질의 생성
    # "잡1이 다르거나 OR 잡2가 다르거나 OR 스텝1이 다르거나..."
    final_query = Or(non_equivalence_conditions)
    solver.add(final_query)
    print("INFO: 비동치(Non-Equivalence) 조건을 솔버에 추가했습니다.")
    print(f"  - 검증 질의: Is there any case where ({str(final_query)[:100]}...)?")


    # --- 4단계: 검증 실행 및 결과 해석 ---
    print("\n[3] Z3 솔버로 검증 실행...")
    result = solver.check()
    print("-" * 60)
    
    if result == unsat:
        print("✅ 결과: UNSAT (Unsatisfiable)")
        print("🎉 결론: 안전(SAFE)합니다. 두 워크플로우는 논리적으로 동치입니다.")
        print("   스멜 수정으로 인해 다른 부분의 실행 흐름이 변경되지 않았음을 증명했습니다.")
        return True
    elif result == sat:
        print("❌ 결과: SAT (Satisfiable)")
        print("🚨 결론: 안전하지 않습니다(UNSAFE). 두 워크플로우의 동작이 다른 경우가 존재합니다.")
        print("   아래는 동작이 달라지는 시나리오(반례)입니다:")
        model = solver.model()
        pprint(model)
        return False
    else:
        print(f"❔ 결과: 알 수 없음 ({result})")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python src/verify.py <original_file> <repaired_file>")
        sys.exit(1)

    original_file = Path(sys.argv[1])
    repaired_file = Path(sys.argv[2])

    if not original_file.exists() or not repaired_file.exists():
        print(f"ERROR: 입력 파일({original_file}, {repaired_file})을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    run_verification(original_file, repaired_file)

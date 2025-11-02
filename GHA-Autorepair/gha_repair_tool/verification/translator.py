# translator.py
# 분석된 워크플로우 구조를 Z3 논리 공식으로 변환하고 출력합니다.

import sys
from pathlib import Path
from pprint import pprint

# Z3 관련 import
from z3 import (And, Bool, BoolVal, Datatype, Not, Or, Solver, String,
                StringVal, sat, If, Const)

# --- 로컬 파서 모듈 import ---
# 이 스크립트를 실행하기 전에, 이전 단계에서 만든 parser.py가 동일한 디렉토리에 있어야 합니다.
try:
    from parser import GHAWorkflowParser, GHAWorkflowAnalyzer
except ImportError:
    print("ERROR: 'parser.py'를 찾을 수 없습니다. translator.py와 동일한 디렉토리에 있는지 확인해주세요.", file=sys.stderr)
    sys.exit(1)


# GitHub Actions의 잡 상태를 표현하기 위한 Z3 Enum/Datatype
Status = Datatype('Status')
Status.declare('success')
Status.declare('failure')
Status.declare('skipped')
Status.declare('cancelled')
Status = Status.create()

class SMTTranslator:
    """
    GHAWorkflowAnalyzer의 분석 결과를 Z3 논리 공식으로 변환합니다.
    """
    def __init__(self, analysis_result: dict, workflow_id: str):
        """
        번역기를 초기화합니다.

        Args:
            analysis_result: GHAWorkflowAnalyzer.analyze()의 반환값.
            workflow_id: 여러 워크플로우를 비교하기 위한 고유 식별자 (예: 'orig', 'repaired').
        """
        self.analysis = analysis_result
        self.workflow_id = workflow_id
        
        # --- Z3 변수들을 저장할 딕셔너리 ---
        self.vars = {
            'context': {}, # github.ref 등 컨텍스트 변수
            'jobs': {},    # 각 잡의 실행 여부 및 상태 변수
            'steps': {}    # 각 스텝의 실행 여부 변수
        }
        self._create_context_variables()
        self._create_workflow_variables()

    def _get_var_name(self, *parts):
        """충돌을 피하기 위해 변수 이름에 워크플로우 ID를 접두사로 붙입니다."""
        return f"{self.workflow_id}_{'_'.join(parts)}"

    def _create_context_variables(self):
        """워크플로우 실행에 영향을 주는 GitHub 컨텍스트 변수를 선언합니다."""
        self.vars['context'] = {
            'github.ref': String('github.ref'),
            'github.event_name': String('github.event_name'),
            'github.event.pull_request.draft': Bool('github.event.pull_request.draft'),
        }

    def _create_workflow_variables(self):
        """워크플로우의 각 잡/스텝에 대한 Z3 변수를 미리 생성합니다."""
        for job_name in self.analysis['jobs']:
            # 잡의 실행 여부 (Bool)와 최종 상태 (Enum)
            self.vars['jobs'][job_name] = {
                'executed': Bool(self._get_var_name('job', job_name, 'executed')),
                'status': Const(self._get_var_name('job', job_name, 'status'), Status)
            }
            # 각 스텝의 실행 여부 (Bool)
            for i, _ in enumerate(self.analysis['jobs'][job_name]['steps']):
                step_id = f"step_{i}"
                self.vars['steps'][f"{job_name}_{step_id}"] = {
                    'executed': Bool(self._get_var_name('job', job_name, step_id, 'executed'))
                }

    def translate(self) -> list:
        """
        전체 워크플로우를 분석하여 Z3 제약 조건 리스트를 생성합니다.
        이것이 SMT 솔버에 추가될 최종 논리 공식들입니다.
        """
        constraints = []
        for job_name, job_data in self.analysis['jobs'].items():
            job_precondition = self._get_job_precondition(job_name, job_data)
            
            job_executed_var = self.vars['jobs'][job_name]['executed']
            constraints.append(job_executed_var == job_precondition)

            step_constraints = self._get_step_execution_constraints(job_name, job_data)
            constraints.extend(step_constraints)
            
            job_status_var = self.vars['jobs'][job_name]['status']
            constraints.append(
                If(job_executed_var,
                   job_status_var == Status.success,
                   job_status_var == Status.skipped)
            )
        return constraints

    def _get_job_precondition(self, job_name, job_data):
        """특정 잡이 실행되기 위한 모든 전제 조건을 Z3 논리식으로 반환합니다."""
        needs_conditions = []
        for needed_job_name in job_data['needs']:
            # 'needs'에 명시된 잡이 존재하지 않으면 오류 대신 경고 출력
            if needed_job_name not in self.vars['jobs']:
                print(f"WARNING: Job '{job_name}'의 'needs'에 명시된 '{needed_job_name}' 잡을 찾을 수 없습니다.", file=sys.stderr)
                continue
            needed_job_status = self.vars['jobs'][needed_job_name]['status']
            needs_conditions.append(needed_job_status == Status.success)
        
        if_condition = self._parse_if_string(job_data['if_condition'])
        
        return And(if_condition, *needs_conditions)

    def _get_step_execution_constraints(self, job_name, job_data):
        """특정 잡 내부의 모든 스텝들의 실행 조건을 Z3 제약 조건으로 반환합니다."""
        constraints = []
        job_executed_var = self.vars['jobs'][job_name]['executed']
        previous_steps_succeeded = BoolVal(True)

        for i, step_data in enumerate(job_data['steps']):
            step_id = f"{job_name}_step_{i}"
            step_executed_var = self.vars['steps'][step_id]['executed']
            
            step_if_condition = self._parse_if_string(step_data['if_condition'])
            execution_condition = And(job_executed_var, previous_steps_succeeded, step_if_condition)
            constraints.append(step_executed_var == execution_condition)
            
            previous_steps_succeeded = And(previous_steps_succeeded, step_executed_var)
        return constraints

    def _parse_if_string(self, condition_str: str):
        """
        GHA의 `if` 조건 문자열을 Z3 논리식으로 파싱합니다.
        NOTE: 이 함수는 PoC를 위한 단순한 버전이며, 실제로는 더 정교한 파서가 필요합니다.
        """
        if not condition_str:
            return BoolVal(True)

        # 공백 및 ${{...}} 제거
        condition_str = condition_str.strip().replace('${{', '').replace('}}', '').strip()

        if condition_str == 'success()':
             return BoolVal(True)
        if condition_str == "github.ref == 'refs/heads/main'":
            return self.vars['context']['github.ref'] == StringVal("refs/heads/main")
        if condition_str == "!github.event.pull_request.draft":
            return Not(self.vars['context']['github.event.pull_request.draft'])

        print(f"WARNING: '{condition_str}' 조건은 파싱할 수 없어 True로 처리합니다.")
        return BoolVal(True)

    def get_execution_formula(self, job_name: str, step_index: int):
        """특정 스텝의 실행 여부를 나타내는 최종 Z3 변수를 반환합니다."""
        step_id = f"{job_name}_step_{step_index}"
        if step_id in self.vars['steps']:
            return self.vars['steps'][step_id]['executed']
        return None

    # === Z3 논리 공식 출력을 위한 신규 메소드 ===
    def pretty_print_constraints(self, constraints: list):
        """
        생성된 Z3 제약 조건 리스트를 사람이 읽기 좋은 형태로 출력합니다.
        """
        print("\n" + "="*20 + " 생성된 Z3 제약 조건 " + "="*20)
        if not constraints:
            print("  (생성된 제약 조건이 없습니다)")
            return
            
        for i, constraint in enumerate(constraints):
            print(f"  [{i+1:02d}] {constraint}")
        print("="*62 + "\n")


# === main 함수: yaml_parser 결과를 받아 SMTTranslator로 실행 ===
def main():
    """
    커맨드라인 인자로 받은 YAML 파일을 파싱하고, Z3 논리 공식으로 변환하여 출력합니다.
    """
    if len(sys.argv) != 2:
        print(f"사용법: python {sys.argv[0]} <yaml_파일_경로>")
        return

    yaml_path = Path(sys.argv[1])
    if not yaml_path.is_file():
        print(f"ERROR: 파일을 찾을 수 없습니다: {yaml_path}", file=sys.stderr)
        return

    # 1. 파싱
    parser = GHAWorkflowParser()
    parsed_data = parser.parse(yaml_path)
    if not parsed_data:
        return

    # 2. 분석
    analyzer = GHAWorkflowAnalyzer(parsed_data)
    analysis_result = analyzer.analyze()
    
    print("\n--- 분석 결과 (구조화된 딕셔너리) ---")
    pprint(analysis_result)
    print("------------------------------------")

    # 3. Z3 논리 공식으로 변환
    # workflow_id는 임의로 'main' 사용
    translator = SMTTranslator(analysis_result, workflow_id='main')
    constraints = translator.translate()
    
    # 4. 생성된 논리 공식 출력 (핵심 추가 기능)
    translator.pretty_print_constraints(constraints)
    
    # 5. SMT 솔버로 실행 가능성(satisfiability) 확인
    solver = Solver()
    solver.add(constraints)
    result = solver.check()
    print(f"SMT Solver 결과: {result}")
    if result == sat:
        print("\n--- 가능한 실행 시나리오 (하나의 모델) ---")
        print(solver.model())
        print("------------------------------------")


if __name__ == "__main__":
    main()

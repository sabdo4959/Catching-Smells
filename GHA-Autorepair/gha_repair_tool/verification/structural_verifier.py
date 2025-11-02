# structural_verifier.py
# 두 GHA 워크플로우의 AST를 비교하여 구조적 동치성을 검증합니다.

import sys
from pathlib import Path
from pprint import pprint
from deepdiff import DeepDiff

# 로컬 파서 모듈 import
try:
    from parser import GHAWorkflowParser
except ImportError:
    print("ERROR: 'parser.py'를 찾을 수 없습니다. 이 스크립트와 동일한 디렉토리에 있는지 확인해주세요.", file=sys.stderr)
    sys.exit(1)

def verify_structural_equivalence(original_file: Path, repaired_file: Path):
    """
    두 워크플로우의 구조적 동치성을 검증합니다.
    특히 스텝 순서, 잡 의존성, 워크플로우 구조의 무결성을 중점적으로 검사합니다.

    Args:
        original_file: 원본 워크플로우 파일 경로.
        repaired_file: 수정된 워크플로우 파일 경로.
    
    Returns:
        bool: 구조적으로 안전한지 여부
    """
    print("="*60)
    print(f"🔬 원본 파일: {original_file.name}")
    print(f"🔬 수정된 파일: {repaired_file.name}")
    print("="*60)

    # 1. 두 파일을 파싱하여 AST 생성
    parser = GHAWorkflowParser()
    ast_orig = parser.parse(original_file)
    ast_repaired = parser.parse(repaired_file)

    if not ast_orig or not ast_repaired:
        print("ERROR: 파일 파싱에 실패하여 검증을 중단합니다.", file=sys.stderr)
        return False

    # 1-1. 세부 구조 검증 수행
    structure_issues = []
    
    # 잡 순서 검증
    job_order_issue = _verify_job_order(ast_orig, ast_repaired)
    if job_order_issue:
        structure_issues.append(job_order_issue)
    
    # 스텝 순서 검증 (각 잡별로)
    step_order_issues = _verify_step_orders(ast_orig, ast_repaired)
    structure_issues.extend(step_order_issues)
    
    # 의존성 구조 검증
    dependency_issue = _verify_dependencies(ast_orig, ast_repaired)
    if dependency_issue:
        structure_issues.append(dependency_issue)
    
    # 워크플로우 트리거 검증
    trigger_issue = _verify_triggers(ast_orig, ast_repaired)
    if trigger_issue:
        structure_issues.append(trigger_issue)

    # 2. 기본 DeepDiff 비교 (기존 로직 유지)
    # 예상되는 '안전한' 변경 정의 (Smell 수정 패턴)
    exclude_regex_paths = [
        # Smell 1: Using latest runner (e.g., ubuntu-latest -> ubuntu-22.04)
        r"root\['jobs'\]\['[\w-]+'\]\['runs-on'\]",
        
        # Smell 2: Using outdated actions (e.g., actions/checkout@v2 -> v4)
        r"root\['jobs'\]\['[\w-]+'\]\['steps'\]\[\d+\]\['uses'\]",

        # Smell 3: GITHUB_TOKEN permissions
        r"root\['jobs'\]\['[\w-]+'\]\['permissions'\]",
        r"root\['permissions'\]",

        # Smell 5: Forked PR action execution (if condition은 세부 검증에서 처리)
        r"root\['jobs'\]\['[\w-]+'\]\['if'\]",

        # Smell 6: No job timeout
        r"root\['jobs'\]\['[\w-]+'\]\['timeout-minutes'\]",
        r"root\['jobs'\]\['[\w-]+'\]\['steps'\]\[\d+\]\['timeout-minutes'\]",

        # Smell 7: Duplicate action execution on new commits (concurrency는 안전한 추가)
        r"root\['concurrency'\]",

        # 기타 안전한 변경: 스텝에 이름 추가/변경 등
        r"root\['jobs'\]\['[\w-]+'\]\['steps'\]\[\d+\]\['name'\]",
        
        # GitHub Actions deprecated 구문 수정 관련 (run 명령어는 블랙박스)
        r"root\['jobs'\]\['[\w-]+'\]\['steps'\]\[\d+\]\['run'\]",
        
        # workflow_dispatch input 타입 수정 (str -> string)
        r"root\['on'\]\['workflow_dispatch'\]\['inputs'\]\['[\w-]+'\]\['type'\]",
    ]

    # DeepDiff를 사용하여 두 AST 비교
    diff = DeepDiff(
        ast_orig,
        ast_repaired,
        ignore_order=False,  # 스텝 순서는 중요하므로 순서를 무시하지 않음
        exclude_regex_paths=exclude_regex_paths
    )

    # 3. 통합 결과 분석 및 출력
    print("\n[1] 세부 구조 검증 결과:")
    print("-" * 40)
    
    critical_issues = []
    warning_issues = []
    
    for issue in structure_issues:
        # 진짜 구조적 문제들: 스텝/잡 추가/삭제, 순서 변경, 실행 타입 변경, 트리거 변경
        if issue['type'] in [
            'job_order_changed', 'job_added', 'job_removed',
            'step_count_changed', 'step_type_changed', 'step_execution_type_changed',
            'job_dependencies_changed', 'trigger_events_changed', 'trigger_structure_changed', 'trigger_config_changed',
            'step_action_changed', 'step_id_changed'
        ]:
            critical_issues.append(issue)
        else:
            warning_issues.append(issue)
    
    if critical_issues:
        print("🚨 심각한 구조적 문제:")
        for issue in critical_issues:
            print(f"  - {issue['description']}")
            if 'original' in issue and 'repaired' in issue:
                print(f"    원본: {issue['original']}")
                print(f"    수정: {issue['repaired']}")
    
    if warning_issues:
        print("⚠️  주의사항:")
        for issue in warning_issues:
            print(f"  - {issue['description']}")
    
    if not structure_issues:
        print("✅ 세부 구조 검증: 모든 검사 통과")

    print("\n[2] DeepDiff 구조적 동치성 검증 결과:")
    print("-" * 40)

    if not diff:
        print("✅ DeepDiff 검증: 구조적으로 동치함")
        print("   (무시하기로 한 경로를 제외하고 구조적 차이가 없습니다)")
    else:
        print("❌ DeepDiff 검증: 예상치 못한 구조적 변경 발견")
        print("\n   ▼ 발견된 차이점 상세 정보 ▼")
        pprint(diff)

    # 4. 최종 판정
    print("\n" + "="*60)
    final_safe = len(critical_issues) == 0 and not diff
    
    if final_safe:
        print("🎉 최종 결론: 구조적으로 안전(SAFE)합니다.")
        print("   복구된 워크플로우가 원본의 구조와 순서를 잘 유지하고 있습니다.")
    else:
        print("🚨 최종 결론: 구조적으로 안전하지 않습니다(UNSAFE).")
        if critical_issues:
            print(f"   - 심각한 구조적 문제: {len(critical_issues)}개")
        if diff:
            print("   - 예상치 못한 구조적 변경 감지")
    
    print("="*60)
    return final_safe


def _verify_job_order(ast_orig, ast_repaired):
    """
    잡의 순서가 유지되는지 검증합니다.
    """
    try:
        orig_jobs = list(ast_orig.get('jobs', {}).keys()) if ast_orig.get('jobs') else []
        repaired_jobs = list(ast_repaired.get('jobs', {}).keys()) if ast_repaired.get('jobs') else []
        
        if orig_jobs != repaired_jobs:
            return {
                "type": "job_order_changed",
                "original_order": orig_jobs,
                "repaired_order": repaired_jobs,
                "description": "잡의 순서가 변경되었습니다."
            }
        return None
    except Exception as e:
        return {
            "type": "job_order_check_error",
            "error": str(e),
            "description": "잡 순서 검증 중 오류가 발생했습니다."
        }


def _verify_step_orders(ast_orig, ast_repaired):
    """
    각 잡 내의 스텝 순서가 유지되는지 검증합니다.
    스텝의 추가/삭제/순서 변경 등 진짜 구조적 변경에 집중합니다.
    """
    issues = []
    try:
        orig_jobs = ast_orig.get('jobs', {})
        repaired_jobs = ast_repaired.get('jobs', {})
        
        for job_name in orig_jobs.keys():
            if job_name not in repaired_jobs:
                issues.append({
                    "type": "job_removed",
                    "job": job_name,
                    "description": f"잡 '{job_name}'이 제거되었습니다."
                })
                continue
                
            orig_steps = orig_jobs[job_name].get('steps', [])
            repaired_steps = repaired_jobs[job_name].get('steps', [])
            
            # 스텝 수 변경 - 이것은 심각한 구조적 변경
            if len(orig_steps) != len(repaired_steps):
                issues.append({
                    "type": "step_count_changed",
                    "job": job_name,
                    "original_count": len(orig_steps),
                    "repaired_count": len(repaired_steps),
                    "description": f"잡 '{job_name}'의 스텝 수가 변경되었습니다 ({len(orig_steps)} → {len(repaired_steps)})."
                })
                
                # 스텝 수가 다르면 더 이상 비교할 수 없음
                continue
            
            # 스텝 순서 및 핵심 구조 검증 (수가 같은 경우만)
            for i, (orig_step, repaired_step) in enumerate(zip(orig_steps, repaired_steps)):
                # 스텝의 구조적 무결성 검사
                step_issues = _compare_step_structure(orig_step, repaired_step, job_name, i)
                issues.extend(step_issues)
                
                # 스텝의 기본 구조가 유지되는지 확인 (uses vs run)
                orig_step_type = _get_step_type(orig_step)
                repaired_step_type = _get_step_type(repaired_step)
                
                if orig_step_type != repaired_step_type:
                    issues.append({
                        "type": "step_type_changed",
                        "job": job_name,
                        "step_index": i,
                        "original_type": orig_step_type,
                        "repaired_type": repaired_step_type,
                        "description": f"스텝 {i+1}의 타입이 변경되었습니다 ({orig_step_type} → {repaired_step_type})."
                    })
        
        # 새로 추가된 잡이 있는지 확인
        for job_name in repaired_jobs.keys():
            if job_name not in orig_jobs:
                issues.append({
                    "type": "job_added", 
                    "job": job_name,
                    "description": f"잡 '{job_name}'이 새로 추가되었습니다."
                })
                
    except Exception as e:
        issues.append({
            "type": "step_order_check_error",
            "error": str(e),
            "description": "스텝 순서 검증 중 오류가 발생했습니다."
        })
    
    return issues


def _get_step_type(step):
    """
    스텝의 기본 타입을 반환합니다 (구조적 분류용).
    """
    if 'uses' in step:
        return 'action'
    elif 'run' in step:
        return 'command'
    else:
        return 'unknown'


def _compare_step_structure(orig_step, repaired_step, job_name, step_index):
    """
    개별 스텝의 구조적 무결성을 검증합니다.
    run 명령어 내용은 블랙박스로 처리하고, 구조적 변경에만 집중합니다.
    """
    issues = []
    
    # 구조적으로 중요한 속성들 (순서와 실행 흐름에 영향을 주는 것들)
    critical_fields = ['uses', 'if', 'id']
    
    for field in critical_fields:
        orig_value = orig_step.get(field)
        repaired_value = repaired_step.get(field)
        
        if field == 'uses' and orig_value and repaired_value:
            # 액션 버전 업데이트는 허용 (예: v2 -> v4)
            if not _is_safe_action_update(orig_value, repaired_value):
                issues.append({
                    "type": "step_action_changed",
                    "job": job_name,
                    "step_index": step_index,
                    "field": field,
                    "original": orig_value,
                    "repaired": repaired_value,
                    "description": f"스텝의 액션이 안전하지 않게 변경되었습니다."
                })
        elif field == 'if' and orig_value != repaired_value:
            # if 조건 변경은 일부 smell 수정에서 허용
            if not _is_safe_condition_change(orig_value, repaired_value):
                issues.append({
                    "type": "step_condition_changed",
                    "job": job_name,
                    "step_index": step_index,
                    "field": field,
                    "original": orig_value,
                    "repaired": repaired_value,
                    "description": f"스텝의 실행 조건이 안전하지 않게 변경되었습니다."
                })
        elif field == 'id' and orig_value != repaired_value:
            # 스텝 ID 변경은 의존성에 영향을 줄 수 있음
            issues.append({
                "type": "step_id_changed",
                "job": job_name,
                "step_index": step_index,
                "field": field,
                "original": orig_value,
                "repaired": repaired_value,
                "description": f"스텝의 ID가 변경되어 의존성에 영향을 줄 수 있습니다."
            })
    
    # run 명령어는 블랙박스로 처리 - 내용 변경은 무시
    # 단, run과 uses가 동시에 있거나 둘 다 없는 등의 구조적 문제는 체크
    orig_has_run = 'run' in orig_step
    orig_has_uses = 'uses' in orig_step
    repaired_has_run = 'run' in repaired_step
    repaired_has_uses = 'uses' in repaired_step
    
    # 스텝의 기본 실행 방식이 변경된 경우 (run <-> uses)
    if (orig_has_run and not orig_has_uses) != (repaired_has_run and not repaired_has_uses):
        issues.append({
            "type": "step_execution_type_changed",
            "job": job_name,
            "step_index": step_index,
            "description": f"스텝의 실행 방식이 변경되었습니다 (run <-> uses)."
        })
    
    return issues


def _is_safe_action_update(orig_action, repaired_action):
    """
    액션 업데이트가 안전한지 검증합니다 (예: checkout@v2 -> checkout@v4).
    """
    try:
        # 기본 액션 이름이 같은지 확인
        orig_base = orig_action.split('@')[0] if '@' in orig_action else orig_action
        repaired_base = repaired_action.split('@')[0] if '@' in repaired_action else repaired_action
        
        return orig_base == repaired_base
    except:
        return False


def _is_safe_command_update(orig_command, repaired_command):
    """
    명령어 업데이트가 안전한지 검증합니다.
    GitHub Actions deprecated 구문 수정 등을 허용합니다.
    """
    if not orig_command or not repaired_command:
        return orig_command == repaired_command
    
    # 줄바꿈 문자 정규화 후 비교
    orig_normalized = orig_command.strip()
    repaired_normalized = repaired_command.strip()
    
    if orig_normalized == repaired_normalized:
        return True
    
    # GitHub Actions deprecated 구문 수정 패턴들
    safe_replacements = [
        # ::set-output -> $GITHUB_OUTPUT
        (r'echo\s+::set-output\s+name=(\w+)::(.+)', r'echo\s+"\1=\2"\s+>>\s+\$GITHUB_OUTPUT'),
        # ::add-path -> $GITHUB_PATH
        (r'echo\s+"(.+)"\s+>>\s+\$GITHUB_PATH', r'echo\s+::add-path::(.+)'),
        # ::set-env -> $GITHUB_ENV 
        (r'echo\s+::set-env\s+name=(\w+)::(.+)', r'echo\s+"\1=\2"\s+>>\s+\$GITHUB_ENV'),
    ]
    
    import re
    for old_pattern, new_pattern in safe_replacements:
        if re.search(old_pattern, orig_normalized) and re.search(new_pattern, repaired_normalized):
            return True
        if re.search(new_pattern, orig_normalized) and re.search(old_pattern, repaired_normalized):
            return True
    
    # 주석 제거만 된 경우 (기능적으로 동일)
    orig_no_comments = re.sub(r'#.*$', '', orig_normalized, flags=re.MULTILINE).strip()
    repaired_no_comments = re.sub(r'#.*$', '', repaired_normalized, flags=re.MULTILINE).strip()
    
    if orig_no_comments == repaired_no_comments:
        return True
    
    return False


def _is_safe_condition_change(orig_condition, repaired_condition):
    """
    조건 변경이 안전한지 검증합니다 (포크된 PR 관련 smell 수정 등).
    """
    # None -> 조건 추가는 일반적으로 안전 (보안 강화)
    if orig_condition is None and repaired_condition:
        return True
    
    # 조건 제거는 위험할 수 있음
    if orig_condition and repaired_condition is None:
        return False
    
    # 조건 변경의 경우 더 세밀한 분석이 필요하지만, 현재는 보수적으로 접근
    return orig_condition == repaired_condition


def _verify_dependencies(ast_orig, ast_repaired):
    """
    잡 간의 의존성 구조가 유지되는지 검증합니다.
    """
    try:
        orig_jobs = ast_orig.get('jobs', {})
        repaired_jobs = ast_repaired.get('jobs', {})
        
        for job_name, job_config in orig_jobs.items():
            if job_name not in repaired_jobs:
                continue
                
            orig_needs = job_config.get('needs', [])
            repaired_needs = repaired_jobs[job_name].get('needs', [])
            
            # needs를 리스트로 정규화
            if isinstance(orig_needs, str):
                orig_needs = [orig_needs]
            if isinstance(repaired_needs, str):
                repaired_needs = [repaired_needs]
            
            # 의존성 변경 검사
            if set(orig_needs) != set(repaired_needs):
                return {
                    "type": "job_dependencies_changed",
                    "job": job_name,
                    "original_needs": orig_needs,
                    "repaired_needs": repaired_needs,
                    "description": f"잡 '{job_name}'의 의존성이 변경되었습니다."
                }
        
        return None
    except Exception as e:
        return {
            "type": "dependency_check_error",
            "error": str(e),
            "description": "의존성 검증 중 오류가 발생했습니다."
        }


def _verify_triggers(ast_orig, ast_repaired):
    """
    워크플로우 트리거 구조가 유지되는지 검증합니다.
    """
    try:
        orig_on = ast_orig.get('on', {})
        repaired_on = ast_repaired.get('on', {})
        
        # 트리거가 완전히 다른 타입으로 변경된 경우
        orig_is_simple = isinstance(orig_on, str)
        repaired_is_simple = isinstance(repaired_on, str)
        
        if orig_is_simple != repaired_is_simple:
            return {
                "type": "trigger_structure_changed",
                "original_type": "simple" if orig_is_simple else "complex",
                "repaired_type": "simple" if repaired_is_simple else "complex",
                "description": "트리거 구조가 단순형과 복합형 사이에서 변경되었습니다."
            }
        
        # 둘 다 단순형인 경우
        if orig_is_simple and repaired_is_simple:
            if orig_on != repaired_on:
                return {
                    "type": "trigger_events_changed",
                    "original_events": [orig_on],
                    "repaired_events": [repaired_on],
                    "description": f"트리거 이벤트가 '{orig_on}'에서 '{repaired_on}'로 변경되었습니다."
                }
        
        # 둘 다 복합형인 경우
        elif not orig_is_simple and not repaired_is_simple:
            # 트리거 이벤트 타입이 변경되었는지 확인
            orig_events = set(orig_on.keys()) if isinstance(orig_on, dict) else set()
            repaired_events = set(repaired_on.keys()) if isinstance(repaired_on, dict) else set()
            
            if orig_events != repaired_events:
                return {
                    "type": "trigger_events_changed",
                    "original_events": list(orig_events),
                    "repaired_events": list(repaired_events),
                    "description": f"트리거 이벤트가 {orig_events}에서 {repaired_events}로 변경되었습니다."
                }
            
            # 각 이벤트의 세부 설정이 변경되었는지 확인
            for event in orig_events:
                orig_config = orig_on.get(event, {})
                repaired_config = repaired_on.get(event, {})
                
                # 간단한 비교 (브랜치 설정 등)
                if orig_config != repaired_config:
                    return {
                        "type": "trigger_config_changed",
                        "event": event,
                        "original_config": orig_config,
                        "repaired_config": repaired_config,
                        "description": f"트리거 이벤트 '{event}'의 설정이 변경되었습니다."
                    }
        
        return None
    except Exception as e:
        return {
            "type": "trigger_check_error",
            "error": str(e),
            "description": "트리거 검증 중 오류가 발생했습니다."
        }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python src/structural_verifier.py <original_file> <repaired_file>")
        sys.exit(1)

    original_file = Path(sys.argv[1])
    repaired_file = Path(sys.argv[2])

    verify_structural_equivalence(original_file, repaired_file)

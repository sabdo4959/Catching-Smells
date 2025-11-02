"""
개선된 키 구조 검증 모듈 (v2.0)

키 구조와 구조적 값(needs, matrix 등)을 모두 검증합니다.
- 키 구조: 값은 블랙박스로 처리
- 구조적 값: needs, matrix 등 워크플로우 동작에 영향을 주는 특수 값들 검증

주요 개선사항:
1. needs 값 변경 검증 추가
2. matrix 전략 변경 검증 추가  
3. 단계적 검증 결과 제공
"""

import sys
from pathlib import Path
from pprint import pprint
from deepdiff import DeepDiff

try:
    from parser import GHAWorkflowParser
except ImportError:
    print("ERROR: 'parser.py'를 찾을 수 없습니다.", file=sys.stderr)
    sys.exit(1)


class EnhancedKeyStructureVerifier:
    """향상된 키 구조 검증기 메인 클래스"""
    
    def __init__(self):
        """검증기 초기화"""
        self.parser = GHAWorkflowParser()
        self.structural_verifier = StructuralValueVerifier()
    
    def verify_structural_safety(self, original_file, repaired_file):
        """구조적 안전성 검증"""
        from pathlib import Path
        
        if isinstance(original_file, str):
            original_file = Path(original_file)
        if isinstance(repaired_file, str):
            repaired_file = Path(repaired_file)
            
        result = verify_enhanced_structural_equivalence(original_file, repaired_file)
        
        return {
            'is_safe': result['safe'],
            'issues': result['key_structure_issues'] + result.get('steps_issues', []) + result['structural_value_issues'],
            'details': result['details']
        }


class StructuralValueVerifier:
    """구조적 값들(needs, matrix 등)을 검증하는 클래스"""
    
    @staticmethod
    def extract_structural_values(yaml_obj, path="root"):
        """YAML에서 구조적으로 중요한 값들을 추출합니다."""
        structural_values = {}
        
        if isinstance(yaml_obj, dict):
            for key, value in yaml_obj.items():
                current_path = f"{path}.{key}"
                
                # needs 필드 처리
                if key == "needs":
                    structural_values[current_path] = {
                        "type": "needs",
                        "value": value if isinstance(value, list) else [value] if value else []
                    }
                
                # matrix 전략 처리
                elif key == "matrix":
                    structural_values[current_path] = {
                        "type": "matrix",
                        "value": value
                    }
                
                # 재귀적으로 하위 검색
                if isinstance(value, (dict, list)):
                    child_values = StructuralValueVerifier.extract_structural_values(value, current_path)
                    structural_values.update(child_values)
        
        elif isinstance(yaml_obj, list):
            for i, item in enumerate(yaml_obj):
                current_path = f"{path}[{i}]"
                if isinstance(item, (dict, list)):
                    child_values = StructuralValueVerifier.extract_structural_values(item, current_path)
                    structural_values.update(child_values)
        
        return structural_values
    
    @staticmethod
    def compare_structural_values(orig_values, repaired_values):
        """구조적 값들을 비교하여 변경사항을 찾습니다."""
        issues = []
        
        # 1. 구조적 값이 제거된 경우
        removed_paths = set(orig_values.keys()) - set(repaired_values.keys())
        for path in removed_paths:
            value_type = orig_values[path]["type"]
            issues.append(f"구조적 값 제거: {path} (타입: {value_type})")
        
        # 2. 구조적 값이 추가된 경우 (일부는 허용)
        added_paths = set(repaired_values.keys()) - set(orig_values.keys())
        for path in added_paths:
            value_type = repaired_values[path]["type"]
            if not StructuralValueVerifier._is_allowed_structural_addition(path, value_type):
                issues.append(f"예상치 못한 구조적 값 추가: {path} (타입: {value_type})")
        
        # 3. 공통 구조적 값들의 변경 검사
        common_paths = set(orig_values.keys()) & set(repaired_values.keys())
        for path in common_paths:
            orig_info = orig_values[path]
            repaired_info = repaired_values[path]
            
            # needs 의존성 변경 검사
            if orig_info["type"] == "needs":
                orig_deps = set(orig_info["value"])
                repaired_deps = set(repaired_info["value"])
                
                if orig_deps != repaired_deps:
                    issues.append(f"needs 의존성 변경: {path} ({orig_deps} → {repaired_deps})")
            
            # matrix 전략 변경 검사
            elif orig_info["type"] == "matrix":
                if orig_info["value"] != repaired_info["value"]:
                    issues.append(f"matrix 전략 변경: {path}")
        
        return issues
    
    @staticmethod
    def _is_allowed_structural_addition(path, value_type):
        """구조적 값 추가가 허용되는지 확인합니다."""
        # needs와 matrix는 일반적으로 추가되면 안 됨
        # 단, smell 수정 관련 특수 케이스는 허용 가능
        return False


def verify_enhanced_structural_equivalence(original_file: Path, repaired_file: Path):
    """
    향상된 구조적 동치성을 검증합니다.
    키 구조 + 구조적 값 모두 검증
    
    Returns:
        dict: 검증 결과 상세 정보
    """
    print("="*70)
    print(f"🔬 Enhanced 구조 검증 - 원본: {original_file.name}")
    print(f"🔬 Enhanced 구조 검증 - 수정: {repaired_file.name}")
    print("="*70)

    # 1. 파싱
    parser = GHAWorkflowParser()
    ast_orig = parser.parse(original_file)
    ast_repaired = parser.parse(repaired_file)

    if not ast_orig or not ast_repaired:
        print("ERROR: 파일 파싱에 실패하여 검증을 중단합니다.", file=sys.stderr)
        return {"safe": False, "reason": "parsing_failed"}

    # 2. 키 구조 검증 (기존 로직)
    orig_key_structure = _extract_key_structure(ast_orig)
    repaired_key_structure = _extract_key_structure(ast_repaired)
    key_structure_issues = _compare_key_structures(orig_key_structure, repaired_key_structure)
    
    # 3. Steps 순서 검증 (특별 처리)
    steps_issues = _check_steps_order_changes(ast_orig, ast_repaired)
    
    # 4. 구조적 값 검증 (새로운 로직)
    verifier = StructuralValueVerifier()
    orig_structural_values = verifier.extract_structural_values(ast_orig)
    repaired_structural_values = verifier.extract_structural_values(ast_repaired)
    structural_value_issues = verifier.compare_structural_values(orig_structural_values, repaired_structural_values)
    
    # 5. 결과 통합
    print("\\n[1] 키 구조 검증 결과:")
    print("-" * 40)
    if key_structure_issues:
        print("❌ 키 구조 문제 발견:")
        for issue in key_structure_issues:
            print(f"  - {issue}")
    else:
        print("✅ 키 구조 안전")
    
    print("\\n[2] Steps 순서 검증 결과:")
    print("-" * 40)
    if steps_issues:
        print("❌ Steps 순서 문제 발견:")
        for issue in steps_issues:
            print(f"  - {issue}")
    else:
        print("✅ Steps 순서 안전")
    
    print("\\n[3] 구조적 값 검증 결과:")
    print("-" * 40)
    if structural_value_issues:
        print("❌ 구조적 값 문제 발견:")
        for issue in structural_value_issues:
            print(f"  - {issue}")
    else:
        print("✅ 구조적 값 안전")
    
    # 6. 최종 판정
    all_issues = key_structure_issues + steps_issues + structural_value_issues
    is_safe = len(all_issues) == 0
    
    print("\\n[4] 최종 판정:")
    print("-" * 40)
    if is_safe:
        print("🎉 구조적으로 안전함")
    else:
        print(f"⚠️  구조적 위험 ({len(all_issues)}개 문제)")
    
    return {
        "safe": is_safe,
        "key_structure_issues": key_structure_issues,
        "steps_issues": steps_issues,
        "structural_value_issues": structural_value_issues,
        "total_issues": len(all_issues),
        "details": {
            "original_structural_values": orig_structural_values,
            "repaired_structural_values": repaired_structural_values
        }
    }


def _check_steps_order_changes(ast_orig, ast_repaired):
    """Steps 순서 변경을 검사합니다."""
    issues = []
    
    # 모든 jobs를 순회하면서 steps 확인
    orig_jobs = ast_orig.get('jobs', {})
    repaired_jobs = ast_repaired.get('jobs', {})
    
    # 공통으로 존재하는 job들만 확인
    common_jobs = set(orig_jobs.keys()) & set(repaired_jobs.keys())
    
    for job_name in common_jobs:
        orig_steps = orig_jobs[job_name].get('steps', [])
        repaired_steps = repaired_jobs[job_name].get('steps', [])
        
        # steps 길이가 다르면 이미 다른 검증에서 잡힐 것
        if len(orig_steps) != len(repaired_steps):
            continue
        
        # Steps 순서 변경 vs 값 변경 구별
        if _is_steps_reordered(orig_steps, repaired_steps):
            issues.append(f"Steps 순서 변경 감지: jobs.{job_name}.steps")
    
    return issues


def _is_steps_reordered(orig_steps, repaired_steps):
    """Steps가 순서 변경되었는지 확인 (값 변경과 구별)"""
    if len(orig_steps) != len(repaired_steps):
        return False
    
    # 1. 위치별 비교: 같은 위치에서 서로 다른 step 타입이 나타나면 순서 변경
    for i, (orig_step, repaired_step) in enumerate(zip(orig_steps, repaired_steps)):
        orig_keys = tuple(sorted(orig_step.keys()))
        repaired_keys = tuple(sorted(repaired_step.keys()))
        
        # 키 구조가 다르면 순서가 바뀐 것
        if orig_keys != repaired_keys:
            return True
    
    # 2. 모든 위치에서 키 구조가 같다면, 값만 변경된 것으로 간주
    # (하지만 실제로는 step들이 섞였을 수도 있음)
    
    # 3. Step 정체성 기반 검사: 각 step의 최소한의 식별 정보로 매칭
    orig_identities = _extract_step_identities(orig_steps)
    repaired_identities = _extract_step_identities(repaired_steps)
    
    # 같은 step들이 다른 순서로 나타나면 순서 변경
    if set(orig_identities) == set(repaired_identities) and orig_identities != repaired_identities:
        return True
    
    return False


def _extract_step_identities(steps):
    """각 step의 최소한의 식별 정보 추출"""
    identities = []
    
    for step in steps:
        # Step 타입 결정: uses vs run vs name 기반 식별
        if 'uses' in step:
            # uses step은 action 이름의 prefix만 사용 (버전 제외)
            uses_value = step['uses']
            action_name = uses_value.split('@')[0] if '@' in uses_value else uses_value
            identity = f"uses:{action_name}"
        elif 'run' in step:
            # run step은 name이 있으면 name, 없으면 run의 첫 단어
            if 'name' in step:
                identity = f"run:{step['name']}"
            else:
                run_first_word = step['run'].split()[0] if step['run'].strip() else "run"
                identity = f"run:{run_first_word}"
        else:
            # 기타 step은 키 조합 사용
            identity = f"other:{'-'.join(sorted(step.keys()))}"
        
        identities.append(identity)
    
    return identities


def _extract_key_structure(yaml_obj, path="root"):
    """
    YAML 객체에서 키 구조만 추출합니다.
    값은 블랙박스로 처리하고 타입 정보만 기록합니다.
    """
    structure = {}
    
    if isinstance(yaml_obj, dict):
        structure[path] = {
            "type": "dict",
            "keys": list(yaml_obj.keys())
        }
        
        for key, value in yaml_obj.items():
            child_path = f"{path}.{key}"
            child_structure = _extract_key_structure(value, child_path)
            structure.update(child_structure)
    
    elif isinstance(yaml_obj, list):
        structure[path] = {
            "type": "list",
            "length": len(yaml_obj)
        }
        
        for i, item in enumerate(yaml_obj):
            child_path = f"{path}[{i}]"
            child_structure = _extract_key_structure(item, child_path)
            structure.update(child_structure)
    
    else:
        # 값은 블랙박스로 처리 - 타입만 기록
        structure[path] = {
            "type": "value",
            "value_type": type(yaml_obj).__name__
        }
    
    return structure


def _compare_key_structures(orig_structure, repaired_structure):
    """
    두 키 구조를 비교하여 문제점을 찾습니다.
    """
    issues = []
    
    # 1. 키가 제거된 경우 (구조적 문제)
    removed_keys = set(orig_structure.keys()) - set(repaired_structure.keys())
    for key in removed_keys:
        if not _is_allowed_key_removal(key):
            issues.append(f"키가 제거됨: {key}")
    
    # 2. 키가 추가된 경우 (smell 수정 관련은 허용)
    added_keys = set(repaired_structure.keys()) - set(orig_structure.keys())
    for key in added_keys:
        if not _is_allowed_key_addition(key):
            issues.append(f"예상치 못한 키 추가: {key}")
    
    # 3. 공통 키들의 구조 변경 검사
    common_keys = set(orig_structure.keys()) & set(repaired_structure.keys())
    for key in common_keys:
        orig_info = orig_structure[key]
        repaired_info = repaired_structure[key]
        
        # 타입 변경 검사 (dict <-> list <-> value)
        if orig_info["type"] != repaired_info["type"]:
            issues.append(f"타입 변경: {key} ({orig_info['type']} → {repaired_info['type']})")
        
        # dict의 경우 키 순서 변경 검사
        elif orig_info["type"] == "dict":
            orig_keys = orig_info.get("keys", [])
            repaired_keys = repaired_info.get("keys", [])
            
            # 키 순서 중요한 경우만 체크 (jobs, steps)
            if _is_order_critical_path(key) and orig_keys != repaired_keys:
                issues.append(f"키 순서 변경: {key}")
        
        # list의 경우 길이 변경 검사
        elif orig_info["type"] == "list":
            orig_length = orig_info.get("length", 0)
            repaired_length = repaired_info.get("length", 0)
            
            # 스텝 리스트 등에서 길이 변경은 중요
            if _is_length_critical_path(key) and orig_length != repaired_length:
                issues.append(f"리스트 길이 변경: {key} ({orig_length} → {repaired_length})")
            
            # steps 리스트의 경우 순서 변경 검사는 별도 함수에서 처리
            # (여기서는 길이 변경만 확인)
    
    return issues


def _is_allowed_key_removal(key_path):
    """키 제거가 허용되는지 확인합니다."""
    if "timeout-minutes" in key_path:
        return True
    return False


def _is_allowed_key_addition(key_path):
    """키 추가가 허용되는지 확인합니다."""
    allowed_additions = [
        "permissions",      # Smell 3: GITHUB_TOKEN permissions
        "timeout-minutes",  # Smell 6: No job timeout
        "concurrency",      # Smell 7: Duplicate action execution
        "if",              # Smell 5: Forked PR action execution
    ]
    
    for allowed in allowed_additions:
        if allowed in key_path:
            return True
    
    return False


def _is_order_critical_path(key_path):
    """키 순서가 중요한 경로인지 확인합니다."""
    order_critical = ["root.jobs"]
    
    if ".steps" in key_path and key_path.endswith(".steps"):
        return True
    
    if key_path.startswith("root.jobs.") and key_path.count('.') == 2:
        return False
    
    for critical in order_critical:
        if key_path == critical:
            return True
    
    return False


def _is_length_critical_path(key_path):
    """리스트 길이가 중요한 경로인지 확인합니다."""
    length_critical = [".steps"]
    
    for critical in length_critical:
        if critical in key_path:
            return True
    
    return False


# 하위 호환성을 위한 기존 함수
def verify_structural_equivalence(original_file: Path, repaired_file: Path):
    """기존 함수 (하위 호환성)"""
    result = verify_enhanced_structural_equivalence(original_file, repaired_file)
    return result["safe"]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python enhanced_key_structure_verifier.py <original_file> <repaired_file>")
        sys.exit(1)

    original_file = Path(sys.argv[1])
    repaired_file = Path(sys.argv[2])

    result = verify_enhanced_structural_equivalence(original_file, repaired_file)
    sys.exit(0 if result["safe"] else 1)

"""
개선된 구조적 검증 모듈

키 구조에만 집중하고, 값은 블랙박스로 처리합니다.
새로운 키가 smell 수정과 관련된 경우 예외로 허용합니다.
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


class KeyStructureVerifier:
    """키 구조 검증을 위한 클래스"""
    
    def verify_key_structure(self, original_file: str, repaired_file: str) -> bool:
        """
        키 구조를 검증합니다.
        
        Args:
            original_file: 원본 파일 경로
            repaired_file: 수정된 파일 경로
            
        Returns:
            bool: 구조적으로 안전한지 여부
        """
        try:
            result = verify_structural_equivalence(Path(original_file), Path(repaired_file))
            return result
        except Exception as e:
            print(f"ERROR: 키 구조 검증 중 오류 발생: {e}", file=sys.stderr)
            return False


def verify_structural_equivalence(original_file: Path, repaired_file: Path):
    """
    키 구조 기반 구조적 동치성을 검증합니다.
    
    Returns:
        bool: 구조적으로 안전한지 여부
    """
    print("="*60)
    print(f"🔬 원본 파일: {original_file.name}")
    print(f"🔬 수정된 파일: {repaired_file.name}")
    print("="*60)

    # 1. 파싱
    parser = GHAWorkflowParser()
    ast_orig = parser.parse(original_file)
    ast_repaired = parser.parse(repaired_file)

    if not ast_orig or not ast_repaired:
        print("ERROR: 파일 파싱에 실패하여 검증을 중단합니다.", file=sys.stderr)
        return False

    # 2. 키 구조 추출
    orig_structure = _extract_key_structure(ast_orig)
    repaired_structure = _extract_key_structure(ast_repaired)
    
    # 3. 구조 비교
    structure_issues = _compare_key_structures(orig_structure, repaired_structure)
    
    print("\n[1] 키 구조 검증 결과:")
    print("-" * 40)
    
    if not structure_issues:
        print("✅ 키 구조 검증: 모든 검사 통과")
    else:
        print("🚨 키 구조 문제:")
        for issue in structure_issues:
            print(f"  - {issue}")
    
    # 4. 최종 판정
    print("\n" + "="*60)
    is_safe = len(structure_issues) == 0
    
    if is_safe:
        print("🎉 최종 결론: 구조적으로 안전(SAFE)합니다.")
        print("   키 구조가 적절히 유지되고 있습니다.")
    else:
        print("🚨 최종 결론: 구조적으로 안전하지 않습니다(UNSAFE).")
        print(f"   - 키 구조 문제: {len(structure_issues)}개")
    
    print("="*60)
    return is_safe


def _extract_key_structure(yaml_obj, path="root"):
    """
    YAML 객체에서 키 구조만 추출합니다.
    값은 무시하고 키의 존재와 타입만 기록합니다.
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
    
    return issues


def _is_allowed_key_removal(key_path):
    """
    키 제거가 허용되는지 확인합니다.
    일반적으로 키 제거는 구조적 변경이므로 허용하지 않습니다.
    """
    # timeout-minutes 제거는 허용 (smell 수정)
    if "timeout-minutes" in key_path:
        return True
    
    return False


def _is_allowed_key_addition(key_path):
    """
    키 추가가 허용되는지 확인합니다.
    smell 수정과 관련된 키 추가는 허용합니다.
    """
    # Smell 수정과 관련된 키들
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
    """
    키 순서가 중요한 경로인지 확인합니다.
    잡과 스텝의 순서는 중요하지만, 잡 내부 속성 순서는 중요하지 않습니다.
    """
    order_critical = [
        "root.jobs",      # 잡 순서 (중요)
    ]
    
    # 스텝 순서 (중요) - 각 잡의 steps 리스트
    if ".steps" in key_path and key_path.endswith(".steps"):
        return True
    
    # 잡 내부 속성 순서는 중요하지 않음
    if key_path.startswith("root.jobs.") and key_path.count('.') == 2:
        return False
    
    for critical in order_critical:
        if key_path == critical:  # 정확히 일치해야 함
            return True
    
    return False


def _is_length_critical_path(key_path):
    """
    리스트 길이가 중요한 경로인지 확인합니다.
    """
    length_critical = [
        ".steps",         # 스텝 리스트 길이
    ]
    
    for critical in length_critical:
        if critical in key_path:
            return True
    
    return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python key_structure_verifier.py <original_file> <repaired_file>")
        sys.exit(1)

    original_file = Path(sys.argv[1])
    repaired_file = Path(sys.argv[2])

    verify_structural_equivalence(original_file, repaired_file)

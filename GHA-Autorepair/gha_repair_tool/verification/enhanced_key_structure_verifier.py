"""
개선된 키 구조 검증 모듈 (v3.0)

structural_verifier.md의 철학에 따른 체계적 검증:
1. "키 구조" 기반 검증 - 값은 블랙박스로 처리
2. "안전한 변경" vs "위험한 변경" 명확한 분류  
3. Tier-1 스멜 수정으로 인한 허용된 변경 처리
4. steps 순서 변경 엄격한 검증
5. "값이 곧 구조"인 키들(needs, matrix)의 엄격한 검증
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

# ===== 검증 규칙 정의 =====

# ✅ 안전한 변경: 단순 메타데이터 및 논리 키 (값 변경 무시)
SAFE_METADATA_KEYS = {
    'name',      # UI 표시용 이름
    'env',       # 환경 변수
    'with',      # 액션 입력값
    'on',        # 트리거 (논리적 검증 대상이므로 여기서는 무시)
    'if'         # 조건 (논리적 검증 대상이므로 여기서는 무시)
}

# ✅ 허용된 스멜 수정으로 인한 키 추가/변경
ALLOWED_SMELL_FIX_KEYS = {
    'permissions',      # Smell 15: 권한 설정
    'timeout-minutes',  # Smell 10: 타임아웃 설정
    'concurrency',      # Smell 4, 5: 동시성 제어
    'continue-on-error' # 에러 처리 개선
}

# ✅ 허용된 스멜 수정으로 인한 특정 값 변경 (조건부)
ALLOWED_VALUE_CHANGE_CONTEXTS = {
    'uses',  # Smell 24: 버전 업그레이드 (예: @v2 → @v4)
    'run'    # Smell 25: 사용 중단된 명령어 수정 (예: set-output → GITHUB_OUTPUT)
}

# ❌ 위험한 변경: "값이 곧 구조"인 키들 (엄격한 검증)
STRUCTURAL_VALUE_KEYS = {
    'needs',           # 잡 의존성 - 실행 순서 정의
    'strategy.matrix', # 매트릭스 전략 - 실행 개수/조합 정의
    'jobs',           # 잡 목록 - 워크플로우 구성 정의
    'steps'           # 스텝 목록 - 잡 내 실행 순서 정의
}

# ❌ 위험한 변경: 핵심 구조 식별자 (절대 변경 불가)
CORE_IDENTITY_KEYS = {
    'jobs.<job_id>',  # 잡 ID 이름
    'steps.id'        # 스텝 ID 이름  
}


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
    """
    Steps 순서 검증 상세 로직 (structural_verifier.md 5번 항목)
    
    steps 리스트의 순서 변경은 치명적인 구조 변경이므로 
    "지문(Fingerprint)" 비교를 통해 엄격하게 검증합니다.
    
    Returns:
        bool: True if steps are reordered (UNSAFE), False if safe
    """
    # 1. 길이 확인 (다르면 UNSAFE)
    if len(orig_steps) != len(repaired_steps):
        return True
    
    # 2. 각 스텝의 "핵심 지문" 비교
    for i, (orig_step, repaired_step) in enumerate(zip(orig_steps, repaired_steps)):
        orig_fingerprint = _extract_step_fingerprint(orig_step)
        repaired_fingerprint = _extract_step_fingerprint(repaired_step)
        
        # 3. 같은 위치(index)의 스텝이 다른 지문을 가지면 UNSAFE
        if not _is_fingerprint_compatible(orig_fingerprint, repaired_fingerprint):
            return True
    
    # 4. 모든 스텝의 지문이 순서대로 일치하면 SAFE
    return False


def _normalize_whitespace(text):
    """
    텍스트의 줄바꿈과 공백을 정규화합니다.
    
    향상된 검증에서 의미 없는 포맷팅 차이는 무시하도록 합니다:
    - 줄 끝 공백 제거
    - 연속된 줄바꿈 정규화
    - 마지막 줄바꿈 통일
    """
    if not isinstance(text, str):
        return text
    
    # 1. 각 줄의 끝 공백 제거
    lines = text.splitlines()
    lines = [line.rstrip() for line in lines]
    
    # 2. 빈 줄들 정리 (연속된 빈 줄은 하나로)
    normalized_lines = []
    prev_empty = False
    for line in lines:
        if line.strip() == '':
            if not prev_empty:
                normalized_lines.append('')
            prev_empty = True
        else:
            normalized_lines.append(line)
            prev_empty = False
    
    # 3. 마지막 빈 줄 제거
    while normalized_lines and normalized_lines[-1] == '':
        normalized_lines.pop()
    
    return '\n'.join(normalized_lines)


def _remove_comments(text):
    """
    텍스트에서 주석 라인을 제거합니다.
    
    Shell/Bash 스타일의 주석 (#로 시작하는 라인)을 제거하여
    주석만 다른 경우를 허용된 변경으로 처리합니다.
    """
    if not isinstance(text, str):
        return text
    
    lines = text.splitlines()
    non_comment_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        # 완전히 주석으로만 이루어진 라인은 제거
        if stripped_line.startswith('#') or stripped_line == '':
            continue
        # 라인 끝의 주석은 제거 (단순 구현)
        if '#' in line:
            # 문자열 안의 #은 고려하지 않는 단순 구현
            # 실제 명령어에서 #이 포함된 경우는 드물기 때문
            comment_pos = line.find('#')
            line_without_comment = line[:comment_pos].rstrip()
            if line_without_comment:
                non_comment_lines.append(line_without_comment)
        else:
            non_comment_lines.append(line)
    
    return '\n'.join(non_comment_lines)


def _extract_step_fingerprint(step):
    """
    각 스텝의 핵심 지문 추출
    
    핵심 지문: uses 키의 값 또는 run 키의 값
    (name 등 다른 키의 변경은 무시)
    """
    if 'uses' in step:
        # uses step의 경우: action 이름 (버전 제외 가능)
        uses_value = step['uses']
        # 버전 업그레이드는 허용된 변경이므로 기본 action 이름만 추출
        action_name = uses_value.split('@')[0] if '@' in uses_value else uses_value
        return {'type': 'uses', 'action': action_name, 'full_uses': uses_value}
    
    elif 'run' in step:
        # run step의 경우: run 명령어 내용 (줄바꿈 정규화 적용)
        normalized_command = _normalize_whitespace(step['run'])
        return {'type': 'run', 'command': normalized_command}
    
    else:
        # 기타 step: 키 구조로 식별
        keys = set(step.keys()) - SAFE_METADATA_KEYS - ALLOWED_SMELL_FIX_KEYS
        return {'type': 'other', 'keys': frozenset(keys)}


def _is_fingerprint_compatible(orig_fp, repaired_fp):
    """
    두 스텝의 지문이 호환되는지 확인
    
    허용되는 변경:
    - uses: 버전 업그레이드 (Smell 24)
    - run: 사용 중단된 명령어 수정 (Smell 25)
    """
    # 타입이 다르면 호환되지 않음
    if orig_fp['type'] != repaired_fp['type']:
        return False
    
    if orig_fp['type'] == 'uses':
        # uses step: action 이름이 같으면 호환 (버전 업그레이드 허용)
        if orig_fp['action'] == repaired_fp['action']:
            return True
        # action 이름이 다르면 호환되지 않음
        return False
    
    elif orig_fp['type'] == 'run':
        # run step: 명령어 내용이 같으면 호환
        if orig_fp['command'] == repaired_fp['command']:
            return True
        # TODO: Smell 25 (사용 중단된 명령어 수정) 검증 로직 추가 가능
        # 예: set-output → GITHUB_OUTPUT 변경은 허용
        return _is_allowed_run_command_change(orig_fp['command'], repaired_fp['command'])
    
    else:
        # 기타 step: 키 구조가 같으면 호환
        return orig_fp['keys'] == repaired_fp['keys']


def _is_allowed_run_command_change(orig_command, repaired_command):
    """
    허용된 run 명령어 변경인지 확인 (Smell 25 + 주석 제거)
    
    허용되는 변경:
    - set-output → GITHUB_OUTPUT 등의 사용 중단된 명령어 수정
    - 주석 제거 (# 로 시작하는 라인)
    - 줄바꿈 및 공백 정규화
    """
    # 1. 줄바꿈 정규화 후 동일한지 확인
    normalized_orig = _normalize_whitespace(orig_command)
    normalized_repaired = _normalize_whitespace(repaired_command)
    
    if normalized_orig == normalized_repaired:
        return True  # 줄바꿈 차이만 있는 경우 허용
    
    # 2. 주석 제거 확인
    orig_without_comments = _remove_comments(normalized_orig)
    repaired_without_comments = _remove_comments(normalized_repaired)
    
    if orig_without_comments == repaired_without_comments:
        return True  # 주석만 제거된 경우 허용
    
    # 3. deprecated command patterns 확인
    deprecated_patterns = [
        ('set-output', 'GITHUB_OUTPUT'),
        ('add-path', 'GITHUB_PATH'),
        ('::set-env', 'GITHUB_ENV')
    ]
    
    # 간단한 패턴 매칭 (실제로는 더 정교한 분석 필요)
    for old_pattern, new_pattern in deprecated_patterns:
        if old_pattern in normalized_orig and new_pattern in normalized_repaired:
            return True
    
    return False
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
    마크다운 철학에 따른 키 구조 비교
    
    핵심 원칙:
    1. "값은 블랙박스" - 메타데이터 키의 값 변경은 무시
    2. "허용된 스멜 수정" - Tier-1 스멜 수정으로 인한 키 추가는 허용
    3. "핵심 구조 보호" - jobs, steps 등 워크플로우 뼈대는 엄격히 보호
    """
    issues = []
    
    # 1. 제거된 키 검사 (핵심 구조 키 제거는 위험)
    removed_keys = set(orig_structure.keys()) - set(repaired_structure.keys())
    for key in removed_keys:
        if _is_critical_structural_key(key):
            issues.append(f"핵심 구조 키 제거: {key}")
        # 메타데이터 키 제거는 허용 (예: name, env 등)
    
    # 2. 추가된 키 검사 (스멜 수정 관련 추가는 허용)
    added_keys = set(repaired_structure.keys()) - set(orig_structure.keys())
    for key in added_keys:
        if not _is_allowed_key_addition_for_smell_fix(key):
            issues.append(f"예상치 못한 키 추가: {key}")
    
    # 3. 공통 키의 구조 변경 검사
    common_keys = set(orig_structure.keys()) & set(repaired_structure.keys())
    for key in common_keys:
        orig_info = orig_structure[key]
        repaired_info = repaired_structure[key]
        
        # 타입 변경 검사 (중요한 구조만)
        if orig_info["type"] != repaired_info["type"]:
            if _is_type_change_critical(key, orig_info["type"], repaired_info["type"]):
                issues.append(f"중요 타입 변경: {key} ({orig_info['type']} → {repaired_info['type']})")
        
        # 리스트 길이 변경 검사 (jobs, steps 등)
        elif orig_info["type"] == "list":
            if _is_list_length_critical(key):
                orig_length = orig_info.get("length", 0)
                repaired_length = repaired_info.get("length", 0)
                if orig_length != repaired_length:
                    issues.append(f"핵심 리스트 길이 변경: {key} ({orig_length} → {repaired_length})")
        
        # 딕셔너리 키 순서 변경 검사 (jobs만)
        elif orig_info["type"] == "dict":
            if _is_dict_key_order_critical(key):
                orig_keys = orig_info.get("keys", [])
                repaired_keys = repaired_info.get("keys", [])
                if orig_keys != repaired_keys:
                    issues.append(f"핵심 딕셔너리 키 순서 변경: {key}")
    
    return issues


def _is_critical_structural_key(key_path):
    """핵심 구조 키인지 판단 (제거되면 위험)"""
    critical_patterns = [
        'root.jobs',           # 전체 jobs 딕셔너리
        'root.jobs.',          # 개별 job 정의
        '.steps',             # steps 리스트
        '.needs',             # 의존성 정의
        '.strategy.matrix',   # 매트릭스 전략
        '.runs-on'            # 실행 환경
    ]
    
    return any(pattern in key_path for pattern in critical_patterns)


def _is_allowed_key_addition_for_smell_fix(key_path):
    """스멜 수정으로 인한 허용된 키 추가인지 판단"""
    allowed_additions = [
        '.permissions',        # Smell 15: 권한 설정 추가
        '.timeout-minutes',    # Smell 10: 타임아웃 추가
        '.concurrency',        # Smell 4, 5: 동시성 제어 추가
        '.continue-on-error',  # 에러 처리 개선
        '.if',                # Smell 9, 10: 조건부 실행 추가
        '.on.',               # 트리거 조건 개선
        '.paths',             # Smell 16: 경로 필터 추가
        '.paths-ignore'       # Smell 16: 경로 무시 추가
    ]
    
    return any(pattern in key_path for pattern in allowed_additions)


def _is_type_change_critical(key_path, orig_type, repaired_type):
    """타입 변경이 중요한 구조 변경인지 판단"""
    # jobs, steps 등의 타입 변경은 치명적
    critical_type_paths = [
        'root.jobs',
        '.steps',
        '.needs',
        '.strategy.matrix'
    ]
    
    if any(pattern in key_path for pattern in critical_type_paths):
        return True
    
    # 스칼라 → 딕셔너리 변경은 구조적 개선일 수 있음 (예: permissions: read-all → permissions: {contents: read})
    if orig_type in ['str', 'bool', 'int'] and repaired_type == 'dict':
        if any(allowed in key_path for allowed in ['.permissions', '.with']):
            return False  # 허용된 확장
    
    return True  # 기본적으로 타입 변경은 중요


def _is_list_length_critical(key_path):
    """리스트 길이 변경이 중요한지 판단"""
    critical_list_paths = [
        'root.jobs',          # jobs는 딕셔너리지만 순서 중요
        '.steps',            # steps 리스트
        '.needs',            # needs 리스트  
        '.strategy.matrix'   # matrix 리스트
    ]
    
    return any(pattern in key_path for pattern in critical_list_paths)


def _is_dict_key_order_critical(key_path):
    """딕셔너리 키 순서가 중요한지 판단"""
    # GitHub Actions에서는 일반적으로 키 순서가 의미 없음
    # jobs는 needs에 의해 의존성이 결정되므로 딕셔너리 순서는 무관
    # 마크다운 철학: "값이 곧 구조"인 키(needs, matrix)만 중요
    order_critical_paths = [
        # 현재는 키 순서가 중요한 경우가 없음
        # jobs 딕셔너리 순서는 needs에 의해 실행 순서가 결정되므로 무관
    ]
    
    return any(pattern in key_path for pattern in order_critical_paths)


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

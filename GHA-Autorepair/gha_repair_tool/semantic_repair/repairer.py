"""
의미론적 스멜 복구 모듈

탐지된 의미론적 스멜을 LLM을 통해 수정합니다.
"""

import logging
from typing import List, Dict, Any, Optional

from utils import llm_api, yaml_parser, process_runner


def repair_smells(
    yaml_path: str, 
    detected_smells: List[Dict[str, Any]], 
    repair_mode: str = "guided"
) -> Dict[str, Any]:
    """
    탐지된 의미론적 스멜을 수정합니다.
    
    Args:
        yaml_path: 원본 YAML 파일 경로
        detected_smells: 탐지된 스멜 리스트 (detector.py에서 반환)
        repair_mode: 복구 모드 ("guided" 또는 "simple")
        
    Returns:
        Dict: 수정 결과
              {
                  "success": bool,
                  "repaired_content": str,
                  "changes": List[Dict],
                  "remaining_smells": List[Dict]
              }
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"의미론적 스멜 복구 시작: {yaml_path}")
        logger.info(f"복구 모드: {repair_mode}, 스멜 개수: {len(detected_smells)}")
        
        # 원본 YAML 내용 읽기
        original_content = yaml_parser.read_yaml_content(yaml_path)
        if not original_content:
            return _create_repair_result(False, "", [], detected_smells)
        
        # 우선순위별로 스멜 정렬 (high -> medium -> low)
        sorted_smells = _sort_smells_by_priority(detected_smells)
        
        # 현재 작업 중인 내용
        current_content = original_content
        applied_changes = []
        remaining_smells = []
        
        # 각 스멜을 순차적으로 수정
        for smell in sorted_smells:
            repair_result = _repair_single_smell(
                current_content, 
                smell, 
                repair_mode
            )
            
            if repair_result["success"]:
                current_content = repair_result["repaired_content"]
                applied_changes.append(repair_result["change"])
                logger.info(f"스멜 수정 완료: {smell['smell_type']}")
            else:
                remaining_smells.append(smell)
                logger.warning(f"스멜 수정 실패: {smell['smell_type']}")
        
        # 최종 검증
        final_validation = _validate_repaired_yaml(current_content)
        
        success = final_validation and len(applied_changes) > 0
        
        return _create_repair_result(
            success, 
            current_content, 
            applied_changes, 
            remaining_smells
        )
        
    except Exception as e:
        logger.error(f"의미론적 스멜 복구 중 오류 발생: {e}")
        return _create_repair_result(False, "", [], detected_smells)


def _repair_single_smell(
    yaml_content: str, 
    smell: Dict[str, Any], 
    repair_mode: str
) -> Dict[str, Any]:
    """
    단일 스멜을 수정합니다.
    
    Args:
        yaml_content: 현재 YAML 내용
        smell: 수정할 스멜 정보
        repair_mode: 복구 모드
        
    Returns:
        Dict: 단일 스멜 수정 결과
    """
    logger = logging.getLogger(__name__)
    
    try:
        # LLM용 프롬프트 생성
        prompt = _generate_smell_repair_prompt(yaml_content, smell, repair_mode)
        
        # LLM 호출
        llm_response = llm_api.call_llm(prompt)
        
        if not llm_response:
            return {"success": False, "repaired_content": yaml_content}
        
        # LLM 응답에서 수정된 YAML 추출
        repaired_content = _extract_yaml_from_response(llm_response)
        
        if not repaired_content:
            return {"success": False, "repaired_content": yaml_content}
        
        # 수정 결과 검증
        if _validate_smell_repair(yaml_content, repaired_content, smell):
            change_info = _create_change_info(smell, yaml_content, repaired_content)
            return {
                "success": True,
                "repaired_content": repaired_content,
                "change": change_info
            }
        else:
            return {"success": False, "repaired_content": yaml_content}
        
    except Exception as e:
        logger.error(f"단일 스멜 수정 중 오류: {e}")
        return {"success": False, "repaired_content": yaml_content}


def _generate_smell_repair_prompt(
    yaml_content: str, 
    smell: Dict[str, Any], 
    repair_mode: str
) -> str:
    """
    의미론적 스멜 수정을 위한 LLM 프롬프트를 생성합니다.
    
    Args:
        yaml_content: YAML 내용
        smell: 스멜 정보
        repair_mode: 복구 모드
        
    Returns:
        str: 생성된 프롬프트
    """
    smell_type = smell.get('smell_type', 'unknown')
    message = smell.get('message', '')
    severity = smell.get('severity', 'medium')
    
    base_prompt = f"""
GitHub Actions 워크플로우에서 의미론적 스멜을 수정해야 합니다.

**탐지된 스멜 정보:**
- 타입: {smell_type}
- 메시지: {message}
- 심각도: {severity}

**원본 워크플로우:**
```yaml
{yaml_content}
```

**수정 요구사항:**
"""
    
    if repair_mode == "guided":
        guided_instructions = _get_guided_repair_instructions(smell_type)
        prompt = base_prompt + f"""
{guided_instructions}

위 가이드라인을 따라 스멜을 수정하고, 수정된 전체 YAML을 제공해주세요.
수정 이유와 변경사항도 함께 설명해주세요.
"""
    else:  # simple mode
        prompt = base_prompt + """
위에서 탐지된 의미론적 스멜을 수정해주세요.
수정된 전체 YAML만 제공해주세요.
"""
    
    return prompt


def _get_guided_repair_instructions(smell_type: str) -> str:
    """
    스멜 타입별 수정 가이드라인을 반환합니다.
    
    Args:
        smell_type: 스멜 타입
        
    Returns:
        str: 수정 가이드라인
    """
    guidelines = {
        "hardcoded_credentials": """
1. 하드코딩된 비밀정보를 GitHub Secrets로 대체하세요
2. ${{ secrets.SECRET_NAME }} 형식을 사용하세요
3. 비밀정보가 로그에 노출되지 않도록 주의하세요
        """,
        
        "missing_permissions": """
1. 필요한 permissions를 명시적으로 선언하세요
2. 최소 권한 원칙을 따르세요
3. GITHUB_TOKEN의 기본 권한을 확인하세요
        """,
        
        "shell_injection": """
1. 사용자 입력을 직접 shell 명령에 사용하지 마세요
2. 환경변수를 통해 안전하게 전달하세요
3. 입력값 검증과 이스케이핑을 추가하세요
        """,
        
        "deprecated_action": """
1. 최신 버전의 액션으로 업데이트하세요
2. 새로운 문법과 기능을 활용하세요
3. 호환성 문제가 없는지 확인하세요
        """
    }
    
    return guidelines.get(smell_type, "일반적인 모범 사례를 따라 수정하세요.")


def _sort_smells_by_priority(smells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    스멜을 우선순위별로 정렬합니다.
    
    Args:
        smells: 스멜 리스트
        
    Returns:
        List[Dict]: 정렬된 스멜 리스트
    """
    severity_order = {"high": 0, "medium": 1, "low": 2}
    
    return sorted(
        smells, 
        key=lambda x: severity_order.get(x.get('severity', 'medium'), 1)
    )


def _extract_yaml_from_response(response: str) -> Optional[str]:
    """
    LLM 응답에서 YAML 코드를 추출합니다.
    
    Args:
        response: LLM 응답
        
    Returns:
        Optional[str]: 추출된 YAML 내용
    """
    try:
        # YAML 코드 블록 찾기
        import re
        
        # ```yaml 또는 ``` 코드 블록 찾기
        yaml_pattern = r'```(?:yaml)?\n(.*?)```'
        matches = re.findall(yaml_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # 코드 블록이 없다면 전체 응답을 YAML로 간주
        return response.strip()
        
    except Exception as e:
        logging.getLogger(__name__).error(f"YAML 추출 중 오류: {e}")
        return None


def _validate_smell_repair(
    original_content: str, 
    repaired_content: str, 
    smell: Dict[str, Any]
) -> bool:
    """
    스멜 수정 결과를 검증합니다.
    
    Args:
        original_content: 원본 내용
        repaired_content: 수정된 내용
        smell: 스멜 정보
        
    Returns:
        bool: 검증 성공 여부
    """
    try:
        # 1. YAML 문법 검증
        if not yaml_parser.validate_yaml(repaired_content):
            return False
        
        # 2. 기본적인 구조 검증 (jobs, steps 등이 유지되는지)
        original_structure = yaml_parser.get_workflow_structure(original_content)
        repaired_structure = yaml_parser.get_workflow_structure(repaired_content)
        
        if not _compare_workflow_structures(original_structure, repaired_structure):
            return False
        
        # 3. 스멜별 특화 검증
        return _validate_smell_specific_repair(repaired_content, smell)
        
    except Exception as e:
        logging.getLogger(__name__).error(f"수정 결과 검증 중 오류: {e}")
        return False


def _validate_smell_specific_repair(content: str, smell: Dict[str, Any]) -> bool:
    """
    스멜 타입별 특화 검증을 수행합니다.
    
    Args:
        content: 수정된 내용
        smell: 스멜 정보
        
    Returns:
        bool: 검증 성공 여부
    """
    smell_type = smell.get('smell_type', '')
    
    # TODO: 각 스멜 타입별 특화 검증 로직 구현
    if 'hardcoded' in smell_type.lower():
        # 하드코딩된 값이 secrets로 대체되었는지 확인
        return '${{ secrets.' in content
    
    if 'permission' in smell_type.lower():
        # permissions가 추가되었는지 확인
        return 'permissions:' in content
    
    return True  # 기본적으로 통과


def _compare_workflow_structures(structure1: Dict, structure2: Dict) -> bool:
    """
    워크플로우 구조를 비교합니다.
    
    Args:
        structure1: 첫 번째 구조
        structure2: 두 번째 구조
        
    Returns:
        bool: 구조가 유사한지 여부
    """
    # TODO: 더 정교한 구조 비교 로직 구현
    return True


def _create_change_info(
    smell: Dict[str, Any], 
    original: str, 
    repaired: str
) -> Dict[str, Any]:
    """
    변경 정보를 생성합니다.
    
    Args:
        smell: 스멜 정보
        original: 원본 내용
        repaired: 수정된 내용
        
    Returns:
        Dict: 변경 정보
    """
    return {
        "smell_type": smell.get('smell_type'),
        "change_type": "semantic_repair",
        "original_length": len(original),
        "repaired_length": len(repaired),
        "severity": smell.get('severity'),
        "message": smell.get('message')
    }


def _validate_repaired_yaml(content: str) -> bool:
    """
    최종 수정된 YAML을 검증합니다.
    
    Args:
        content: YAML 내용
        
    Returns:
        bool: 검증 성공 여부
    """
    return yaml_parser.validate_yaml(content)


def _create_repair_result(
    success: bool, 
    content: str, 
    changes: List[Dict], 
    remaining_smells: List[Dict]
) -> Dict[str, Any]:
    """
    수정 결과를 생성합니다.
    
    Args:
        success: 성공 여부
        content: 수정된 내용
        changes: 적용된 변경사항 리스트
        remaining_smells: 남은 스멜 리스트
        
    Returns:
        Dict: 수정 결과
    """
    return {
        "success": success,
        "repaired_content": content,
        "changes": changes,
        "remaining_smells": remaining_smells
    }

"""
의미론적 스멜 탐지 모듈

구문적으로 유효한 워크플로우에서 Tier-1 의미론적 스멜을 탐지합니다.
"""

import logging
from typing import List, Dict, Any

from utils import process_runner


def detect_smells(valid_yaml_path: str) -> List[Dict[str, Any]]:
    """
    구문적으로 유효한 워크플로우에서 의미론적 스멜을 탐지합니다.
    
    Args:
        valid_yaml_path: 구문적으로 유효한 YAML 파일 경로
        
    Returns:
        List[Dict]: 탐지된 스멜과 위치 정보를 담은 구조화된 데이터
                   예: [
                       {
                           "smell_type": "hardcoded_credentials",
                           "line": 15,
                           "column": 10,
                           "message": "Hardcoded secret detected",
                           "severity": "high"
                       }
                   ]
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"의미론적 스멜 탐지 시작: {valid_yaml_path}")
        
        # 탐지된 스멜을 저장할 리스트
        detected_smells = []
        
        # 1. 커스텀 smell_detector 실행
        custom_smells = _run_custom_smell_detector(valid_yaml_path)
        detected_smells.extend(custom_smells)
        
        # 2. actionlint (의미론적 체크 위주) 실행
        actionlint_smells = _run_actionlint_semantic_check(valid_yaml_path)
        detected_smells.extend(actionlint_smells)
        
        logger.info(f"총 {len(detected_smells)}개의 스멜 탐지됨")
        
        return detected_smells
        
    except Exception as e:
        logger.error(f"스멜 탐지 중 오류 발생: {e}")
        return []


def _run_custom_smell_detector(yaml_path: str) -> List[Dict[str, Any]]:
    """
    커스텀 smell_detector를 실행하여 스멜을 탐지합니다.
    
    Args:
        yaml_path: YAML 파일 경로
        
    Returns:
        List[Dict]: 탐지된 스멜 리스트
    """
    logger = logging.getLogger(__name__)
    
    try:
        # TODO: 기존 smell_detector 모듈과 연동
        # 예시: gha_ci_detector 모듈 활용
        
        # 임시 구현: 기존 프로젝트의 smell_detector 호출
        command = f"python -m gha_ci_detector single {yaml_path}"
        result = process_runner.run_command(command)
        
        if result['returncode'] != 0:
            logger.warning(f"Custom smell detector 실행 실패: {result['stderr']}")
            return []
        
        # TODO: smell_detector 출력을 파싱하여 구조화된 데이터로 변환
        smells = _parse_custom_detector_output(result['stdout'])
        
        logger.info(f"Custom detector에서 {len(smells)}개 스멜 탐지")
        return smells
        
    except Exception as e:
        logger.error(f"Custom smell detector 실행 중 오류: {e}")
        return []


def _run_actionlint_semantic_check(yaml_path: str) -> List[Dict[str, Any]]:
    """
    actionlint의 의미론적 체크를 실행합니다.
    
    Args:
        yaml_path: YAML 파일 경로
        
    Returns:
        List[Dict]: 탐지된 의미론적 문제 리스트
    """
    logger = logging.getLogger(__name__)
    
    try:
        # TODO: actionlint의 의미론적 체크 옵션 사용
        # 예시: actionlint -shellcheck= -pyflakes= workflow.yml
        
        command = f"actionlint -format '{{{{json .}}}}' {yaml_path}"
        result = process_runner.run_command(command)
        
        if result['returncode'] == 0:
            return []  # 문제 없음
        
        # TODO: actionlint 출력을 파싱하여 의미론적 문제만 필터링
        smells = _parse_actionlint_semantic_output(result['stderr'])
        
        logger.info(f"Actionlint에서 {len(smells)}개 의미론적 문제 탐지")
        return smells
        
    except Exception as e:
        logger.error(f"Actionlint 의미론적 체크 중 오류: {e}")
        return []


def _parse_custom_detector_output(output: str) -> List[Dict[str, Any]]:
    """
    커스텀 스멜 탐지기의 출력을 파싱합니다.
    
    Args:
        output: 탐지기 출력
        
    Returns:
        List[Dict]: 파싱된 스멜 정보
    """
    # TODO: 실제 smell_detector 출력 형식에 맞게 파싱 로직 구현
    
    smells = []
    lines = output.strip().split('\n')
    
    for line in lines:
        if 'smell' in line.lower() or 'warning' in line.lower():
            # 간단한 파싱 예시
            smells.append({
                'smell_type': 'custom_detected',
                'line': 0,
                'column': 0,
                'message': line.strip(),
                'severity': 'medium',
                'detector': 'custom'
            })
    
    return smells


def _parse_actionlint_semantic_output(output: str) -> List[Dict[str, Any]]:
    """
    actionlint의 의미론적 체크 출력을 파싱합니다.
    
    Args:
        output: actionlint 출력
        
    Returns:
        List[Dict]: 파싱된 의미론적 문제 정보
    """
    # TODO: actionlint JSON 출력을 파싱하여 의미론적 문제만 필터링
    
    smells = []
    lines = output.strip().split('\n')
    
    # 의미론적 문제 키워드들
    semantic_keywords = [
        'shell', 'permissions', 'credentials', 'security',
        'environment', 'context', 'expression'
    ]
    
    for line in lines:
        if any(keyword in line.lower() for keyword in semantic_keywords):
            smells.append({
                'smell_type': 'actionlint_semantic',
                'line': 0,
                'column': 0,
                'message': line.strip(),
                'severity': 'medium',
                'detector': 'actionlint'
            })
    
    return smells

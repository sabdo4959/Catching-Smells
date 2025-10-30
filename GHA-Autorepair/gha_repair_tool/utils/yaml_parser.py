"""
YAML 파싱 및 처리 유틸리티 모듈

GitHub Actions 워크플로우 YAML 파일의 파싱, 검증, 구조 분석을 담당합니다.
"""

import logging
from typing import Dict, Any, Optional, List
import os
import tempfile

try:
    import yaml
except ImportError:
    yaml = None


def read_yaml_content(file_path: str) -> Optional[str]:
    """
    YAML 파일의 내용을 읽어 문자열로 반환합니다.
    
    Args:
        file_path: YAML 파일 경로
        
    Returns:
        Optional[str]: 파일 내용 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not os.path.exists(file_path):
            logger.error(f"파일이 존재하지 않음: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        logger.debug(f"YAML 파일 읽기 완료: {file_path}")
        return content
        
    except Exception as e:
        logger.error(f"YAML 파일 읽기 중 오류 ({file_path}): {e}")
        return None


def write_yaml_content(content: str, file_path: str) -> bool:
    """
    YAML 내용을 파일에 저장합니다.
    
    Args:
        content: 저장할 YAML 내용
        file_path: 저장할 파일 경로
        
    Returns:
        bool: 저장 성공 여부
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 파일 경로가 디렉토리인지 확인
        if os.path.isdir(file_path):
            logger.error(f"파일 경로가 디렉토리입니다: {file_path}")
            return False
        
        # 디렉토리가 없으면 생성
        dir_path = os.path.dirname(file_path)
        if dir_path:  # 빈 문자열이 아닌 경우에만
            os.makedirs(dir_path, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        logger.debug(f"YAML 파일 저장 완료: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"YAML 파일 저장 중 오류 ({file_path}): {e}")
        return False


def validate_yaml(content: str) -> bool:
    """
    YAML 내용의 문법을 검증합니다.
    
    Args:
        content: 검증할 YAML 내용
        
    Returns:
        bool: 유효한 YAML인지 여부
    """
    logger = logging.getLogger(__name__)
    
    if yaml is None:
        logger.error("PyYAML이 설치되지 않음")
        return False
    
    try:
        yaml.safe_load(content)
        return True
        
    except yaml.YAMLError as e:
        logger.debug(f"YAML 문법 오류: {e}")
        return False
    except Exception as e:
        logger.error(f"YAML 검증 중 예외 발생: {e}")
        return False


def parse_yaml(content: str) -> Optional[Dict[str, Any]]:
    """
    YAML 내용을 파싱하여 딕셔너리로 반환합니다.
    
    Args:
        content: 파싱할 YAML 내용
        
    Returns:
        Optional[Dict]: 파싱된 YAML 객체 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    if yaml is None:
        logger.error("PyYAML이 설치되지 않음")
        return None
    
    try:
        # GitHub Actions specific processing: handle 'on' keyword
        # Replace 'on:' with '"on":' to prevent YAML from interpreting it as boolean
        # But be careful not to replace words that contain 'on' like 'runs-on'
        processed_content = content
        import re
        # Match 'on:' only when it's at the beginning of a line (after whitespace)
        processed_content = re.sub(r'^(\s*)on:', r'\1"on":', processed_content, flags=re.MULTILINE)
        
        result = yaml.safe_load(processed_content)
        
        # If 'on' was converted to True (boolean), fix it back
        if isinstance(result, dict) and True in result:
            result['on'] = result.pop(True)
        
        return result
        
    except yaml.YAMLError as e:
        logger.error(f"YAML 파싱 오류: {e}")
        return None
    except Exception as e:
        logger.error(f"YAML 파싱 중 예외 발생: {e}")
        return None


def yaml_to_string(yaml_obj: Dict[str, Any]) -> Optional[str]:
    """
    YAML 객체를 문자열로 변환합니다.
    
    Args:
        yaml_obj: YAML 객체
        
    Returns:
        Optional[str]: YAML 문자열 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    if yaml is None:
        logger.error("PyYAML이 설치되지 않음")
        return None
    
    try:
        return yaml.dump(
            yaml_obj, 
            default_flow_style=False, 
            allow_unicode=True,
            sort_keys=False
        )
        
    except Exception as e:
        logger.error(f"YAML 객체를 문자열로 변환 중 오류: {e}")
        return None


def get_workflow_structure(content: str) -> Dict[str, Any]:
    """
    워크플로우의 구조 정보를 추출합니다.
    
    Args:
        content: YAML 내용
        
    Returns:
        Dict: 워크플로우 구조 정보
               {
                   "name": str,
                   "triggers": List[str],
                   "jobs": List[Dict],
                   "job_count": int,
                   "step_count": int
               }
    """
    logger = logging.getLogger(__name__)
    
    try:
        yaml_obj = parse_yaml(content)
        if not yaml_obj:
            return {}
        
        structure = {
            "name": yaml_obj.get("name", ""),
            "triggers": list(yaml_obj.get("on", {}).keys()) if isinstance(yaml_obj.get("on"), dict) else [],
            "jobs": [],
            "job_count": 0,
            "step_count": 0
        }
        
        jobs = yaml_obj.get("jobs", {})
        if isinstance(jobs, dict):
            structure["job_count"] = len(jobs)
            
            for job_name, job_config in jobs.items():
                if isinstance(job_config, dict):
                    steps = job_config.get("steps", [])
                    step_count = len(steps) if isinstance(steps, list) else 0
                    structure["step_count"] += step_count
                    
                    job_info = {
                        "name": job_name,
                        "runs_on": job_config.get("runs-on", ""),
                        "step_count": step_count,
                        "has_strategy": "strategy" in job_config,
                        "has_environment": "environment" in job_config
                    }
                    structure["jobs"].append(job_info)
        
        return structure
        
    except Exception as e:
        logger.error(f"워크플로우 구조 분석 중 오류: {e}")
        return {}


def extract_workflow_steps(content: str) -> List[Dict[str, Any]]:
    """
    워크플로우의 모든 스텝을 추출합니다.
    
    Args:
        content: YAML 내용
        
    Returns:
        List[Dict]: 스텝 정보 리스트
    """
    logger = logging.getLogger(__name__)
    
    try:
        yaml_obj = parse_yaml(content)
        if not yaml_obj:
            return []
        
        all_steps = []
        jobs = yaml_obj.get("jobs", {})
        
        if isinstance(jobs, dict):
            for job_name, job_config in jobs.items():
                if isinstance(job_config, dict):
                    steps = job_config.get("steps", [])
                    if isinstance(steps, list):
                        for i, step in enumerate(steps):
                            if isinstance(step, dict):
                                step_info = {
                                    "job_name": job_name,
                                    "step_index": i,
                                    "step_name": step.get("name", f"Step {i+1}"),
                                    "uses": step.get("uses", ""),
                                    "run": step.get("run", ""),
                                    "with": step.get("with", {}),
                                    "env": step.get("env", {})
                                }
                                all_steps.append(step_info)
        
        return all_steps
        
    except Exception as e:
        logger.error(f"워크플로우 스텝 추출 중 오류: {e}")
        return []


def get_action_versions(content: str) -> Dict[str, str]:
    """
    워크플로우에서 사용된 액션들과 버전을 추출합니다.
    
    Args:
        content: YAML 내용
        
    Returns:
        Dict[str, str]: 액션명과 버전의 매핑
    """
    logger = logging.getLogger(__name__)
    
    try:
        steps = extract_workflow_steps(content)
        action_versions = {}
        
        for step in steps:
            uses = step.get("uses", "")
            if uses and "@" in uses:
                action_name, version = uses.rsplit("@", 1)
                action_versions[action_name] = version
        
        return action_versions
        
    except Exception as e:
        logger.error(f"액션 버전 추출 중 오류: {e}")
        return {}


def create_temp_yaml_file(content: str, prefix: str = "workflow_") -> Optional[str]:
    """
    임시 YAML 파일을 생성합니다.
    
    Args:
        content: YAML 내용
        prefix: 파일명 접두사
        
    Returns:
        Optional[str]: 생성된 임시 파일 경로 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.yml', 
            prefix=prefix, 
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        logger.debug(f"임시 YAML 파일 생성: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"임시 YAML 파일 생성 중 오류: {e}")
        return None


def cleanup_temp_file(file_path: str) -> bool:
    """
    임시 파일을 삭제합니다.
    
    Args:
        file_path: 삭제할 파일 경로
        
    Returns:
        bool: 삭제 성공 여부
    """
    logger = logging.getLogger(__name__)
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"임시 파일 삭제 완료: {file_path}")
            return True
        else:
            logger.warning(f"삭제할 파일이 존재하지 않음: {file_path}")
            return False
            
    except Exception as e:
        logger.error(f"임시 파일 삭제 중 오류: {e}")
        return False


def validate_github_actions_workflow(content: str) -> Dict[str, Any]:
    """
    GitHub Actions 워크플로우의 유효성을 종합적으로 검증합니다.
    
    Args:
        content: YAML 내용
        
    Returns:
        Dict: 검증 결과
               {
                   "is_valid": bool,
                   "yaml_valid": bool,
                   "has_required_fields": bool,
                   "issues": List[str]
               }
    """
    logger = logging.getLogger(__name__)
    
    try:
        result = {
            "is_valid": True,
            "yaml_valid": False,
            "has_required_fields": False,
            "issues": []
        }
        
        # 1. YAML 문법 검증
        if not validate_yaml(content):
            result["yaml_valid"] = False
            result["is_valid"] = False
            result["issues"].append("Invalid YAML syntax")
            return result
        else:
            result["yaml_valid"] = True
        
        # 2. YAML 파싱
        yaml_obj = parse_yaml(content)
        logger.debug(f"파싱된 YAML 객체: {yaml_obj}")
        if not yaml_obj:
            result["is_valid"] = False
            result["issues"].append("Failed to parse YAML")
            return result
        
        # 3. 필수 필드 검증
        required_fields = ["on", "jobs"]
        for field in required_fields:
            if field not in yaml_obj:
                result["issues"].append(f"Missing required field: {field}")
                result["is_valid"] = False
        
        if result["is_valid"]:
            result["has_required_fields"] = True
        
        # 4. jobs 구조 검증
        jobs = yaml_obj.get("jobs", {})
        if not isinstance(jobs, dict) or len(jobs) == 0:
            result["issues"].append("No valid jobs found")
            result["is_valid"] = False
        
        # 5. 각 job의 필수 필드 검증
        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                result["issues"].append(f"Job '{job_name}' is not a valid object")
                result["is_valid"] = False
                continue
            
            if "runs-on" not in job_config:
                result["issues"].append(f"Job '{job_name}' missing 'runs-on'")
                result["is_valid"] = False
            
            if "steps" not in job_config:
                result["issues"].append(f"Job '{job_name}' missing 'steps'")
                result["is_valid"] = False
        
        return result
        
    except Exception as e:
        logger.error(f"워크플로우 검증 중 오류: {e}")
        return {
            "is_valid": False,
            "yaml_valid": False,
            "has_required_fields": False,
            "issues": [f"Validation error: {str(e)}"]
        }

"""
프로세스 실행 유틸리티 모듈

외부 명령어 실행 및 subprocess 관리를 담당합니다.
"""

import logging
import subprocess
import os
import tempfile
import shlex
from typing import Dict, Any, Optional, List, Union


def run_command(
    command: Union[str, List[str]],
    cwd: Optional[str] = None,
    timeout: int = 30,
    capture_output: bool = True,
    shell: bool = False
) -> Dict[str, Any]:
    """
    외부 명령어를 실행합니다.
    
    Args:
        command: 실행할 명령어 (문자열 또는 리스트)
        cwd: 작업 디렉토리
        timeout: 타임아웃 (초)
        capture_output: 출력 캡처 여부
        shell: 셸 사용 여부
        
    Returns:
        Dict: 실행 결과
              {
                  "returncode": int,
                  "stdout": str,
                  "stderr": str,
                  "success": bool,
                  "command": str,
                  "execution_time": float
              }
    """
    logger = logging.getLogger(__name__)
    
    import time
    start_time = time.time()
    
    try:
        # 명령어 문자열 처리
        if isinstance(command, str):
            if shell:
                cmd_for_log = command
                cmd_args = command
            else:
                cmd_args = shlex.split(command)
                cmd_for_log = command
        else:
            cmd_args = command
            cmd_for_log = ' '.join(command)
        
        logger.info(f"명령어 실행: {cmd_for_log}")
        
        # 프로세스 실행
        result = subprocess.run(
            cmd_args,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            shell=shell,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        execution_time = time.time() - start_time
        
        success = result.returncode == 0
        
        if success:
            logger.debug(f"명령어 실행 성공 ({execution_time:.2f}초)")
        else:
            logger.warning(f"명령어 실행 실패 (코드: {result.returncode}, 시간: {execution_time:.2f}초)")
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "success": success,
            "command": cmd_for_log,
            "execution_time": execution_time
        }
        
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        logger.error(f"명령어 실행 타임아웃 ({timeout}초)")
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "success": False,
            "command": cmd_for_log if 'cmd_for_log' in locals() else str(command),
            "execution_time": execution_time
        }
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"명령어 실행 중 오류: {e}")
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False,
            "command": cmd_for_log if 'cmd_for_log' in locals() else str(command),
            "execution_time": execution_time
        }


def run_actionlint(
    yaml_file_path: str,
    actionlint_path: str = "actionlint",
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    actionlint를 실행하여 워크플로우를 검사합니다.
    
    Args:
        yaml_file_path: 검사할 YAML 파일 경로
        actionlint_path: actionlint 실행파일 경로
        output_format: 출력 형식 ("json", "text")
        
    Returns:
        Dict: actionlint 실행 결과
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not os.path.exists(yaml_file_path):
            logger.error(f"YAML 파일이 존재하지 않음: {yaml_file_path}")
            return {
                "success": False,
                "errors": [],
                "raw_output": "",
                "error_message": "File not found"
            }
        
        # actionlint 실행파일 경로 자동 감지
        if actionlint_path == "actionlint":
            # 기본값인 경우 사용 가능한 actionlint 바이너리를 찾음
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            
            # 여러 위치에서 actionlint 바이너리 검색
            search_paths = [
                # 현재 프로젝트의 syntax_repair 디렉토리
                os.path.join(project_root, "syntax_repair", "actionlint"),
                # smell_linter 디렉토리들 (절대 경로로 수정)
                "/Users/nam/Desktop/repository/Catching-Smells/smell_linter/actionlint_mac",
                "/Users/nam/Desktop/repository/Catching-Smells/smell_linter/src/actionlint_mac",
                "/Users/nam/Desktop/repository/Catching-Smells/smell_linter/actionlint_linux",
                "/Users/nam/Desktop/repository/Catching-Smells/smell_linter/src/actionlint_linux",
            ]
            
            actionlint_found = None
            for path in search_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    actionlint_found = path
                    logger.info(f"actionlint 바이너리 발견: {actionlint_found}")
                    break
            
            if actionlint_found:
                actionlint_path = actionlint_found
            else:
                # 시스템 PATH에서 찾기 시도
                actionlint_found = find_executable("actionlint")
                if actionlint_found:
                    actionlint_path = actionlint_found
                else:
                    logger.error("actionlint 바이너리를 찾을 수 없음")
                    return {
                        "success": False,
                        "errors": [],
                        "raw_output": "",
                        "error_message": "actionlint binary not found"
                    }
        
        # actionlint 명령어 구성
        if output_format == "json":
            command = f"{actionlint_path} -format '{{{{json .}}}}' {yaml_file_path}"
        else:
            command = f"{actionlint_path} {yaml_file_path}"
        
        # actionlint 실행
        result = run_command(command, timeout=60)
        
        # actionlint는 오류가 있으면 returncode가 0이 아님
        has_errors = result["returncode"] != 0
        
        # actionlint 전용 로깅 (오류 발견은 정상 동작)
        if has_errors:
            logger.info(f"actionlint 실행 완료: 오류 발견됨 (코드: {result['returncode']})")
        else:
            logger.info("actionlint 실행 완료: 오류 없음")
        
        errors = []
        if has_errors and output_format == "json":
            try:
                import json
                # actionlint는 JSON 출력을 stdout에 보냄
                output_text = result["stdout"].strip()
                if output_text.startswith('['):
                    # JSON 배열 형태로 출력됨
                    errors = json.loads(output_text)
                else:
                    # 줄별로 JSON 객체가 출력되는 경우
                    stdout_lines = output_text.split('\n')
                    for line in stdout_lines:
                        if line.strip() and line.startswith('{'):
                            error_data = json.loads(line)
                            errors.append(error_data)
            except Exception as e:
                logger.warning(f"actionlint JSON 출력 파싱 실패: {e}")
                # JSON 파싱 실패 시 텍스트로 처리 (stdout과 stderr 모두 확인)
                output_text = result["stdout"] if result["stdout"] else result["stderr"]
                errors = output_text.strip().split('\n') if output_text else []
        
        elif has_errors:
            # 텍스트 형식 오류 처리 (stdout과 stderr 모두 확인)
            output_text = result["stdout"] if result["stdout"] else result["stderr"]
            errors = output_text.strip().split('\n') if output_text else []
        
        return {
            "success": not has_errors,
            "errors": errors,
            "raw_output": result["stdout"] if has_errors else result["stdout"],
            "error_message": "" if not has_errors else "actionlint found issues",
            "execution_time": result["execution_time"]
        }
        
    except Exception as e:
        logger.error(f"actionlint 실행 중 오류: {e}")
        return {
            "success": False,
            "errors": [],
            "raw_output": "",
            "error_message": str(e)
        }


def create_temp_script(
    script_content: str,
    script_extension: str = ".sh",
    executable: bool = True
) -> Optional[str]:
    """
    임시 스크립트 파일을 생성합니다.
    
    Args:
        script_content: 스크립트 내용
        script_extension: 스크립트 확장자
        executable: 실행 권한 부여 여부
        
    Returns:
        Optional[str]: 생성된 스크립트 파일 경로 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=script_extension,
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            temp_file.write(script_content)
            script_path = temp_file.name
        
        # 실행 권한 부여
        if executable:
            os.chmod(script_path, 0o755)
        
        logger.debug(f"임시 스크립트 생성: {script_path}")
        return script_path
        
    except Exception as e:
        logger.error(f"임시 스크립트 생성 중 오류: {e}")
        return None


def find_executable(name: str, search_paths: Optional[List[str]] = None) -> Optional[str]:
    """
    실행파일을 찾습니다.
    
    Args:
        name: 실행파일 이름
        search_paths: 추가 검색 경로 리스트
        
    Returns:
        Optional[str]: 실행파일 경로 (없으면 None)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # PATH에서 검색
        import shutil
        path = shutil.which(name)
        if path:
            logger.debug(f"실행파일 발견 (PATH): {path}")
            return path
        
        # 추가 경로에서 검색
        if search_paths:
            for search_path in search_paths:
                full_path = os.path.join(search_path, name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    logger.debug(f"실행파일 발견 (추가 경로): {full_path}")
                    return full_path
        
        # 현재 디렉토리에서 검색
        current_dir_path = os.path.join(os.getcwd(), name)
        if os.path.isfile(current_dir_path) and os.access(current_dir_path, os.X_OK):
            logger.debug(f"실행파일 발견 (현재 디렉토리): {current_dir_path}")
            return current_dir_path
        
        logger.warning(f"실행파일을 찾을 수 없음: {name}")
        return None
        
    except Exception as e:
        logger.error(f"실행파일 검색 중 오류: {e}")
        return None


def run_python_script(
    script_path: str,
    args: Optional[List[str]] = None,
    python_executable: str = "python3"
) -> Dict[str, Any]:
    """
    Python 스크립트를 실행합니다.
    
    Args:
        script_path: 스크립트 파일 경로
        args: 스크립트 인자 리스트
        python_executable: Python 실행파일
        
    Returns:
        Dict: 실행 결과
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not os.path.exists(script_path):
            logger.error(f"Python 스크립트가 존재하지 않음: {script_path}")
            return {
                "success": False,
                "stdout": "",
                "stderr": "Script file not found",
                "returncode": -1
            }
        
        # 명령어 구성
        command = [python_executable, script_path]
        if args:
            command.extend(args)
        
        # 스크립트 실행
        result = run_command(command, timeout=120)
        
        return result
        
    except Exception as e:
        logger.error(f"Python 스크립트 실행 중 오류: {e}")
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }


def run_command_with_input(
    command: Union[str, List[str]],
    input_data: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    표준 입력과 함께 명령어를 실행합니다.
    
    Args:
        command: 실행할 명령어
        input_data: 표준 입력으로 전달할 데이터
        timeout: 타임아웃 (초)
        
    Returns:
        Dict: 실행 결과
    """
    logger = logging.getLogger(__name__)
    
    try:
        if isinstance(command, str):
            cmd_args = shlex.split(command)
            cmd_for_log = command
        else:
            cmd_args = command
            cmd_for_log = ' '.join(command)
        
        logger.info(f"입력과 함께 명령어 실행: {cmd_for_log}")
        
        process = subprocess.Popen(
            cmd_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        stdout, stderr = process.communicate(input=input_data, timeout=timeout)
        
        success = process.returncode == 0
        
        return {
            "returncode": process.returncode,
            "stdout": stdout or "",
            "stderr": stderr or "",
            "success": success,
            "command": cmd_for_log
        }
        
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"명령어 실행 타임아웃 ({timeout}초)")
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "success": False,
            "command": cmd_for_log if 'cmd_for_log' in locals() else str(command)
        }
    
    except Exception as e:
        logger.error(f"입력과 함께 명령어 실행 중 오류: {e}")
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False,
            "command": cmd_for_log if 'cmd_for_log' in locals() else str(command)
        }


def kill_process_by_name(process_name: str) -> bool:
    """
    프로세스 이름으로 프로세스를 종료합니다.
    
    Args:
        process_name: 프로세스 이름
        
    Returns:
        bool: 종료 성공 여부
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Unix/Linux/macOS
        if os.name != 'nt':
            result = run_command(f"pkill -f {process_name}", timeout=10)
            return result["success"]
        # Windows
        else:
            result = run_command(f"taskkill /f /im {process_name}", timeout=10)
            return result["success"]
            
    except Exception as e:
        logger.error(f"프로세스 종료 중 오류: {e}")
        return False


def check_tool_availability() -> Dict[str, bool]:
    """
    필요한 도구들의 사용 가능성을 확인합니다.
    
    Returns:
        Dict[str, bool]: 도구별 사용 가능성
    """
    logger = logging.getLogger(__name__)
    
    tools = {
        "actionlint": ["actionlint", "actionlint_mac", "actionlint_linux"],
        "python": ["python3", "python"],
        "git": ["git"],
        "curl": ["curl"],
        "wget": ["wget"]
    }
    
    availability = {}
    
    for tool_name, possible_names in tools.items():
        found = False
        for name in possible_names:
            if find_executable(name):
                availability[tool_name] = True
                found = True
                break
        
        if not found:
            availability[tool_name] = False
            logger.warning(f"도구를 찾을 수 없음: {tool_name}")
    
    logger.info(f"도구 사용 가능성 확인 완료: {availability}")
    return availability


def run_smell_detector(yaml_file_path: str) -> Dict[str, Any]:
    """
    기존 프로젝트의 smell detector를 실행합니다.
    
    Args:
        yaml_file_path: 검사할 YAML 파일 경로
        
    Returns:
        Dict: smell detector 실행 결과
              {
                  "success": bool,
                  "smells": List[Dict],
                  "raw_output": str,
                  "error": str (실패 시)
              }
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not os.path.exists(yaml_file_path):
            logger.error(f"YAML 파일이 존재하지 않음: {yaml_file_path}")
            return {
                "success": False,
                "smells": [],
                "raw_output": "",
                "error": "File not found"
            }
        
        # 기존 gha-ci-detector 실행 (smell detection 전용 환경 사용)
        detector_path = "/Users/nam/Desktop/repository/Catching-Smells/RQ3/gha-ci-detector_paper/src"
        python_path = "/Users/nam/Desktop/repository/Catching-Smells/.venv/bin/python"
        command = f"cd {detector_path} && {python_path} -m gha_ci_detector file {yaml_file_path}"
        
        result = run_command(command, timeout=60, shell=True)
        
        logger.debug(f"Smell detector stdout: {result['stdout']}")
        logger.debug(f"Smell detector stderr: {result['stderr']}")
        logger.debug(f"Smell detector return code: {result['returncode']}")
        
        # 성공적으로 실행되었고 출력이 있는 경우
        if result["success"] and result["stdout"].strip():
            smells = _parse_smell_detector_output(result["stdout"])
            logger.info(f"Smell detector 실행 완료: {len(smells)}개 스멜 발견")
            return {
                "success": True,
                "smells": smells,
                "raw_output": result["stdout"]
            }
        # 성공했지만 출력이 없거나, stderr에 오류가 있는 경우
        elif result["success"] and not result["stdout"].strip():
            logger.warning("Smell detector가 빈 출력을 반환했습니다.")
            if result["stderr"].strip():
                logger.warning(f"Smell detector stderr: {result['stderr']}")
            return {
                "success": False,
                "smells": [],
                "raw_output": result["stdout"],
                "error": "Empty output from smell detector"
            }
        else:
            logger.warning(f"Smell detector 실행 실패: {result['stderr']}")
            return {
                "success": False,
                "smells": [],
                "raw_output": result["stdout"],
                "error": result["stderr"]
            }
            
    except Exception as e:
        logger.error(f"Smell detector 실행 중 오류: {e}")
        return {
            "success": False,
            "smells": [],
            "raw_output": "",
            "error": str(e)
        }


def _parse_smell_detector_output(output: str) -> list:
    """
    Smell detector 출력을 파싱하여 스멜 정보를 추출합니다.
    대상 스멜만 필터링: 1, 4, 5, 10, 11, 15, 16번
    
    Args:
        output: smell detector의 stdout 출력
        
    Returns:
        list: 파싱된 스멜 정보 리스트 (대상 스멜만)
    """
    logger = logging.getLogger(__name__)
    smells = []
    
    # 대상 스멜 번호 정의
    TARGET_SMELLS = {'1', '4', '5', '10', '11', '15', '16'}
    
    try:
        lines = output.strip().split('\n')
        logger.debug(f"Smell detector 출력 라인 수: {len(lines)}")
        
        # 메타데이터 라인 패턴들 (제외할 라인들)
        skip_patterns = [
            "Welcome to GHA CI Detector",
            "Detecting smells for",
            "We have found",
            "The following styling errors were found"
        ]
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            logger.debug(f"라인 {i}: {line}")
            
            # 메타데이터 라인 건너뛰기
            if any(pattern in line for pattern in skip_patterns):
                logger.debug(f"메타데이터 라인 건너뛰기: {line}")
                continue
            
            # 실제 스멜 라인 패턴: "- 숫자. 설명" 또는 "숫자:숫자: 오류"
            if (line.startswith("- ") and ". " in line) or (":" in line and ("error" in line.lower() or "warning" in line.lower())):
                # 스멜 번호와 설명 분리
                if line.startswith("- "):
                    # "- 3. Use fixed version for runs-on argument (line 7)" 형태
                    smell_text = line[2:].strip()  # "- " 제거
                    if ". " in smell_text:
                        parts = smell_text.split(". ", 1)
                        smell_number = parts[0]
                        smell_description = parts[1]
                    else:
                        smell_number = "unknown"
                        smell_description = smell_text
                    
                    # 대상 스멜 번호만 필터링
                    if smell_number in TARGET_SMELLS:
                        smells.append({
                            'type': 'code_smell',
                            'id': smell_number,
                            'description': smell_description,
                            'message': line,
                            'severity': 'medium'
                        })
                        logger.debug(f"대상 스멜 감지 (#{smell_number}): {smell_description}")
                    else:
                        logger.debug(f"대상 외 스멜 건너뛰기 (#{smell_number}): {smell_description}")
                else:
                    # "11:5: wrong indentation: expected 6 but found 4 (indentation)" 형태는 대상 스멜이 아니므로 건너뛰기
                    logger.debug(f"스타일 오류 건너뛰기 (대상 스멜 아님): {line}")
            elif "YAML parsing error" in line:
                # YAML 파싱 오류는 대상 스멜이 아니므로 건너뛰기
                logger.debug(f"파싱 오류 건너뛰기 (대상 스멜 아님): {line}")
                
    except Exception as e:
        logger.error(f"Smell 출력 파싱 중 오류: {e}")
    
    logger.info(f"총 {len(smells)}개 대상 스멜 파싱됨 (1,4,5,10,11,15,16번만)")
    return smells

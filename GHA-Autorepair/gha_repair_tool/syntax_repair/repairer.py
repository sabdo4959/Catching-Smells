"""
구문 복구 모듈

actionlint를 사용하여 기본적인 YAML 포맷 및 GHA 스키마 오류를 수정합니다.
다양한 프롬프트 모드를 지원합니다.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

from utils import process_runner
from utils import llm_api
from utils import yaml_parser


def repair_syntax(input_yaml_path: str, use_guided_prompt: bool = True) -> Optional[str]:
    """
    actionlint를 사용하여 구문 오류를 수정합니다.
    
    Args:
        input_yaml_path: 입력 YAML 파일 경로
        use_guided_prompt: 가이드 프롬프트 사용 여부
            - True: 오류 정보 포함, 다른 부분 변경 금지 제약이 있는 가이드 프롬프트
            - False: 단순 프롬프트
    
    Returns:
        str or None: 구문적으로 유효한 YAML 파일 경로 또는 실패 시 None
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1. actionlint로 오류 탐지
        logger.info("actionlint로 구문 오류 탐지 중...")
        errors = _detect_syntax_errors(input_yaml_path)
        
        if not errors:
            logger.info("구문 오류가 없습니다.")
            return input_yaml_path
        
        logger.info(f"{len(errors)}개의 구문 오류 발견")
        
        # 2. 프롬프트 생성
        prompt = _generate_repair_prompt(input_yaml_path, errors, use_guided_prompt)
        
        # 3. LLM을 통한 수정
        logger.info("LLM을 통한 구문 수정 중...")
        repaired_content = llm_api.call_llm(prompt)
        
        if not repaired_content:
            logger.error("LLM 수정 실패")
            return None
        
        # 4. 수정된 내용을 임시 파일에 저장
        temp_file = _save_to_temp_file(repaired_content)
        
        # 5. 수정된 파일을 다시 actionlint로 검증
        logger.info("수정된 파일 검증 중...")
        verification_errors = _detect_syntax_errors(temp_file)
        
        if verification_errors:
            logger.warning(f"수정 후에도 {len(verification_errors)}개의 오류가 남아있습니다.")
            # TODO: 재시도 로직 구현 가능
        
        logger.info("구문 복구 완료")
        return temp_file
        
    except Exception as e:
        logger.error(f"구문 복구 중 오류 발생: {e}")
        return None


def _detect_syntax_errors(yaml_path: str) -> list:
    """
    actionlint를 사용하여 구문 오류를 탐지합니다.
    
    Args:
        yaml_path: YAML 파일 경로
        
    Returns:
        list: 오류 정보 리스트
    """
    logger = logging.getLogger(__name__)
    
    try:
        # TODO: actionlint 실행 및 오류 정보 파싱
        # 예시 명령어: actionlint -format '{{json .}}' workflow.yml
        command = f"./actionlint -format '{{{{json .}}}}' {yaml_path}"
        result = process_runner.run_command(command)
        
        if result['returncode'] == 0:
            return []  # 오류 없음
        
        # TODO: JSON 출력을 파싱하여 구조화된 오류 정보 반환
        errors = _parse_actionlint_output(result['stderr'])
        return errors
        
    except Exception as e:
        logger.error(f"actionlint 실행 중 오류: {e}")
        return []


def _parse_actionlint_output(output: str) -> list:
    """
    actionlint 출력을 파싱하여 구조화된 오류 정보로 변환합니다.
    
    Args:
        output: actionlint의 stderr 출력
        
    Returns:
        list: 파싱된 오류 정보 리스트
    """
    # TODO: actionlint JSON 출력 파싱 로직 구현
    # 예상 구조: [{"message": "...", "line": 10, "column": 5, "kind": "..."}]
    
    errors = []
    lines = output.strip().split('\n')
    
    for line in lines:
        if line.strip():
            # 간단한 파싱 예시 (실제로는 JSON 파싱 필요)
            errors.append({
                'message': line,
                'line': 0,
                'column': 0,
                'kind': 'syntax'
            })
    
    return errors


def _generate_repair_prompt(yaml_path: str, errors: list, use_guided_prompt: bool) -> str:
    """
    수정을 위한 프롬프트를 생성합니다.
    
    Args:
        yaml_path: YAML 파일 경로
        errors: 오류 정보 리스트
        use_guided_prompt: 가이드 프롬프트 사용 여부
        
    Returns:
        str: 생성된 프롬프트
    """
    # 파일 내용 읽기
    content = yaml_parser.load_yaml_as_text(yaml_path)
    
    if use_guided_prompt:
        # syntax-check와 expression 타입의 에러만 필터링
        filtered_errors = [
            err for err in errors 
            if err.get('kind') in ['syntax-check', 'expression']
        ]
        
        # 가이드 프롬프트: 필터링된 오류 정보 포함, 제약사항 명시
        error_details = "\n".join([
            f"- Line {err.get('line', '?')}: {err.get('message', 'Unknown error')}"
            for err in filtered_errors
        ])
        
        prompt = f"""다음 GitHub Actions 워크플로우 YAML 파일에 구문 오류가 있습니다.

오류 정보 (syntax-check 및 expression 에러만):
{error_details}

원본 YAML:
```yaml
{content}
```

요구사항:
1. 위에 명시된 구문 오류만 수정하세요.
2. 워크플로우의 의미와 동작을 변경하지 마세요.
3. 오류와 관련없는 부분은 절대 변경하지 마세요.
4. 수정된 전체 YAML 파일만 반환하세요.

수정된 YAML:"""
    else:
        # 단순 프롬프트
        prompt = f"""다음 GitHub Actions 워크플로우 YAML 파일의 구문 오류를 수정해주세요.

```yaml
{content}
```

수정된 YAML:"""
    
    return prompt


def _save_to_temp_file(content: str) -> str:
    """
    내용을 임시 파일에 저장합니다.
    
    Args:
        content: 저장할 내용
        
    Returns:
        str: 임시 파일 경로
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(content)
        return f.name

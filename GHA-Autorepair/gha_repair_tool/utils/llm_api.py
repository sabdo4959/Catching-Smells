"""
LLM API 호출 유틸리티 모듈

OpenAI API 등을 이용한 LLM 호출 및 응답 처리를 담당합니다.
"""

import logging
from typing import Optional, Dict, Any, List
import json
import time

try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    OpenAI = None
    openai_available = False


class LLMAPIError(Exception):
    """LLM API 관련 예외"""
    pass


def call_llm(
    prompt: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 2000,
    temperature: float = 0.1,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    LLM API를 호출하여 응답을 받습니다.
    
    Args:
        prompt: 프롬프트
        model: 사용할 모델명
        max_tokens: 최대 토큰 수
        temperature: 응답의 랜덤성 (0.0 ~ 1.0)
        api_key: API 키 (None이면 환경변수 사용)
        
    Returns:
        Optional[str]: LLM 응답 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    if not openai_available:
        logger.error("OpenAI 라이브러리가 설치되지 않음")
        return None
    
    try:
        # OpenAI 클라이언트 생성
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            client = OpenAI()  # 환경변수에서 OPENAI_API_KEY 사용
        
        logger.info(f"LLM API 호출 시작 (모델: {model})")
        
        # API 호출 (새로운 v1.0.0+ 형식)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=60
        )
        
        # 응답 추출
        if response and response.choices:
            content = response.choices[0].message.content
            logger.info("LLM API 호출 성공")
            return content
        else:
            logger.error("LLM API 응답이 비어있음")
            return None
            
    except Exception as e:
        logger.error(f"LLM API 호출 중 오류: {e}")
        return None


def call_llm_with_retry(
    prompt: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs
) -> Optional[str]:
    """
    재시도 로직이 포함된 LLM API 호출.
    
    Args:
        prompt: 프롬프트
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간격 (초)
        **kwargs: call_llm에 전달될 추가 인자들
        
    Returns:
        Optional[str]: LLM 응답 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries + 1):
        try:
            result = call_llm(prompt, **kwargs)
            if result:
                return result
            
            if attempt < max_retries:
                logger.warning(f"LLM API 호출 실패, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # 지수 백오프
            
        except Exception as e:
            logger.error(f"LLM API 호출 시도 {attempt + 1} 실패: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
    
    logger.error(f"모든 재시도 실패, 총 {max_retries + 1}회 시도함")
    return None


def call_llm_batch(
    prompts: List[str],
    batch_size: int = 5,
    delay_between_batches: float = 1.0,
    **kwargs
) -> List[Optional[str]]:
    """
    여러 프롬프트를 배치로 처리합니다.
    
    Args:
        prompts: 프롬프트 리스트
        batch_size: 배치 크기
        delay_between_batches: 배치 간 지연 시간 (초)
        **kwargs: call_llm에 전달될 추가 인자들
        
    Returns:
        List[Optional[str]]: 응답 리스트
    """
    logger = logging.getLogger(__name__)
    
    results = []
    total_prompts = len(prompts)
    
    logger.info(f"배치 LLM 호출 시작: {total_prompts}개 프롬프트, 배치 크기: {batch_size}")
    
    for i in range(0, total_prompts, batch_size):
        batch = prompts[i:i + batch_size]
        batch_results = []
        
        logger.info(f"배치 {i // batch_size + 1} 처리 중 ({len(batch)}개 프롬프트)")
        
        for prompt in batch:
            result = call_llm_with_retry(prompt, **kwargs)
            batch_results.append(result)
        
        results.extend(batch_results)
        
        # 배치 간 지연
        if i + batch_size < total_prompts:
            time.sleep(delay_between_batches)
    
    logger.info(f"배치 처리 완료: {len([r for r in results if r])}개 성공")
    return results


def validate_llm_response(
    response: str,
    expected_format: str = "yaml"
) -> Dict[str, Any]:
    """
    LLM 응답의 유효성을 검증합니다.
    
    Args:
        response: LLM 응답
        expected_format: 예상 형식 ("yaml", "json", "text")
        
    Returns:
        Dict: 검증 결과
               {
                   "is_valid": bool,
                   "format_valid": bool,
                   "content": str,
                   "issues": List[str]
               }
    """
    logger = logging.getLogger(__name__)
    
    result = {
        "is_valid": True,
        "format_valid": False,
        "content": response,
        "issues": []
    }
    
    try:
        if not response or not response.strip():
            result["is_valid"] = False
            result["issues"].append("Empty response")
            return result
        
        # 형식별 검증
        if expected_format == "yaml":
            try:
                # yaml_parser 모듈 사용
                from utils import yaml_parser
                yaml_parser.validate_yaml(response)
                result["format_valid"] = True
            except Exception as e:
                result["issues"].append(f"Invalid YAML format: {e}")
                result["is_valid"] = False
        
        elif expected_format == "json":
            try:
                json.loads(response)
                result["format_valid"] = True
            except Exception as e:
                result["issues"].append(f"Invalid JSON format: {e}")
                result["is_valid"] = False
        
        elif expected_format == "text":
            result["format_valid"] = True
        
        # 길이 검증
        if len(response) < 10:
            result["issues"].append("Response too short")
            result["is_valid"] = False
        
        if len(response) > 10000:
            result["issues"].append("Response too long")
            # 너무 길어도 유효하다고 간주
        
        return result
        
    except Exception as e:
        logger.error(f"응답 검증 중 오류: {e}")
        result["is_valid"] = False
        result["issues"].append(f"Validation error: {e}")
        return result


def extract_code_from_response(response: str, language: str = "yaml") -> Optional[str]:
    """
    LLM 응답에서 코드 블록을 추출합니다.
    
    Args:
        response: LLM 응답
        language: 코드 언어 ("yaml", "json", "bash" 등)
        
    Returns:
        Optional[str]: 추출된 코드 (없으면 None)
    """
    try:
        import re
        
        # 언어별 코드 블록 패턴
        patterns = [
            rf'```{language}\s*\n(.*?)```',
            r'```\s*\n(.*?)```',
            rf'```{language}(.*?)```',
            r'```(.*?)```'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                extracted = matches[0].strip()
                # 주석 줄 제거 (# 수정된 워크플로우 같은 줄)
                lines = extracted.split('\n')
                filtered_lines = []
                for line in lines:
                    # 첫 번째 라인이 주석이고 "수정된"이나 "repaired" 등의 키워드가 있으면 제거
                    if (len(filtered_lines) == 0 and 
                        line.strip().startswith('#') and 
                        ('수정된' in line or 'repaired' in line.lower() or 'fixed' in line.lower())):
                        continue
                    filtered_lines.append(line)
                return '\n'.join(filtered_lines).strip()
        
        # 코드 블록이 없으면 전체 응답에서 추출 시도
        if language == "yaml":
            # YAML 같은 패턴 찾기
            yaml_pattern = r'(name:\s*.*?(?:\n.*?)*)'
            match = re.search(yaml_pattern, response, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
        
    except Exception as e:
        logging.getLogger(__name__).error(f"코드 추출 중 오류: {e}")
        return None


def format_prompt_for_repair(
    workflow_content: str,
    error_info: Dict[str, Any],
    repair_mode: str = "guided",
    additional_context: str = ""
) -> str:
    """
    워크플로우 수정을 위한 표준화된 프롬프트를 생성합니다.
    
    Args:
        workflow_content: 워크플로우 YAML 내용
        error_info: 오류 정보
        repair_mode: 수정 모드 ("guided" 또는 "simple")
        additional_context: 추가 컨텍스트
        
    Returns:
        str: 생성된 프롬프트
    """
    error_type = error_info.get('type', 'unknown')
    error_message = error_info.get('message', '')
    line_number = error_info.get('line', 0)
    
    base_prompt = f"""
GitHub Actions 워크플로우에서 오류가 발견되었습니다. 이를 수정해주세요.

**오류 정보:**
- 타입: {error_type}
- 메시지: {error_message}
- 라인: {line_number}

**원본 워크플로우:**
```yaml
{workflow_content}
```
"""
    
    if additional_context:
        base_prompt += f"\n**추가 컨텍스트:**\n{additional_context}\n"
    
    if repair_mode == "guided":
        base_prompt += """
**수정 요구사항:**
1. 오류를 정확히 식별하고 수정하세요
2. GitHub Actions의 모범 사례를 따르세요
3. 기존 워크플로우의 의도를 유지하세요
4. 수정된 전체 YAML을 제공하고, 변경사항을 설명하세요

**응답 형식:**
```yaml
# 수정된 워크플로우
```

**변경사항 설명:**
- [변경사항 설명]
"""
    else:  # simple mode
        base_prompt += """
**요청:**
위 오류를 수정한 완전한 YAML 워크플로우를 제공해주세요.

```yaml
# 수정된 워크플로우
```
"""
    
    return base_prompt


def get_model_info(model: str) -> Dict[str, Any]:
    """
    모델 정보를 반환합니다.
    
    Args:
        model: 모델명
        
    Returns:
        Dict: 모델 정보
    """
    model_info = {
        "gpt-3.5-turbo": {
            "max_tokens": 4096,
            "cost_per_1k_tokens": 0.002,
            "good_for": ["syntax_repair", "simple_semantic_repair"]
        },
        "gpt-4": {
            "max_tokens": 8192,
            "cost_per_1k_tokens": 0.03,
            "good_for": ["complex_semantic_repair", "guided_repair"]
        },
        "gpt-4-turbo": {
            "max_tokens": 128000,
            "cost_per_1k_tokens": 0.01,
            "good_for": ["large_workflows", "complex_analysis"]
        }
    }
    
    return model_info.get(model, {
        "max_tokens": 4096,
        "cost_per_1k_tokens": 0.002,
        "good_for": ["general"]
    })


def estimate_token_cost(prompt: str, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """
    토큰 수와 예상 비용을 계산합니다.
    
    Args:
        prompt: 프롬프트
        model: 모델명
        
    Returns:
        Dict: 토큰 정보
               {
                   "estimated_tokens": int,
                   "estimated_cost": float,
                   "model": str
               }
    """
    # 간단한 토큰 추정 (1 토큰 ≈ 4 characters)
    estimated_tokens = len(prompt) // 4
    
    model_info = get_model_info(model)
    cost_per_1k = model_info.get("cost_per_1k_tokens", 0.002)
    estimated_cost = (estimated_tokens / 1000) * cost_per_1k
    
    return {
        "estimated_tokens": estimated_tokens,
        "estimated_cost": estimated_cost,
        "model": model
    }

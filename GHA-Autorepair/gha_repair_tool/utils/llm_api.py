"""
LLM API 호출 유틸리티 모듈

OpenAI API와 Ollama API를 지원하여 다양한 LLM 모델을 사용할 수 있습니다.
"""

import logging
import os
import re
from typing import Optional, Dict, Any, List
import json
import time
from enum import Enum

try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    OpenAI = None
    openai_available = False

try:
    import requests
    requests_available = True
except ImportError:
    requests_available = False


class LLMProvider(Enum):
    """지원되는 LLM 제공자"""
    OPENAI = "openai"
    OLLAMA = "ollama"


# Ollama 지원 모델 목록
OLLAMA_MODELS = {
    "llama3.1:8b": "llama3.1:8b-instruct-fp16",
    "codegemma:7b": "codegemma:7b-instruct-v1.1-fp16",
    "codellama:7b": "codellama:7b-instruct-fp16"
}

# OpenAI 지원 모델 목록
OPENAI_MODELS = {
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o", 
    "gpt-4-turbo": "gpt-4-turbo-preview",
    "gpt-4": "gpt-4",
    "gpt-3.5-turbo": "gpt-3.5-turbo"
}


class LLMAPIError(Exception):
    """LLM API 관련 예외"""
    pass


def call_openai_api(
    prompt: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 2000,
    temperature: float = 0.0,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    OpenAI API를 호출하여 응답을 받습니다.
    
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
        # API 키 우선순위: 파라미터 > 환경변수 > 기본값
        final_api_key = api_key or os.getenv("OPENAI_API_KEY") or ""
        
        # OpenAI 클라이언트 생성
        client = OpenAI(api_key=final_api_key)
        
        logger.info(f"OpenAI API 호출 시작 (모델: {model})")
        
        # API 호출
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=180  # 60초에서 180초로 증가 (복잡한 파일 처리 위해)
        )
        
        # 응답 추출
        if response and response.choices:
            content = response.choices[0].message.content
            logger.info("OpenAI API 호출 성공")
            return content
        else:
            logger.error("OpenAI API 응답이 비어있음")
            return None
            
    except Exception as e:
        logger.error(f"OpenAI API 호출 중 오류: {e}")
        return None


def call_ollama_api(
    prompt: str,
    model: str = "llama3.1:8b-instruct-fp16",
    ollama_url: str = "http://115.145.178.160:11434/api/chat",
    temperature: float = 0.1,
    timeout: int = 300
) -> Optional[str]:
    """
    Ollama API를 호출하여 응답을 받습니다.
    
    Args:
        prompt: 프롬프트
        model: 사용할 모델명
        ollama_url: Ollama 서버 URL
        temperature: 응답의 랜덤성 (0.0 ~ 1.0)
        timeout: 요청 타임아웃 (초)
        
    Returns:
        Optional[str]: LLM 응답 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    if not requests_available:
        logger.error("requests 라이브러리가 설치되지 않음")
        return None
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    try:
        logger.info(f"Ollama API 호출 시작 (모델: {model}, URL: {ollama_url})")
        
        response = requests.post(ollama_url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        result = response.json()
        content = result.get('message', {}).get('content', '').strip()
        
        # YAML 코드 블록이 있다면 제거
        if content.startswith('```yaml'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
            
        content = content.strip()
        
        logger.info("Ollama API 호출 성공")
        return content
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama API 호출 중 네트워크 오류: {e}")
        return None
    except Exception as e:
        logger.error(f"Ollama API 호출 중 오류: {e}")
        return None


def call_llm(
    prompt: str,
    provider: LLMProvider = LLMProvider.OPENAI,
    model: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.1,
    api_key: Optional[str] = None,
    ollama_url: str = "http://115.145.178.160:11434/api/chat",
    timeout: int = 300
) -> Optional[str]:
    """
    LLM API를 호출하여 응답을 받습니다. (통합 인터페이스)
    
    Args:
        prompt: 프롬프트
        provider: LLM 제공자 (OPENAI 또는 OLLAMA)
        model: 사용할 모델명 (None이면 기본값 사용)
        max_tokens: 최대 토큰 수 (OpenAI만 해당)
        temperature: 응답의 랜덤성 (0.0 ~ 1.0)
        api_key: API 키 (OpenAI만 해당, None이면 환경변수 사용)
        ollama_url: Ollama 서버 URL (Ollama만 해당)
        timeout: 요청 타임아웃 (초)
        
    Returns:
        Optional[str]: LLM 응답 (실패 시 None)
    """
    logger = logging.getLogger(__name__)
    
    # 기본 모델 설정
    if model is None:
        if provider == LLMProvider.OPENAI:
            model = "gpt-4o-mini"
        elif provider == LLMProvider.OLLAMA:
            model = "llama3.1:8b-instruct-fp16"
    
    # 제공자별 API 호출
    if provider == LLMProvider.OPENAI:
        logger.info(f"OpenAI 제공자로 LLM 호출: {model}")
        return call_openai_api(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_key
        )
    elif provider == LLMProvider.OLLAMA:
        logger.info(f"Ollama 제공자로 LLM 호출: {model}")
        return call_ollama_api(
            prompt=prompt,
            model=model,
            ollama_url=ollama_url,
            temperature=temperature,
            timeout=timeout
        )
    else:
        logger.error(f"지원되지 않는 LLM 제공자: {provider}")
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
        
        logger.info(f"배치 {i//batch_size + 1} 처리 중: {len(batch)}개 프롬프트")
        
        for j, prompt in enumerate(batch):
            logger.debug(f"  프롬프트 {i + j + 1}/{total_prompts} 처리 중...")
            result = call_llm(prompt, **kwargs)
            batch_results.append(result)
            
            # 배치 내 요청 간 지연 (API 레이트 제한 방지)
            if j < len(batch) - 1:
                time.sleep(0.1)
        
        results.extend(batch_results)
        
        # 배치 간 지연
        if i + batch_size < total_prompts:
            logger.info(f"다음 배치 전 {delay_between_batches}초 대기...")
            time.sleep(delay_between_batches)
    
    logger.info(f"배치 LLM 호출 완료: {len(results)}개 응답")
    return results


# 하위 호환성을 위한 별칭 함수들
def call_openai(prompt: str, **kwargs) -> Optional[str]:
    """OpenAI API 호출 (하위 호환성)"""
    return call_llm(prompt, provider=LLMProvider.OPENAI, **kwargs)


def call_ollama(prompt: str, **kwargs) -> Optional[str]:
    """Ollama API 호출 (하위 호환성)"""
    return call_llm(prompt, provider=LLMProvider.OLLAMA, **kwargs)


# 기존 함수명과의 호환성을 위한 별칭 (기존 코드가 이 함수를 사용할 수 있음)
def call_llm_openai(prompt: str, **kwargs) -> Optional[str]:
    """기존 코드 호환성을 위한 OpenAI 호출"""
    return call_openai_api(prompt, **kwargs)


def get_available_providers() -> List[str]:
    """사용 가능한 LLM 제공자 목록을 반환합니다."""
    providers = []
    
    if openai_available:
        providers.append("openai")
    
    if requests_available:
        providers.append("ollama")
    
    return providers


def create_workflow_repair_prompt(workflow_content: str) -> str:
    """워크플로우 수리를 위한 표준 프롬프트를 생성합니다."""
    return f"""
You are an expert in GitHub Actions workflow optimization and security. Please analyze and improve the following GitHub Actions workflow file to fix common issues and smells.

Focus on improving:
1. Security issues (outdated actions, permissions)
2. Performance issues (timeout settings, caching)
3. Reliability issues (race conditions, resource limits)
4. Best practices (concurrency, error handling)

Original workflow:
```yaml
{workflow_content}
```

Please provide ONLY the improved YAML content without any explanations or markdown formatting. The output should be valid YAML that can be directly saved to a file.
"""


def extract_code_from_response(response: str, language: str = "yaml") -> Optional[str]:
    """
    LLM 응답에서 코드 블록을 추출합니다.
    
    Args:
        response: LLM 응답 텍스트
        language: 추출할 코드 언어 (yaml, python 등)
        
    Returns:
        Optional[str]: 추출된 코드 (실패 시 None)
    """
    if not response:
        return None
    
    # 언어별 코드 블록 패턴
    patterns = [
        f"```{language}\\s*\\n(.*?)\\n```",  # ```yaml ... ```
        f"```\\s*\\n(.*?)\\n```",           # ``` ... ```
        f"```{language}(.*?)```",           # ```yaml...```
        f"```(.*?)```"                     # ```...```
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        if matches:
            # 가장 긴 매치를 선택 (더 완전할 가능성)
            code = max(matches, key=len).strip()
            return code
    
    # 코드 블록이 없으면 전체 응답 반환 (이미 코드일 수 있음)
    return response.strip()


def validate_llm_response(response: str) -> bool:
    """
    LLM 응답의 유효성을 검증합니다.
    
    Args:
        response: 검증할 응답
        
    Returns:
        bool: 유효하면 True
    """
    if not response or not response.strip():
        return False
    
    # 기본적인 유효성 검사
    if len(response.strip()) < 10:
        return False
    
    # 에러 메시지 패턴 검사
    error_patterns = [
        r"I cannot|I can't|I'm sorry|I apologize",
        r"error|Error|ERROR",
        r"invalid|Invalid|INVALID"
    ]
    
    for pattern in error_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            return False
    
    return True


def format_prompt_for_repair(workflow_content: str, issues: List[str] = None) -> str:
    """
    워크플로우 수리를 위한 프롬프트를 포맷팅합니다.
    
    Args:
        workflow_content: 워크플로우 내용
        issues: 발견된 이슈 목록
        
    Returns:
        str: 포맷팅된 프롬프트
    """
    base_prompt = f"""
You are an expert in GitHub Actions workflow optimization and security. Please analyze and improve the following GitHub Actions workflow file to fix common issues and smells.

Focus on improving:
1. Security issues (outdated actions, permissions)
2. Performance issues (timeout settings, caching)
3. Reliability issues (race conditions, resource limits)
4. Best practices (concurrency, error handling)
"""
    
    if issues:
        issues_text = "\n".join(f"- {issue}" for issue in issues)
        base_prompt += f"\n\nSpecific issues to address:\n{issues_text}"
    
    base_prompt += f"""

Original workflow:
```yaml
{workflow_content}
```

Please provide ONLY the improved YAML content without any explanations or markdown formatting. The output should be valid YAML that can be directly saved to a file.
"""
    
    return base_prompt


def get_model_info() -> Dict[str, Any]:
    """
    현재 사용 중인 모델 정보를 반환합니다.
    
    Returns:
        Dict[str, Any]: 모델 정보
    """
    provider = _get_current_provider()
    
    if provider == LLMProvider.OPENAI:
        model_key = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        actual_model = OPENAI_MODELS.get(model_key, model_key)
        return {
            "provider": "openai",
            "model_key": model_key,
            "actual_model": actual_model,
            "available": openai_available,
            "supported_models": list(OPENAI_MODELS.keys())
        }
    elif provider == LLMProvider.OLLAMA:
        model_key = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        actual_model = OLLAMA_MODELS.get(model_key, model_key)
        return {
            "provider": "ollama",
            "model_key": model_key,
            "actual_model": actual_model,
            "url": os.getenv("OLLAMA_URL", "http://115.145.178.160:11434/api/chat"),
            "available": requests_available,
            "supported_models": list(OLLAMA_MODELS.keys())
        }
    else:
        return {"provider": "unknown", "available": False}


def get_available_ollama_models() -> List[str]:
    """
    사용 가능한 Ollama 모델 목록을 반환합니다.
    
    Returns:
        List[str]: 모델 키 목록
    """
    return list(OLLAMA_MODELS.keys())


def get_available_openai_models() -> List[str]:
    """
    사용 가능한 OpenAI 모델 목록을 반환합니다.
    
    Returns:
        List[str]: 모델 키 목록
    """
    return list(OPENAI_MODELS.keys())


def validate_model_for_provider(provider: LLMProvider, model: str) -> bool:
    """
    특정 제공자에 대해 모델이 유효한지 검증합니다.
    
    Args:
        provider: LLM 제공자
        model: 모델 키
        
    Returns:
        bool: 유효하면 True
    """
    if provider == LLMProvider.OPENAI:
        return model in OPENAI_MODELS
    elif provider == LLMProvider.OLLAMA:
        return model in OLLAMA_MODELS
    return False


def estimate_token_cost(prompt: str, max_tokens: int = 2000) -> Dict[str, float]:
    """
    토큰 비용을 추정합니다 (OpenAI 기준).
    
    Args:
        prompt: 입력 프롬프트
        max_tokens: 최대 출력 토큰
        
    Returns:
        Dict[str, float]: 예상 비용 정보
    """
    # 대략적인 토큰 계산 (1 토큰 ≈ 4글자)
    input_tokens = len(prompt) // 4
    output_tokens = max_tokens
    
    # GPT-4o-mini 가격 (2024년 기준, $0.00015/1K input, $0.0006/1K output)
    input_cost = (input_tokens / 1000) * 0.00015
    output_cost = (output_tokens / 1000) * 0.0006
    total_cost = input_cost + output_cost
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": input_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": total_cost
    }


def _get_current_provider() -> LLMProvider:
    """환경변수를 기반으로 현재 사용할 LLM 제공자를 결정합니다."""
    provider_env = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider_env == "ollama":
        return LLMProvider.OLLAMA
    else:
        return LLMProvider.OPENAI


def call_llm(
    prompt: str,
    model: str = None,
    max_tokens: int = 2000,
    temperature: float = 0.1,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    기존 main.py와 호환되는 LLM 호출 함수.
    환경변수 LLM_PROVIDER로 제공자 선택 가능.
    
    환경변수 설정 예시:
    - export LLM_PROVIDER=ollama
    - export OLLAMA_MODEL=llama3.1:8b
    - export OLLAMA_URL=http://115.145.178.160:11434/api/chat
    
    Args:
        prompt: 프롬프트
        model: 사용할 모델명 (환경변수로 재정의 가능)
        max_tokens: 최대 토큰 수
        temperature: 응답의 랜덤성
        api_key: API 키
        
    Returns:
        Optional[str]: LLM 응답
    """
    logger = logging.getLogger(__name__)
    provider = _get_current_provider()
    
    # 환경변수에서 모델명 가져오기
    if provider == LLMProvider.OPENAI:
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        logger.info(f"OpenAI 모델 사용: {model}")
        
        return call_openai_api(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_key
        )
    
    elif provider == LLMProvider.OLLAMA:
        if model is None:
            model_key = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        else:
            model_key = model
        
        # 실제 모델명 가져오기
        actual_model = OLLAMA_MODELS.get(model_key, model_key)
        ollama_url = os.getenv("OLLAMA_URL", "http://115.145.178.160:11434/api/chat")
        logger.info(f"Ollama 모델 사용: {model_key} -> {actual_model}")
        
        return call_ollama_api(
            prompt=prompt,
            model=actual_model,
            ollama_url=ollama_url,
            temperature=temperature,
            timeout=300
        )
    
    else:
        logger.error(f"지원되지 않는 LLM 제공자: {provider}")
        return None


# 사용 예시 및 도움말
if __name__ == "__main__":
    # 예시 사용법
    print("=" * 60)
    print("🤖 LLM API 모듈 정보")
    print("=" * 60)
    
    print("🔧 사용 가능한 LLM 제공자:", get_available_providers())
    print("📊 현재 모델 정보:", get_model_info())
    
    print("\n📋 지원되는 Ollama 모델:")
    for i, model in enumerate(get_available_ollama_models(), 1):
        actual = OLLAMA_MODELS[model]
        print(f"   {i:2d}. {model} -> {actual}")
    
    print("\n📋 지원되는 OpenAI 모델:")
    for i, model in enumerate(get_available_openai_models(), 1):
        print(f"   {i:2d}. {model}")
    
    print("\n🔧 환경변수 설정 예시:")
    print("   # Ollama 사용")
    print("   export LLM_PROVIDER=ollama")
    print("   export OLLAMA_MODEL=llama3.1:8b")
    print("   export OLLAMA_URL=http://115.145.178.160:11434/api/chat")
    print()
    print("   # OpenAI 사용")  
    print("   export LLM_PROVIDER=openai")
    print("   export OPENAI_MODEL=gpt-4o-mini")
    print("   export OPENAI_API_KEY=your_api_key")
    
    print("\n📝 main.py 사용 예시:")
    print("   # Ollama로 실행")
    print("   LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1:8b python main.py --input file.yml --output . --mode baseline")
    print()
    print("   # 다른 모델로 실행")
    print("   LLM_PROVIDER=ollama OLLAMA_MODEL=codegemma:7b python main.py --input file.yml --output . --mode baseline")
    print("   LLM_PROVIDER=ollama OLLAMA_MODEL=codellama:7b python main.py --input file.yml --output . --mode baseline")
    print()
    print("   # OpenAI로 실행")  
    print("   LLM_PROVIDER=openai OPENAI_MODEL=gpt-4o python main.py --input file.yml --output . --mode baseline")
    
    print("=" * 60)

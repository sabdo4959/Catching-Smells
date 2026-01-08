#!/usr/bin/env python3
"""
GHA-Repair Tool Main Entry Point

이 스크립트는 GitHub Actions 워크플로우를 위한 2단계 자동 복구 프로세스의 진입점입니다.
Ablation Study를 위한 다양한 실행 모드를 지원합니다.

실행 모드:
- baseline: 구문+스멜 통합 요청으로 한 번에 처리
- two_phase_simple: 2단계 처리 (단순 프롬프트 사용)
- gha_repair: 2단계 처리 (가이드 프롬프트 사용)
"""

import argparse
import logging
import sys
from pathlib import Path

# 모듈 임포트
from syntax_repair import repairer as syntax_repairer
from semantic_repair import detector as semantic_detector
from semantic_repair import repairer as semantic_repairer
#from verification import verifier
from utils import llm_api
from utils import yaml_parser


def setup_logging(log_level="INFO"):
    """로깅 설정을 초기화합니다."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def main():
    """메인 함수: 명령줄 인수를 파싱하고 선택된 모드에 따라 실행합니다."""
    parser = argparse.ArgumentParser(
        description="GHA-Repair: GitHub Actions 워크플로우 자동 복구 도구"
    )
    
    parser.add_argument(
        "--input", 
        required=True, 
        type=str,
        help="입력 YAML 워크플로우 파일 경로"
    )
    
    parser.add_argument(
        "--output", 
        type=str,
        help="출력 복구된 YAML 파일 경로 (지정하지 않으면 자동 생성)"
    )
    
    parser.add_argument(
        "--mode", 
        choices=['baseline', 'two_phase_simple', 'gha_repair', 'poc_test'],
        default='gha_repair',
        help="실행 모드 선택 (기본값: gha_repair, poc_test: 기본 기능 테스트)"
    )
    
    parser.add_argument(
        "--verify", 
        action='store_true',
        help="복구 후 동치성 검증 수행 여부"
    )
    
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="로그 레벨 설정 (기본값: INFO)"
    )
    
    args = parser.parse_args()
    
    # 로깅 설정
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"GHA-Repair 도구 시작 (모드: {args.mode})")
    logger.info(f"입력 파일: {args.input}")
    logger.info(f"출력 파일: {args.output}")
    
    # 입력 파일 존재 확인
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"입력 파일을 찾을 수 없습니다: {args.input}")
        sys.exit(1)
    
    # 출력 파일 경로 자동 생성 (지정되지 않은 경우)
    if not args.output:
        input_stem = input_path.stem  # 확장자 제외한 파일명
        input_dir = input_path.parent
        args.output = str(input_dir / f"{input_stem}_repaired.yml")
        logger.info(f"출력 파일 경로 자동 생성: {args.output}")
    else:
        # 출력 경로가 디렉토리인 경우 파일명 추가
        output_path = Path(args.output)
        if output_path.is_dir():
            input_stem = input_path.stem
            args.output = str(output_path / f"{input_stem}_repaired.yml")
            logger.info(f"디렉토리 경로 감지, 파일명 추가: {args.output}")
    
    logger.info(f"출력 파일: {args.output}")
    
    try:
        # 선택된 모드에 따라 실행
        if args.mode == 'baseline':
            logger.info("Baseline 모드로 실행 중...")
            result = run_baseline_mode(args.input, args.output)
            
        elif args.mode == 'two_phase_simple':
            logger.info("Two-phase Simple 모드로 실행 중...")
            result = run_two_phase_mode(args.input, args.output, use_guided_prompt=False)
            
        elif args.mode == 'gha_repair':
            logger.info("GHA-Repair 모드로 실행 중...")
            result = run_two_phase_mode(args.input, args.output, use_guided_prompt=True)
            
        elif args.mode == 'poc_test':
            logger.info("POC 테스트 모드로 실행 중...")
            result = run_poc_test(args.input, args.output)
        
        if result:
            logger.info(f"작업 완료: {args.output}")
            
            # 동치성 검증 수행 (옵션)
            if args.verify and args.mode != 'poc_test':
                logger.info("동치성 검증 수행 중...")
                #verification_result = verifier.verify_equivalence(args.input, args.output)
                #logger.info(f"검증 결과: {verification_result}")
        else:
            logger.error("작업 실패")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        sys.exit(1)


def run_baseline_mode(input_path: str, output_path: str) -> bool:
    """
    Baseline 모드: actionlint + smell detector 결과를 통합하여 한 번에 처리
    
    Args:
        input_path: 입력 YAML 파일 경로
        output_path: 출력 YAML 파일 경로
        
    Returns:
        bool: 성공 여부
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== Baseline 모드 시작 ===")
        
        # 1. 원본 YAML 내용 읽기
        logger.info("1단계: 원본 워크플로우 읽기")
        original_content = yaml_parser.read_yaml_content(input_path)
        if not original_content:
            logger.error("워크플로우 파일 읽기 실패")
            return False
        
        # 2. actionlint 실행
        logger.info("2단계: actionlint 구문 검사 실행")
        from utils import process_runner
        actionlint_result = process_runner.run_actionlint(input_path)
        
        actionlint_errors = []
        if not actionlint_result.get("success", True):
            all_errors = actionlint_result.get("errors", [])
            # syntax-check와 expression 타입의 에러만 필터링
            actionlint_errors = [
                error for error in all_errors 
                if isinstance(error, dict) and error.get('kind') in ['syntax-check', 'expression']
            ]
            logger.info(f"actionlint에서 {len(actionlint_errors)}개 오류 발견 (syntax-check 및 expression만)")
        else:
            logger.info("actionlint 검사 통과")
        
        # 3. smell detector 실행 (기존 프로젝트 연동)
        logger.info("3단계: Smell Detector 실행")
        smell_result = process_runner.run_smell_detector(input_path)
        
        detected_smells = smell_result.get("smells", [])
        logger.info(f"Smell detector에서 {len(detected_smells)}개 스멜 발견")
        
        # 4. 통합 프롬프트 생성
        logger.info("4단계: 통합 프롬프트 생성")
        integrated_prompt = create_baseline_prompt(
            original_content, 
            actionlint_errors, 
            detected_smells
        )
        
        # 디버그: 프롬프트 내용 확인
        logger.debug("생성된 프롬프트:")
        logger.debug(integrated_prompt[:500] + "...")  # 처음 500자만 로그
        
        # 5. LLM 호출
        logger.info("5단계: LLM API 호출")
        llm_response = llm_api.call_llm_with_retry(integrated_prompt, max_tokens=6000)
        
        if not llm_response:
            logger.error("LLM API 호출 실패")
            return False
        
        # 6. 응답에서 YAML 추출
        logger.info("6단계: 수정된 YAML 추출")
        repaired_yaml = llm_api.extract_code_from_response(llm_response, "yaml")
        
        if not repaired_yaml:
            logger.warning("YAML 코드 블록을 찾을 수 없음, 전체 응답 사용")
            repaired_yaml = llm_response.strip()
        
        logger.debug(f"추출된 YAML:\n{repaired_yaml}")
        
        # 7. 결과 검증 및 저장
        logger.info("7단계: 결과 검증 및 저장")
        logger.debug(f"검증할 YAML 길이: {len(repaired_yaml)} 문자")
        logger.debug(f"YAML 시작 부분: {repr(repaired_yaml[:100])}")
        validation_result = yaml_parser.validate_github_actions_workflow(repaired_yaml)
        
        if validation_result.get("is_valid", False):
            success = yaml_parser.write_yaml_content(repaired_yaml, output_path)
            if success:
                logger.info("Baseline 모드 복구 완료")
                logger.info(f"수정된 파일: {output_path}")
                return True
            else:
                logger.error("수정된 파일 저장 실패")
                return False
        else:
            logger.error("수정된 YAML이 유효하지 않음")
            logger.error(f"검증 오류: {validation_result.get('issues', [])}")
            # 유효하지 않아도 일단 저장해보기
            yaml_parser.write_yaml_content(repaired_yaml, output_path)
            return False
            
    except Exception as e:
        logger.error(f"Baseline 모드 실행 중 오류: {e}")
        return False


def run_two_phase_mode(input_path: str, output_path: str, use_guided_prompt: bool = True) -> bool:
    """
    2단계 모드: actionlint → LLM → smell detection → LLM
    
    Args:
        input_path: 입력 YAML 파일 경로
        output_path: 출력 YAML 파일 경로
        use_guided_prompt: 가이드 프롬프트 사용 여부
        
    Returns:
        bool: 성공 여부
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1단계: 파일 읽기
        logger.info("=== 2단계 모드 시작 ===")
        logger.info("1단계: 입력 파일 읽기")
        yaml_content = yaml_parser.read_yaml_content(input_path)
        
        if not yaml_content:
            logger.error("입력 파일 읽기 실패")
            return False
        
        logger.info(f"파일 크기: {len(yaml_content)} 문자")
        
        # Phase 1: Syntax Repair (actionlint → LLM)
        logger.info("=== Phase 1: 구문 오류 수정 ===")
        
        # 2단계: actionlint 실행
        logger.info("2단계: actionlint 구문 검사")
        from utils import process_runner
        actionlint_result = process_runner.run_actionlint(input_path)
        
        actionlint_errors = []
        if not actionlint_result.get("success", True):
            all_errors = actionlint_result.get("errors", [])
            # syntax-check와 expression 타입의 에러만 필터링
            actionlint_errors = [
                error for error in all_errors 
                if isinstance(error, dict) and error.get('kind') in ['syntax-check', 'expression']
            ]
            logger.info(f"actionlint에서 {len(actionlint_errors)}개 오류 발견 (syntax-check 및 expression만)")
        else:
            logger.info("actionlint 검사 통과")
        
        if actionlint_errors:
            logger.info(f"actionlint 오류 {len(actionlint_errors)}개 발견")
            for i, error in enumerate(actionlint_errors[:3]):  # 처음 3개만 로그
                logger.info(f"  오류 {i+1}: {error.get('message', 'N/A')}")
            
            # 3단계: 구문 오류 수정 프롬프트 생성
            logger.info("3단계: 구문 오류 수정 프롬프트 생성")
            syntax_prompt = create_syntax_repair_prompt(yaml_content, actionlint_errors, use_guided_prompt)
            
            # 4단계: 구문 오류 수정 LLM 호출
            logger.info("4단계: 구문 오류 수정 LLM 호출")
            llm_response = llm_api.call_llm_with_retry(syntax_prompt, max_tokens=6000)
            
            if not llm_response:
                logger.error("구문 오류 수정 LLM 호출 실패")
                return False
            
            # 5단계: 수정된 YAML 추출
            logger.info("5단계: 구문 수정된 YAML 추출")
            phase1_yaml = llm_api.extract_code_from_response(llm_response, "yaml")
            
            if not phase1_yaml:
                logger.warning("YAML 코드 블록을 찾을 수 없음, 전체 응답 사용")
                phase1_yaml = llm_response.strip()
            
            logger.info(f"Phase 1 완료, 수정된 YAML 크기: {len(phase1_yaml)} 문자")
        else:
            logger.info("actionlint 오류 없음, Phase 1 건너뛰기")
            phase1_yaml = yaml_content
        
        # Phase 2: Semantic Repair (smell detection → LLM)
        logger.info("=== Phase 2: 스멜 수정 ===")
        
        # 6단계: 임시 파일로 Phase 1 결과 저장 (smell detection을 위해)
        logger.info("6단계: 임시 파일 생성 및 스멜 검사")
        temp_path = f"{input_path}_temp_phase1.yml"
        
        try:
            # 임시 파일 저장
            success = yaml_parser.write_yaml_content(phase1_yaml, temp_path)
            if not success:
                logger.error("임시 파일 저장 실패")
                return False
            
            # 7단계: smell detection 실행
            logger.info("7단계: smell detection 실행")
            from utils import process_runner
            smell_result = process_runner.run_smell_detector(temp_path)
            smells = smell_result.get("smells", [])
            
            if smells:
                logger.info(f"스멜 {len(smells)}개 발견")
                for i, smell in enumerate(smells[:3]):  # 처음 3개만 로그
                    logger.info(f"  스멜 {i+1}: {smell.get('description', 'N/A')}")
                
                # 8단계: 스멜 수정 프롬프트 생성
                logger.info("8단계: 스멜 수정 프롬프트 생성")
                semantic_prompt = create_semantic_repair_prompt(phase1_yaml, smells, use_guided_prompt)
                
                # 9단계: 스멜 수정 LLM 호출
                logger.info("9단계: 스멜 수정 LLM 호출")
                llm_response = llm_api.call_llm_with_retry(semantic_prompt, max_tokens=6000)
                
                if not llm_response:
                    logger.error("스멜 수정 LLM 호출 실패")
                    return False
                
                # 10단계: 최종 수정된 YAML 추출
                logger.info("10단계: 최종 수정된 YAML 추출")
                final_yaml = llm_api.extract_code_from_response(llm_response, "yaml")
                
                if not final_yaml:
                    logger.warning("YAML 코드 블록을 찾을 수 없음, 전체 응답 사용")
                    final_yaml = llm_response.strip()
                
                logger.info(f"Phase 2 완료, 최종 YAML 크기: {len(final_yaml)} 문자")
            else:
                logger.info("스멜 없음, Phase 2 건너뛰기")
                final_yaml = phase1_yaml
                
        finally:
            # 임시 파일 삭제
            import os
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.debug(f"임시 파일 삭제: {temp_path}")
            except Exception as e:
                logger.warning(f"임시 파일 삭제 실패: {e}")
        
        # 11단계: 최종 결과 검증 및 저장
        logger.info("11단계: 최종 결과 검증 및 저장")
        validation_result = yaml_parser.validate_github_actions_workflow(final_yaml)
        
        if validation_result.get("is_valid", False):
            success = yaml_parser.write_yaml_content(final_yaml, output_path)
            if success:
                logger.info("2단계 모드 복구 완료")
                logger.info(f"최종 수정된 파일: {output_path}")
                return True
            else:
                logger.error("최종 파일 저장 실패")
                return False
        else:
            logger.error("최종 YAML이 유효하지 않음")
            logger.error(f"검증 오류: {validation_result.get('issues', [])}")
            # 유효하지 않아도 일단 저장해보기
            yaml_parser.write_yaml_content(final_yaml, output_path)
            return False
            
    except Exception as e:
        logger.error(f"2단계 모드 실행 중 오류: {e}")
        return False


def create_syntax_repair_prompt(yaml_content: str, actionlint_errors: list, use_guided_prompt: bool = True) -> str:
    """
    구문 오류 수정을 위한 프롬프트 생성
    
    Args:
        yaml_content: 원본 YAML 내용
        actionlint_errors: actionlint 오류 목록
        use_guided_prompt: 가이드 프롬프트 사용 여부
        
    Returns:
        str: 생성된 프롬프트
    """
    if use_guided_prompt:
        # GHA-Repair 모드용 가이드 프롬프트
        return create_guided_syntax_repair_prompt(yaml_content, actionlint_errors)
    else:
        # Two-phase Simple 모드용 기본 프롬프트
        prompt = f"""You are an expert GitHub Actions workflow developer. Please fix the syntax errors in the following YAML workflow file.

**Original YAML:**
```yaml
{yaml_content}
```

**Syntax Errors Detected by actionlint:**
"""
        for i, error in enumerate(actionlint_errors, 1):
            prompt += f"{i}. {error.get('message', 'Unknown error')}\n"
            if error.get('line'):
                prompt += f"   Line {error['line']}: {error.get('column', 'N/A')}\n"

        prompt += """
**Instructions:**
1. Fix ONLY the syntax errors listed above
2. Do NOT modify the workflow logic or functionality
3. Preserve all original comments and formatting where possible
4. Return the complete corrected YAML workflow
5. Ensure the output is valid YAML syntax

**Response Format:**
```yaml
# Fixed workflow
```
"""

        return prompt


def create_guided_syntax_repair_prompt(yaml_content: str, actionlint_errors: list) -> str:
    """
    GHA-Repair 모드용 가이드 프롬프트 - 구문 오류 수정
    
    Args:
        yaml_content: 원본 YAML 내용
        actionlint_errors: actionlint 오류 목록
        
    Returns:
        str: 생성된 가이드 프롬프트
    """
    
    YAML_GENERATION_RULES = """
### ⚡ IRONCLAD YAML SYNTAX RULES (NO EXCEPTIONS) ⚡
You are a GitHub Actions YAML repair engine. You must follow these 6 rules strictly to ensure the output is valid YAML.

#### Rule 1: Quote Wildcards and Globs
- **ALWAYS quote** strings containing wildcards: `*`, `?`, `[`, `]`
- Examples:
  - ❌ Bad: `files: *.whl`
  - ✅ Good: `files: '*.whl'`

#### Rule 2: FORCE Block Scalar (`|`) for `run` with Special Cases
- You **MUST** use the pipe (`|`) style when `run` contains:
  1. A colon (`:`) followed by a space
  2. Blank/empty lines between commands (including after comments)
  3. Multi-line commands
- Quoting is NOT enough (it causes YAML parsing conflicts).
- **CRITICAL**: Keep ALL command text exactly the same, only change YAML format.

**CRITICAL EXAMPLES - Learn from these exact patterns:**

**Pattern 1: Colon in run command**
  - ❌ WRONG: `run: echo "binary zip: ${{ binary_zip }}"`
  - ❌ WRONG: `run: 'echo "Status: Success"'`
  - ✅ CORRECT:
    ```
    run: |
      echo "binary zip: ${{ binary_zip }}"
    ```

**Pattern 2: Blank lines in run (especially after comments)**
  - ❌ WRONG:
    ```
    run: |
      mvn_args="install"
      # comment
      # comment
      
      if [ condition ]; then
    ```
  - ✅ CORRECT (remove blank lines after comments):
    ```
    run: |
      mvn_args="install"
      # comment
      # comment
      if [ condition ]; then
    ```

**Pattern 3: Multi-line with colons AND blank lines**
  - ❌ WRONG: Any run with both issues without `|`
  - ✅ CORRECT: Always use `run: |` and clean up blank lines after comments

#### Rule 3: QUOTE ENTIRE `if` Conditions with Colons
- If an `if` expression contains a colon (e.g., inside a string like `'type: bug'`), quote the **WHOLE** condition.
- Examples:
  - ❌ Bad: `if: github.event.label.name == 'type: bug'`
  - ✅ Good: `if: "github.event.label.name == 'type: bug'"`

#### Rule 4: Strict Indentation (2 Spaces)
- Use **exactly 2 spaces** per level. NO TABS.
- Content inside `|` block must be indented **2 spaces deeper** than the parent key.
- Examples:
  - ❌ Bad:
    ```
    run: |
    echo "no indent"
    ```
  - ✅ Good:
    ```
    run: |
      echo "proper indent"
    ```

#### Rule 5: NO MARKDOWN FENCES
- **DO NOT** output ```yaml or ``` tags.
- Return **RAW YAML TEXT ONLY**.

#### Rule 6: Context Availability - `if` Placement (MOST CRITICAL)
**THIS IS THE #1 CAUSE OF ERRORS - PAY EXTREME ATTENTION**

**📚 GHA CONTEXT AVAILABILITY RULES (OFFICIAL DOCUMENTATION):**

**6.1. ❌ ABSOLUTE PROHIBITION: NO `if` or Contexts in `on:` (Triggers)**
- **Rule:** The `on:` section defines **WHEN** to trigger the workflow (static configuration).
- **STRICTLY FORBIDDEN:** 
  - ❌ `if:` key anywhere inside `on:`
  - ❌ `${{ github.* }}` expressions inside `on:`
  - ❌ `${{ secrets.* }}` inside `on:`
  - ❌ `${{ env.* }}` inside `on:`
- **Common Error:** `unexpected key "if" for "push" section` or `unexpected key "if" for "pull_request" section`
- **Examples:**
  ```yaml
  # ❌ ABSOLUTELY WRONG - WILL CAUSE ERROR:
  on:
    push:
      branches: [main]
      if: github.event.after == '...'  # ❌ FATAL ERROR
  
  on:
    pull_request:
      if: github.repository == 'my/repo'  # ❌ FATAL ERROR
  
  on:
    workflow:
      inputs:
        version:
          if: github.event_name == 'push'  # ❌ FATAL ERROR
  ```

**6.2. ✅ CORRECT LOCATION #1: Job Level `if`**
- **Allowed:** `if:` can appear under `jobs.<job_id>:`
- **Available Contexts:** `github`, `needs`, `inputs`, `vars`
- **NOT Available:** `steps`, `runner`, `secrets` (in most cases), `env`
- **Examples:**
  ```yaml
  # ✅ CORRECT:
  jobs:
    build:
      if: github.event_name == 'push'  # ✅ Job-level conditional
      runs-on: ubuntu-latest
      steps:
        - run: echo "Building..."
  
    deploy:
      if: github.repository == 'owner/repo'  # ✅ Job-level conditional
      needs: build
      runs-on: ubuntu-latest
      steps:
        - run: echo "Deploying..."
  ```

**6.3. ✅ CORRECT LOCATION #2: Step Level `if`**
- **Allowed:** `if:` can appear under `steps:` array items
- **Available Contexts:** `github`, `needs`, `inputs`, `steps`, `runner`, `env`, `secrets`, `vars`, `job`, `matrix`
- **Examples:**
  ```yaml
  # ✅ CORRECT:
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - name: Checkout
          uses: actions/checkout@v3
          if: success()  # ✅ Step-level conditional
        
        - name: Run tests
          run: npm test
          if: github.ref == 'refs/heads/main'  # ✅ Step-level conditional
  ```

**6.4. ❌ Security Rule: NO Secrets in `if` (Most Cases)**
- **Rule:** Do NOT use `${{ secrets.* }}` in `if` conditions (security risk)
- **Exception:** `secrets.GITHUB_TOKEN` is sometimes allowed in step-level `if`
- **Examples:**
  ```yaml
  # ❌ WRONG:
  jobs:
    build:
      if: secrets.MY_SECRET == 'value'  # ❌ Security violation
  
  # ✅ CORRECT (if needed, use environment):
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - name: Check secret
          run: |
            if [ -n "${{ secrets.MY_SECRET }}" ]; then
              echo "Secret exists"
            fi
  ```

**6.5. REPAIR STRATEGY: Moving `if` from `on:` to Job Level**
When you see `if:` inside `on:`, you MUST move it to the job level:

```yaml
# ❌ BEFORE (WRONG):
on:
  push:
    branches: [main]
    if: github.event.after == 'xxx'  # ❌ ERROR

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"

# ✅ AFTER (CORRECT):
on:
  push:
    branches: [main]  # ✅ Clean trigger definition

jobs:
  build:
    if: github.event.after == 'xxx'  # ✅ Moved to job level
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
```

**6.6. CRITICAL CHECKLIST:**
Before returning YAML, verify:
- [ ] NO `if:` key anywhere inside `on:` section
- [ ] NO `${{ ... }}` expressions inside `on:` section
- [ ] All `if:` conditions are at job level (`jobs.<job_id>.if`) or step level (`steps[].if`)
- [ ] NO `secrets.*` in `if` conditions (except `secrets.GITHUB_TOKEN` at step level if necessary)
"""
    
    prompt = f"""### ROLE ###
You are a "Precision Linter Robot" that specializes ONLY in fixing syntax errors in GitHub Actions YAML files. Your sole mission is to resolve the given error list.

### STRICT INSTRUCTIONS (MOST IMPORTANT) ###
GOAL: Fix ONLY the 'Detected Syntax Errors' listed below.

### STRICT PROHIBITIONS (Guardrails): ###
- NEVER modify or change any code that is not mentioned in the error list.
- NEVER touch semantic parts such as workflow logic, step order, if conditions logic, etc.
- NEVER add or remove new steps or jobs.
- Preserve original comments and formatting as much as possible.

### SPECIAL RULE FOR `run` COMMANDS: ###
**PRIORITY 1 (HIGHEST): Fix YAML Parsing Errors First**
- If `run` command causes YAML parsing failure, you MUST fix the YAML syntax:
  ✅ ALLOWED: Add block scalar (`run: |`) when run contains colons or blank lines
  ✅ ALLOWED: Fix indentation to make valid YAML
  ✅ ALLOWED: Preserve ALL command text exactly (don't change echo, curl, etc.)
  
**PRIORITY 2: Preserve Command Logic**  
- NEVER change what the command does (no logic changes)
- NEVER modify command arguments, flags, or parameters
- Example:
  - ❌ BAD: Change `echo "Status: Success"` to `echo "Status Success"`
  - ✅ GOOD: Change from `run: echo "Status: Success"` to `run: |\n  echo "Status: Success"`

{YAML_GENERATION_RULES}

**Original YAML:**
```yaml
{yaml_content}
```

**Detected Syntax Errors:**
"""
    for i, error in enumerate(actionlint_errors, 1):
        prompt += f"{i}. {error.get('message', 'Unknown error')}\n"
        if error.get('line'):
            prompt += f"   Line {error['line']}: {error.get('column', 'N/A')}\n"

    prompt += """
**Response Format:**
```yaml
# Fixed workflow
```
"""

    return prompt


def create_semantic_repair_prompt(yaml_content: str, smells: list, use_guided_prompt: bool = True) -> str:
    """
    스멜 수정을 위한 프롬프트 생성
    
    Args:
        yaml_content: Phase 1에서 구문 오류가 수정된 YAML 내용
        smells: 감지된 스멜 목록
        use_guided_prompt: 가이드 프롬프트 사용 여부
        
    Returns:
        str: 생성된 프롬프트
    """
    if use_guided_prompt:
        # GHA-Repair 모드용 가이드 프롬프트
        return create_guided_semantic_repair_prompt(yaml_content, smells)
    else:
        # Two-phase Simple 모드용 기본 프롬프트
        prompt = f"""You are an expert GitHub Actions workflow developer. Please fix the code smells and improve the quality of the following YAML workflow file.

**Current YAML (syntax errors already fixed):**
```yaml
{yaml_content}
```

**Code Smells Detected:**
"""
        for i, smell in enumerate(smells, 1):
            prompt += f"{i}. **{smell.get('type', 'Unknown')}**: {smell.get('description', 'No description')}\n"
            if smell.get('location'):
                prompt += f"   Location: {smell['location']}\n"
            if smell.get('suggestion'):
                prompt += f"   Suggestion: {smell['suggestion']}\n"

        prompt += """
**Instructions:**
1. Fix the code smells listed above
2. Improve workflow efficiency and best practices
3. Maintain the original workflow functionality
4. Apply GitHub Actions best practices
5. Return the complete improved YAML workflow

**Response Format:**
```yaml
# Fixed workflow
```
"""

        return prompt


def create_guided_semantic_repair_prompt(yaml_content: str, smells: list) -> str:
    """
    GHA-Repair 모드용 가이드 프롬프트 - 스멜 수정
    
    Args:
        yaml_content: Phase 1에서 구문 오류가 수정된 YAML 내용
        smells: 감지된 스멜 목록
        
    Returns:
        str: 생성된 가이드 프롬프트
    """
    
    YAML_GENERATION_RULES = """
### ⚡ IRONCLAD YAML SYNTAX RULES (NO EXCEPTIONS) ⚡
You are a GitHub Actions YAML repair engine. You must follow these 6 rules strictly to ensure the output is valid YAML.

#### Rule 1: Quote Wildcards and Globs
- **ALWAYS quote** strings containing wildcards: `*`, `?`, `[`, `]`
- Examples:
  - ❌ Bad: `files: *.whl`
  - ✅ Good: `files: '*.whl'`

#### Rule 2: FORCE Block Scalar (`|`) for `run` with Special Cases
- You **MUST** use the pipe (`|`) style when `run` contains:
  1. A colon (`:`) followed by a space
  2. Blank/empty lines between commands (including after comments)
  3. Multi-line commands
- Quoting is NOT enough (it causes YAML parsing conflicts).
- **CRITICAL**: Keep ALL command text exactly the same, only change YAML format.

**CRITICAL EXAMPLES - Learn from these exact patterns:**

**Pattern 1: Colon in run command**
  - ❌ WRONG: `run: echo "binary zip: ${{ binary_zip }}"`
  - ❌ WRONG: `run: 'echo "Status: Success"'`
  - ✅ CORRECT:
    ```
    run: |
      echo "binary zip: ${{ binary_zip }}"
    ```

**Pattern 2: Blank lines in run (especially after comments)**
  - ❌ WRONG:
    ```
    run: |
      mvn_args="install"
      # comment
      # comment
      
      if [ condition ]; then
    ```
  - ✅ CORRECT (remove blank lines after comments):
    ```
    run: |
      mvn_args="install"
      # comment
      # comment
      if [ condition ]; then
    ```

**Pattern 3: Multi-line with colons AND blank lines**
  - ❌ WRONG: Any run with both issues without `|`
  - ✅ CORRECT: Always use `run: |` and clean up blank lines after comments

#### Rule 3: QUOTE ENTIRE `if` Conditions with Colons
- If an `if` expression contains a colon (e.g., inside a string like `'type: bug'`), quote the **WHOLE** condition.
- Examples:
  - ❌ Bad: `if: github.event.label.name == 'type: bug'`
  - ✅ Good: `if: "github.event.label.name == 'type: bug'"`

#### Rule 4: Strict Indentation (2 Spaces)
- Use **exactly 2 spaces** per level. NO TABS.
- Content inside `|` block must be indented **2 spaces deeper** than the parent key.
- Examples:
  - ❌ Bad:
    ```
    run: |
    echo "no indent"
    ```
  - ✅ Good:
    ```
    run: |
      echo "proper indent"
    ```

#### Rule 5: NO MARKDOWN FENCES
- **DO NOT** output ```yaml or ``` tags.
- Return **RAW YAML TEXT ONLY**.

#### Rule 6: Context Availability - `if` Placement (MOST CRITICAL)
**THIS IS THE #1 CAUSE OF ERRORS - PAY EXTREME ATTENTION**

**📚 GHA CONTEXT AVAILABILITY RULES (OFFICIAL DOCUMENTATION):**

**6.1. ❌ ABSOLUTE PROHIBITION: NO `if` or Contexts in `on:` (Triggers)**
- **Rule:** The `on:` section defines **WHEN** to trigger the workflow (static configuration).
- **STRICTLY FORBIDDEN:** 
  - ❌ `if:` key anywhere inside `on:`
  - ❌ `${{ github.* }}` expressions inside `on:`
  - ❌ `${{ secrets.* }}` inside `on:`
  - ❌ `${{ env.* }}` inside `on:`
- **Common Error:** `unexpected key "if" for "push" section` or `unexpected key "if" for "pull_request" section`
- **Examples:**
  ```yaml
  # ❌ ABSOLUTELY WRONG - WILL CAUSE ERROR:
  on:
    push:
      branches: [main]
      if: github.event.after == '...'  # ❌ FATAL ERROR
  
  on:
    pull_request:
      if: github.repository == 'my/repo'  # ❌ FATAL ERROR
  
  on:
    workflow:
      inputs:
        version:
          if: github.event_name == 'push'  # ❌ FATAL ERROR
  ```

**6.2. ✅ CORRECT LOCATION #1: Job Level `if`**
- **Allowed:** `if:` can appear under `jobs.<job_id>:`
- **Available Contexts:** `github`, `needs`, `inputs`, `vars`
- **NOT Available:** `steps`, `runner`, `secrets` (in most cases), `env`
- **Examples:**
  ```yaml
  # ✅ CORRECT:
  jobs:
    build:
      if: github.event_name == 'push'  # ✅ Job-level conditional
      runs-on: ubuntu-latest
      steps:
        - run: echo "Building..."
  
    deploy:
      if: github.repository == 'owner/repo'  # ✅ Job-level conditional
      needs: build
      runs-on: ubuntu-latest
      steps:
        - run: echo "Deploying..."
  ```

**6.3. ✅ CORRECT LOCATION #2: Step Level `if`**
- **Allowed:** `if:` can appear under `steps:` array items
- **Available Contexts:** `github`, `needs`, `inputs`, `steps`, `runner`, `env`, `secrets`, `vars`, `job`, `matrix`
- **Examples:**
  ```yaml
  # ✅ CORRECT:
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - name: Checkout
          uses: actions/checkout@v3
          if: success()  # ✅ Step-level conditional
        
        - name: Run tests
          run: npm test
          if: github.ref == 'refs/heads/main'  # ✅ Step-level conditional
  ```

**6.4. ❌ Security Rule: NO Secrets in `if` (Most Cases)**
- **Rule:** Do NOT use `${{ secrets.* }}` in `if` conditions (security risk)
- **Exception:** `secrets.GITHUB_TOKEN` is sometimes allowed in step-level `if`
- **Examples:**
  ```yaml
  # ❌ WRONG:
  jobs:
    build:
      if: secrets.MY_SECRET == 'value'  # ❌ Security violation
  
  # ✅ CORRECT (if needed, use environment):
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - name: Check secret
          run: |
            if [ -n "${{ secrets.MY_SECRET }}" ]; then
              echo "Secret exists"
            fi
  ```

**6.5. REPAIR STRATEGY: Moving `if` from `on:` to Job Level**
When you see `if:` inside `on:`, you MUST move it to the job level:

```yaml
# ❌ BEFORE (WRONG):
on:
  push:
    branches: [main]
    if: github.event.after == 'xxx'  # ❌ ERROR

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"

# ✅ AFTER (CORRECT):
on:
  push:
    branches: [main]  # ✅ Clean trigger definition

jobs:
  build:
    if: github.event.after == 'xxx'  # ✅ Moved to job level
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
```

**6.6. CRITICAL CHECKLIST:**
Before returning YAML, verify:
- [ ] NO `if:` key anywhere inside `on:` section
- [ ] NO `${{ ... }}` expressions inside `on:` section
- [ ] All `if:` conditions are at job level (`jobs.<job_id>.if`) or step level (`steps[].if`)
- [ ] NO `secrets.*` in `if` conditions (except `secrets.GITHUB_TOKEN` at step level if necessary)
"""
    
    prompt = f"""### ROLE ###
You are a "Professional DevOps Engineer" who fixes ONLY the 'Specific Code Smell List' in GitHub Actions workflows according to best practices.

### STRICT INSTRUCTIONS (MOST IMPORTANT) ###
GOAL: Fix ONLY the 'Detected Semantic Smell List' listed below according to GitHub best practices.

### STRICT PROHIBITIONS (Guardrails): ###
- NEVER fix smells or other code quality issues not listed. (e.g., don't arbitrarily improve efficiency)
- NEVER change code not directly related to smell fixes. (e.g., don't modify permissions key to fix timeout smell)
- Fix smells while maintaining the core functionality, behavior sequence, if conditions, and other structural/logical flow of the existing workflow

{YAML_GENERATION_RULES}

**Current YAML (syntax errors already fixed):**
```yaml
{yaml_content}
```

**Code Smells to Fix:**
"""
    for i, smell in enumerate(smells, 1):
        prompt += f"{i}. **{smell.get('type', 'Unknown')}**: {smell.get('description', 'No description')}\n"
        if smell.get('location'):
            prompt += f"   Location: {smell['location']}\n"
        if smell.get('suggestion'):
            prompt += f"   Suggestion: {smell['suggestion']}\n"

    prompt += """
Provide an improved YAML that fixes each smell according to GitHub Actions best practices:

**Response Format:**
```yaml
# Fixed workflow
```
"""

    return prompt





def create_baseline_prompt(yaml_content: str, actionlint_errors: list, smells: list) -> str:
    """
    베이스라인 모드용 통합 프롬프트를 생성합니다.
    """
    prompt = f"""Please fix the issues found in this GitHub Actions workflow.

**Original Workflow:**
```yaml
{yaml_content}
```

**Issues Found:**

"""
    
    # actionlint 오류 추가
    if actionlint_errors:
        prompt += "**Syntax Errors (actionlint):**\n"
        for i, error in enumerate(actionlint_errors[:10], 1):  # 최대 10개
            if isinstance(error, dict):
                error_msg = error.get('message', str(error))
            else:
                error_msg = str(error)
            prompt += f"{i}. {error_msg}\n"
        prompt += "\n"
    else:
        prompt += "**Syntax Errors:** None\n\n"
    
    # smell detector 결과 추가
    if smells:
        prompt += "**Semantic Smells:**\n"
        for i, smell in enumerate(smells[:10], 1):  # 최대 10개
            smell_msg = smell.get('message', str(smell))
            prompt += f"{i}. {smell_msg}\n"
        prompt += "\n"
    else:
        prompt += "**Semantic Smells:** None\n\n"
    
    prompt += """**Fix Request:**
Please provide a complete GitHub Actions workflow that fixes all the syntax errors and semantic smells found above.

**Considerations for Fixes:**
1. Follow the latest GitHub Actions syntax and best practices
2. Maintain the intent and functionality of the existing workflow
3. Prioritize fixing security-related issues
4. Fix all syntax errors

**Response Format:**
```yaml
# Fixed workflow
```
"""
    
    return prompt


def run_poc_test(input_path: str, output_path: str) -> bool:
    """
    간단한 POC 테스트: 입력 파일을 읽고 기본적인 검증을 수행합니다.
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== POC 테스트 시작 ===")
        
        # 1. 파일 읽기 테스트
        logger.info("1단계: 파일 읽기 테스트")
        content = yaml_parser.read_yaml_content(input_path)
        if not content:
            logger.error("파일 읽기 실패")
            return False
        
        logger.info(f"파일 크기: {len(content)} 문자")
        
        # 2. YAML 검증 테스트
        logger.info("2단계: YAML 검증 테스트")
        is_valid = yaml_parser.validate_yaml(content)
        logger.info(f"YAML 유효성: {'유효' if is_valid else '무효'}")
        
        # 3. 워크플로우 구조 분석 테스트
        logger.info("3단계: 워크플로우 구조 분석 테스트")
        structure = yaml_parser.get_workflow_structure(content)
        logger.info(f"워크플로우 이름: {structure.get('name', 'N/A')}")
        logger.info(f"Job 수: {structure.get('job_count', 0)}")
        logger.info(f"Step 수: {structure.get('step_count', 0)}")
        
        # 4. LLM API 테스트 (간단한 프롬프트)
        logger.info("4단계: LLM API 연결 테스트")
        test_prompt = "Hello, can you respond with 'API connection successful'?"
        
        try:
            response = llm_api.call_llm(test_prompt, max_tokens=50)
            if response:
                logger.info(f"LLM API 테스트 성공: {response[:100]}...")
            else:
                logger.warning("LLM API 테스트 실패 - 응답 없음")
        except Exception as e:
            logger.warning(f"LLM API 테스트 중 오류: {e}")
        
        # 5. 파일 복사 테스트 (간단한 출력)
        logger.info("5단계: 출력 파일 생성 테스트")
        success = yaml_parser.write_yaml_content(content, output_path)
        if success:
            logger.info(f"출력 파일 생성 완료: {output_path}")
        else:
            logger.error("출력 파일 생성 실패")
            return False
        
        logger.info("=== POC 테스트 완료 ===")
        return True
        
    except Exception as e:
        logger.error(f"POC 테스트 중 오류: {e}")
        return False


if __name__ == "__main__":
    main()
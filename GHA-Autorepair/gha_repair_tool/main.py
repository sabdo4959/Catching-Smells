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
    
    # ==============================================================================
    # PART 1. ACTIONLINT & GHA SCHEMA DEFENSE RULES (HIGHEST PRIORITY)
    # 목표: actionlint 통과를 위한 구조적 제약 사항 준수
    # ==============================================================================
    
    ACTIONLINT_DEFENSE_RULES = """
### 🛡️ ACTIONLINT & SCHEMA DEFENSE RULES (STRICT) 🛡️
You MUST follow these rules to pass 'actionlint' validation and GitHub Actions schema constraints.

#### Defense Rule 1: 🚨 NO `if` in `on` / `triggers` (FATAL ERROR - HIGHEST PRIORITY)
- **FATAL ERROR:** `unexpected key "if" for "push" section` or `"pull_request" section`
- **Root Cause:** `on:` section defines WHEN to trigger (static config). NO runtime conditions allowed.
- **STRICTLY FORBIDDEN:**
  - ❌ ANY `if:` key inside `on:` section
  - ❌ `${{ github.* }}` expressions inside `on:`
  - ❌ Conditional logic in triggers (push, pull_request, schedule, workflow_dispatch, etc.)

**CRITICAL FIX PATTERN (Most Common Error):**
```yaml
# ❌ WRONG (CAUSES FATAL ERROR):
on:
  push:
    branches: [main]
    if: github.event.after == 'xxx'  # ❌ ERROR

# ✅ CORRECT (Move to Job Level):
on:
  push:
    branches: [main]  # ✅ Clean trigger

jobs:
  build:
    if: github.event.after == 'xxx'  # ✅ Condition at job level
    runs-on: ubuntu-latest
```

**Multi-Trigger Pattern (Common Failure Case):**
```yaml
# ❌ WRONG:
on:
  push:
    if: github.repository == 'owner/repo'  # ❌ ERROR
  pull_request:
    if: github.event.pull_request.head.repo.fork == false  # ❌ ERROR

# ✅ CORRECT:
on:
  push:
  pull_request:

jobs:
  build:
    if: |
      github.repository == 'owner/repo' &&
      (github.event_name == 'push' || 
       github.event.pull_request.head.repo.fork == false)
    runs-on: ubuntu-latest
```

#### Defense Rule 2: 🚫 NO `timeout-minutes` for Reusable Workflows
- **ERROR:** `when a reusable workflow is called... timeout-minutes is not available`
- **Rule:** If a job uses `uses: ./.github/workflows/...`, DO NOT add `timeout-minutes`.
- **Exception Handling:** When fixing Smell 5 (Missing Timeout), CHECK if job is reusable first.
```yaml
# ❌ WRONG (Reusable Workflow):
jobs:
  reusable-job:
    uses: ./.github/workflows/check.yml
    timeout-minutes: 60  # ❌ ERROR - not allowed for reusable workflows

# ✅ CORRECT:
jobs:
  reusable-job:
    uses: ./.github/workflows/check.yml  # ✅ No timeout for reusable

  regular-job:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # ✅ OK for regular jobs
```

#### Defense Rule 3: 📝 Strict List Syntax for Paths/Branches
- **ERROR:** `expected scalar node ... but found sequence node`
- **Rule:** `paths`, `paths-ignore`, `branches`, `branches-ignore` MUST use list format (hyphens).
```yaml
# ❌ WRONG:
on:
  push:
    paths-ignore: '**.md'  # ❌ Single string - may cause errors

# ✅ CORRECT (Use List Format):
on:
  push:
    paths-ignore:
      - '**.md'      # ✅ List item (note the hyphen)
      - 'docs/**'    # ✅ Each pattern on separate line
```

#### Defense Rule 4: 🧩 Separation of `uses` and `run`
- **ERROR:** `step contains both "uses" and "run"`
- **Rule:** A step CANNOT have both `uses:` (action) and `run:` (shell command).
- **Fix:** Split into two separate steps.
```yaml
# ❌ WRONG:
- name: Checkout and build
  uses: actions/checkout@v4
  run: npm install  # ❌ Cannot coexist

# ✅ CORRECT:
- name: Checkout
  uses: actions/checkout@v4
- name: Build
  run: npm install
```
"""

    # ==============================================================================
    # PART 2. YAML SYNTAX GENERATION RULES (CRITICAL)
    # 목표: 유효한 YAML 생성 및 파싱 에러 방지
    # ==============================================================================

    YAML_GENERATION_RULES = """
### ⚡ IRONCLAD YAML SYNTAX RULES (NO EXCEPTIONS) ⚡
You are a GitHub Actions YAML repair engine. Follow these rules to ensure valid YAML output.

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

#### Rule 5: NO MARKDOWN FENCES OR BACKTICKS (CRITICAL - NEW)
- **ABSOLUTELY FORBIDDEN:** Backtick characters (`, ```, ``````) in YAML output
- **DO NOT** use markdown code block syntax anywhere in the YAML
- **VERIFICATION:** Output must NOT contain ANY backtick (`) character
- **Common Error:** found character backtick that cannot start any token
- Examples:
  - ❌ WRONG: run with backtick characters
  - ❌ WRONG: Including markdown code fences in output
  - ✅ CORRECT: Use $() for command substitution instead of backticks
- **Return RAW YAML TEXT ONLY** without any markdown formatting.

#### Rule 6: `concurrency` Placement Rules (FIX COMMON ERROR)
- **ERROR PATTERN:** `unexpected key "concurrency" for "push" section` or `"pull_request" section`
- **ROOT CAUSE:** `concurrency` placed INSIDE trigger sections instead of at workflow/job level
- **RULE:** `concurrency` is ONLY valid at:
  1. **Workflow-level** (root of YAML, alongside `name:`, `on:`)
  2. **Job-level** (inside a job definition, alongside `runs-on:`, `steps:`)
- **NEVER place `concurrency` inside:**
  - ❌ `on:` section
  - ❌ `on.push:` section  
  - ❌ `on.pull_request:` section
  - ❌ `on.workflow_dispatch:` section
  - ❌ Any trigger configuration

**EXAMPLES:**

**❌ WRONG - concurrency inside trigger:**
```yaml
on:
  push:
    branches: [main]
    concurrency:        # ❌ INVALID - cannot be inside push
      group: build
      cancel-in-progress: true
```

**❌ WRONG - concurrency as job name:**
```yaml
jobs:
  concurrency:          # ❌ INVALID - job named 'concurrency' 
    group: test         # ❌ Missing runs-on, steps
    cancel-in-progress: true
```

**✅ CORRECT - Workflow-level concurrency:**
```yaml
name: CI
on:
  push:
    branches: [main]

concurrency:            # ✅ VALID - at workflow root
  group: ${{{{ github.workflow }}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
```

**✅ CORRECT - Job-level concurrency:**
```yaml
name: CI
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    concurrency:        # ✅ VALID - inside job
      group: build-${{{{ github.ref }}}}
      cancel-in-progress: true
    steps:
      - run: npm install
```

**FIX STRATEGY:**
1. **DETECT:** Find `concurrency:` inside `on:` or trigger sections
2. **EXTRACT:** Remove `concurrency:` block from wrong location
3. **RELOCATE:** Move to workflow root (before `jobs:`) or inside specific job
4. **VERIFY:** Ensure `group:` and `cancel-in-progress:` remain intact

#### Rule 7: NO Duplicate Keys - Merge Strategy (CRITICAL) 👯
- **FATAL ERROR:** `key "jobs" is duplicated`, `key "on" is duplicated`, `key "env" is duplicated`, `key "permissions" is duplicated`
- **Official Syntax:** Per YAML spec and GitHub Actions syntax, a mapping CANNOT contain duplicate keys at the same level
  - Reference: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **ROOT CAUSE:** Appending new content at end of file instead of merging into EXISTING blocks
- **STRICT INSTRUCTION:**
  1. **CHECK:** Does the top-level key (`jobs`, `on`, `permissions`, `env`, `concurrency`) ALREADY EXIST in the file?
  2. **IF EXISTS:** Write new content **INSIDE** the existing block (merge, don't duplicate)
  3. **NEVER:** Write the same top-level key twice

**EXAMPLES:**

**❌ WRONG - Duplicate 'jobs' key:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm build

# ... lines later ...
jobs:                    # ❌ DUPLICATE KEY ERROR!
  test:
    runs-on: ubuntu-latest
```

**✅ CORRECT - Merged into single 'jobs' block:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm build
  test:                  # ✅ Added as sibling job (same indentation as 'build')
    runs-on: ubuntu-latest
```

**❌ WRONG - Duplicate 'on' key:**
```yaml
on:
  push:
    branches: [main]

on:                      # ❌ DUPLICATE KEY ERROR!
  pull_request:
    branches: [main]
```

**✅ CORRECT - Merged triggers:**
```yaml
on:
  push:
    branches: [main]
  pull_request:          # ✅ Added as sibling trigger (same level as 'push')
    branches: [main]
```

**FIX STRATEGY:**
1. **SCAN:** Identify ALL occurrences of top-level keys (`jobs:`, `on:`, `env:`, etc.)
2. **MERGE:** Combine all content under the FIRST occurrence
3. **DELETE:** Remove duplicate key declarations
4. **VERIFY:** Maintain proper indentation (siblings at same level)

#### Rule 8: YAML Structure Types - Sequence vs. Mapping (CRITICAL) 🏗️
- **FATAL ERRORS:** 
  - `"push" section is sequence node but mapping node is expected`
  - `"tags" section is sequence node but mapping node is expected`
  - `expected scalar node for string value but found sequence node`
- **Official Syntax:** GitHub Actions has STRICT requirements for Mappings (key-value) vs. Sequences (lists)
  - Reference: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **ROOT CAUSE:** Using list syntax (`- item`) where key-value pairs are required, or vice versa

**A. Areas Requiring MAPPINGS (Key-Value, NO Dashes `-`):**

1. **`jobs:`** - Job names are keys, not list items
   - ✅ CORRECT: `jobs:\n  build:\n    runs-on: ubuntu-latest`
   - ❌ WRONG: `jobs:\n  - build:` (don't use dash)

2. **`on:`** - Event names are keys
   - ✅ CORRECT: `on:\n  push:\n    branches: [main]`
   - ❌ WRONG: `on:\n  - push:` (don't use dash)

3. **`on.push:`, `on.pull_request:`** - Trigger filters are keys
   - ✅ CORRECT: `push:\n  branches: [main]\n  tags: [v*]`
   - ❌ WRONG: `push:\n  - branches: [main]` (don't use dash before branches)

4. **`env:`** - Environment variables are key-value pairs
   - ✅ CORRECT: `env:\n  NODE_VERSION: '14'`
   - ❌ WRONG: `env:\n  - NODE_VERSION: '14'`

5. **`with:`** - Action inputs are key-value pairs
   - ✅ CORRECT: `with:\n  node-version: 14`
   - ❌ WRONG: `with:\n  - node-version: 14`

**B. Areas Requiring SEQUENCES (List, MUST use Dashes `-`):**

1. **`steps:`** - Steps are ALWAYS a list
   - ✅ CORRECT: `steps:\n  - name: Checkout\n    uses: actions/checkout@v4`
   - ❌ WRONG: `steps:\n  name: Checkout` (missing dash)

2. **`branches:`, `tags:`, `paths:`** - Filter values are lists (when multiple items)
   - ✅ CORRECT: `branches:\n  - main\n  - develop` OR `branches: [main, develop]`
   - ✅ ALSO OK: `branches: main` (single scalar value allowed)
   - ❌ WRONG: Empty without values (see Rule C2)

3. **`types:`** - Event types are lists
   - ✅ CORRECT: `types: [opened, synchronize]` OR `types:\n  - opened\n  - synchronize`

4. **`strategy.matrix:`** - Matrix values are lists
   - ✅ CORRECT: `matrix:\n  node-version: [14, 16, 18]`

**C. Special Rules:**

1. **`needs:`** - Can be scalar (string) OR sequence (list), NEVER mapping
   - ✅ CORRECT: `needs: build`
   - ✅ CORRECT: `needs: [build, test]`
   - ❌ WRONG: `needs:\n  build: true`

2. **`secrets:`** - For reusable workflows, can be mapping OR `inherit` keyword
   - ✅ CORRECT: `secrets:\n  TOKEN: ${{{{ secrets.TOKEN }}}}`
   - ✅ CORRECT: `secrets: inherit`
   - ❌ WRONG: `secrets:\n  - TOKEN: value` (not a list)

3. **Empty sections MUST be removed:**
   - ❌ WRONG: `tags:` (no values)
   - ❌ WRONG: `env:` (no variables)
   - ❌ WRONG: `paths-ignore:` (no paths)
   - ✅ CORRECT: Remove the entire empty section

**D. Structure Conversion Patterns (CRITICAL FIXES):**

1. **Shorthand to Full Syntax (Triggers):**
   - ❌ WRONG: `on: [push]` → `push: []` (Empty list is wrong)
   - ❌ WRONG: `on: [push]` → `push: {}` (Empty mapping at root is wrong)
   - ✅ CORRECT: `on: [push]` → `on:\n  push:` (Mapping inside 'on')
   
   - ❌ WRONG: `on: [push, pull_request]` → `push: []\n  pull_request: []`
   - ✅ CORRECT: `on: [push, pull_request]` → `on:\n  push:\n  pull_request:`

2. **Filter Placement (Nesting Rule):**
   - **Rule:** `tags`, `branches`, `paths`, `paths-ignore` MUST be INSIDE a specific trigger (push/pull_request), NOT directly under `on`.
   - ❌ WRONG (tags as sibling to push):
     ```yaml
     on:
       push:
         branches: [main]
       tags: [v*]  # ❌ Error: tags is at wrong level
     ```
   - ✅ CORRECT (tags nested in push):
     ```yaml
     on:
       push:
         branches: [main]
         tags: [v*]  # ✅ Correct: tags is child of push
     ```
   - ❌ WRONG (tags at on level):
     ```yaml
     on:
       push:
       tags:  # ❌ Error: tags should be inside push
         - v*
     ```
   - ✅ CORRECT (move tags into push):
     ```yaml
     on:
       push:
         tags:  # ✅ Correct: tags is inside push
           - v*
     ```

**EXAMPLES:**

**❌ WRONG - push as sequence:**
```yaml
on:
  - push:                # ❌ push should be a KEY, not a list item
      branches: [main]
```

**✅ CORRECT - push as mapping:**
```yaml
on:
  push:                  # ✅ push is a key (no dash)
    branches: [main]
```

**❌ WRONG - tags empty:**
```yaml
on:
  push:
    tags:                # ❌ Empty - must have values or be removed
```

**✅ CORRECT - tags with values or removed:**
```yaml
on:
  push:
    tags:
      - v*               # ✅ List of tag patterns
      - release-*
```
OR
```yaml
on:
  push:
    branches: [main]     # ✅ Removed empty tags section entirely
```

**FIX STRATEGY:**
1. **IDENTIFY:** Check GitHub Actions syntax reference for expected type (mapping vs. sequence)
2. **CONVERT:** 
   - If mapping needed → Remove dashes, use `key: value` format
   - If sequence needed → Add dashes, use `- item` format or `[item1, item2]`
3. **REMOVE:** Delete any empty sections (no values)
4. **VERIFY:** Check indentation matches the structure type
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

{ACTIONLINT_DEFENSE_RULES}

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
    
    # ==============================================================================
    # PART 1. ACTIONLINT & GHA SCHEMA DEFENSE RULES (MUST PRESERVE)
    # 목표: Semantic repair 중에도 구조적 제약 위반 방지
    # ==============================================================================
    
    ACTIONLINT_DEFENSE_RULES = """
### 🛡️ ACTIONLINT & SCHEMA DEFENSE RULES (STRICT) 🛡️
You MUST follow these rules to pass 'actionlint' validation and GitHub Actions schema constraints.

#### Defense Rule 0: 👯 NO Duplicate Keys (CRITICAL FOR SEMANTIC REPAIR)
- **CONTEXT:** When fixing smells (e.g., Smell 9, Smell 6, Smell 4), you will ADD new code.
- **FATAL ERROR:** Creating a second `jobs:`, `on:`, `env:`, `permissions:`, or `concurrency:` section causes "key is duplicated" error.
- **STRICT INSTRUCTION:**
  1. **LOOK FIRST:** Does `jobs:` already exist in the file? (It almost ALWAYS does!)
  2. **MERGE:** Write your new job/env/permission **INSIDE** the existing block.
  3. **NEVER:** Write `jobs:` or `on:` again at the bottom of the file.

**EXAMPLES:**

**❌ WRONG - Creating duplicate jobs:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest  # Existing job

# ... (many lines later) ...

jobs:  # ❌ DUPLICATE KEY ERROR!
  scheduled-job:  # Smell 9 fix - WRONG APPROACH
    if: github.repository_owner == 'owner'
    runs-on: ubuntu-latest
```

**✅ CORRECT - Merge into existing jobs:**
```yaml
jobs:
  build:
    runs-on: ubuntu-latest  # Existing job
  
  scheduled-job:  # ✅ Added as sibling job (same indentation as 'build')
    if: github.repository_owner == 'owner'
    runs-on: ubuntu-latest
```

**❌ WRONG - Creating duplicate permissions:**
```yaml
permissions:
  contents: read  # Existing

# ... later ...
permissions:  # ❌ DUPLICATE KEY ERROR!
  issues: write  # Smell 4 fix - WRONG APPROACH
```

**✅ CORRECT - Merge into existing permissions:**
```yaml
permissions:
  contents: read  # Existing
  issues: write   # ✅ Added to same permissions block
```

#### Defense Rule 1: 🚨 NO `if` in `on` / `triggers` (FATAL ERROR - HIGHEST PRIORITY)
- **FATAL ERROR:** `unexpected key "if" for "push" section` or `"pull_request" section`
- **Root Cause:** `on:` section defines WHEN to trigger (static config). NO runtime conditions allowed.
- **STRICTLY FORBIDDEN:**
  - ❌ ANY `if:` key inside `on:` section
  - ❌ `${{ github.* }}` expressions inside `on:`
  - ❌ Conditional logic in triggers (push, pull_request, schedule, workflow_dispatch, etc.)

**CRITICAL FIX PATTERN (Most Common Error):**
```yaml
# ❌ WRONG (CAUSES FATAL ERROR):
on:
  push:
    branches: [main]
    if: github.event.after == 'xxx'  # ❌ ERROR

# ✅ CORRECT (Move to Job Level):
on:
  push:
    branches: [main]  # ✅ Clean trigger

jobs:
  build:
    if: github.event.after == 'xxx'  # ✅ Condition at job level
    runs-on: ubuntu-latest
```

**Multi-Trigger Pattern (Common Failure Case):**
```yaml
# ❌ WRONG:
on:
  push:
    if: github.repository == 'owner/repo'  # ❌ ERROR
  pull_request:
    if: github.event.pull_request.head.repo.fork == false  # ❌ ERROR

# ✅ CORRECT:
on:
  push:
  pull_request:

jobs:
  build:
    if: |
      github.repository == 'owner/repo' &&
      (github.event_name == 'push' || 
       github.event.pull_request.head.repo.fork == false)
    runs-on: ubuntu-latest
```

#### Defense Rule 2: 🚫 NO `timeout-minutes` for Reusable Workflows
- **ERROR:** `when a reusable workflow is called... timeout-minutes is not available`
- **Rule:** If a job uses `uses: ./.github/workflows/...`, DO NOT add `timeout-minutes`.
- **Exception Handling:** When fixing Smell 5 (Missing Timeout), CHECK if job is reusable first.
```yaml
# ❌ WRONG (Reusable Workflow):
jobs:
  reusable-job:
    uses: ./.github/workflows/check.yml
    timeout-minutes: 60  # ❌ ERROR - not allowed for reusable workflows

# ✅ CORRECT:
jobs:
  reusable-job:
    uses: ./.github/workflows/check.yml  # ✅ No timeout for reusable

  regular-job:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # ✅ OK for regular jobs
```

#### Defense Rule 3: 📝 Strict List Syntax for Paths/Branches
- **ERROR:** `expected scalar node ... but found sequence node`
- **Rule:** `paths`, `paths-ignore`, `branches`, `branches-ignore` MUST use list format (hyphens).
```yaml
# ❌ WRONG:
on:
  push:
    paths-ignore: '**.md'  # ❌ Single string - may cause errors

# ✅ CORRECT (Use List Format):
on:
  push:
    paths-ignore:
      - '**.md'      # ✅ List item (note the hyphen)
      - 'docs/**'    # ✅ Each pattern on separate line
```

#### Defense Rule 4: 🧩 Separation of `uses` and `run`
- **ERROR:** `step contains both "uses" and "run"`
- **Rule:** A step CANNOT have both `uses:` (action) and `run:` (shell command).
- **Fix:** Split into two separate steps.
```yaml
# ❌ WRONG:
- name: Checkout and build
  uses: actions/checkout@v4
  run: npm install  # ❌ Cannot coexist

# ✅ CORRECT:
- name: Checkout
  uses: actions/checkout@v4
- name: Build
  run: npm install
```
"""

    # ==============================================================================
    # PART 2. SMELL REPAIR GUIDELINES (REFINED)
    # 목표: Smell 5 예외 처리 추가, Smell 8/9/10 위치 제약 강화
    # ==============================================================================

    SMELL_FIX_INSTRUCTIONS = """
### 🔧 CODE SMELL REPAIR GUIDELINES ###

#### Smell 2: Outdated Action
- **Problem:** Security/Stability risks from old tags.
- **Solution:** Use Commit Hash (Secure) or latest major tag.
- **Example:** `uses: actions/checkout@v4`

#### Smell 3: Deprecated Command
- **Problem:** `::set-output` fails in new runners.
- **Solution:** Use `$GITHUB_OUTPUT`.
- **Syntax:** `run: echo "{key}={value}" >> $GITHUB_OUTPUT`

#### Smell 4: Over-privileged Permissions
- **Problem:** Overly permissive token.
- **Solution:** Add `permissions: contents: read` (or specific rights) to top-level or job.

#### Smell 5: Missing Job Timeout (⚠️ EXCEPTION FOR REUSABLE WORKFLOWS)
- **Problem:** Jobs running indefinitely.
- **Solution:** Add `timeout-minutes: 60` to jobs.
- **🚨 CRITICAL EXCEPTION:** DO NOT add timeout if the job uses a Reusable Workflow (e.g., `uses: ./.github/...`). It causes syntax errors per Defense Rule 2.
```yaml
# ❌ WRONG:
jobs:
  reusable:
    uses: ./.github/workflows/check.yml
    timeout-minutes: 60  # ❌ ERROR

# ✅ CORRECT:
jobs:
  reusable:
    uses: ./.github/workflows/check.yml  # No timeout
  
  regular:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # OK
```

#### Smell 6 & 7: Concurrency
- **Smell 6 (PR):** Add `concurrency` group with `cancel-in-progress: true`.
- **Smell 7 (Branch):** Add `concurrency` group for branches.

#### Smell 8: Missing Path Filter (⚠️ LIST SYNTAX & LOCATION REQUIRED)
- **Problem:** Wasteful runs on doc changes.
- **Solution:** Add `paths-ignore` to `push` or `pull_request`.
- **🚨 SYNTAX:** MUST use list format with hyphens (`-`) per Defense Rule 3.
- **🚨 LOCATION:** MUST be INSIDE `on.push` or `on.pull_request`, NOT at job level or as sibling to `on`.
- **🚨 FORBIDDEN:** NEVER put `paths-ignore` inside `jobs` or at workflow root.

**❌ WRONG - paths-ignore at job level:**
```yaml
jobs:
  build:
    paths-ignore:  # ❌ ERROR: Wrong location
      - '**.md'
    runs-on: ubuntu-latest
```

**❌ WRONG - paths-ignore as sibling to on:**
```yaml
on:
  push:
paths-ignore:  # ❌ ERROR: Wrong location
  - '**.md'
```

**✅ CORRECT - paths-ignore inside on.push:**
```yaml
on:
  push:
    paths-ignore:  # ✅ Correct location
      - '**.md'    # List format with hyphen
      - 'docs/**'
  pull_request:
    paths-ignore:  # ✅ Can also be in pull_request
      - '**.md'
```

#### Smell 9: Run on Fork (Schedule) (⚠️ LOCATION CONSTRAINT)
- **Problem:** Scheduled runs waste resources on forks.
- **Solution:** Add repo owner check.
- **🚨 CRITICAL LOCATION:** `on: schedule` DOES NOT support `if` per Defense Rule 1. You MUST add `if: github.repository_owner == ...` at the **JOB level**.
```yaml
# ✅ CORRECT:
on:
  schedule:
    - cron: '0 0 * * *'  # No if here

jobs:
  scheduled-job:
    if: github.repository_owner == 'owner'  # Check at job level
    runs-on: ubuntu-latest
```

#### Smell 10: Run on Fork (Artifact) (⚠️ LOCATION CONSTRAINT)
- **Problem:** Artifact uploads waste resources on forks.
- **Solution:** Add check before upload.
- **🚨 CRITICAL LOCATION:** Add `if: github.repository_owner == ...` to the **STEP** using `upload-artifact`. NEVER in `on` per Defense Rule 1.
```yaml
# ✅ CORRECT:
steps:
  - name: Upload artifact
    uses: actions/upload-artifact@v4
    if: github.repository_owner == 'owner'  # Check at step level
    with:
      name: build
      path: dist/
```
"""

    # ==============================================================================
    # PART 3. YAML SYNTAX GENERATION RULES (MUST PRESERVE)
    # 목표: Semantic repair 중에도 YAML 파싱 에러 방지
    # ==============================================================================

    YAML_GENERATION_RULES = """
### ⚡ IRONCLAD YAML SYNTAX RULES (NO EXCEPTIONS) ⚡

#### Rule 1: Quote Wildcards and Globs
- **ALWAYS quote** strings containing wildcards: `*`, `?`, `[`, `]`

#### Rule 2: FORCE Block Scalar (`|`) for `run` with Special Cases
- Use pipe (`|`) when `run` contains: colons, blank lines, multi-line commands
- Keep ALL command text exactly the same

#### Rule 3: QUOTE ENTIRE `if` Conditions with Colons
- If `if` expression contains `:`, quote the WHOLE condition

#### Rule 4: Strict Indentation (2 Spaces)
- Use exactly 2 spaces per level. NO TABS.

#### Rule 5: NO MARKDOWN FENCES OR BACKTICKS (CRITICAL)
- **ABSOLUTELY FORBIDDEN:** Backtick characters (`, ```, ``````) in YAML output
- **DO NOT** use markdown code block syntax
- **VERIFICATION:** Output must NOT contain ANY backtick (`) character
- **Return RAW YAML TEXT ONLY**

#### Rule 6: `concurrency` Placement for NEW Additions (Smell 6, 7)
- **WHEN ADDING NEW `concurrency`** (for Smell 6 or Smell 7 fixes):
  - **ALWAYS place at workflow-level** (root of YAML, before `jobs:` section)
  - **NEVER add inside** `on:`, `on.push:`, `on.pull_request:`, or any trigger section
  
- **WHEN `concurrency` ALREADY EXISTS:**
  - **KEEP IT AS-IS** (preserve existing location - workflow-level or job-level)
  - **ONLY update values** if needed (e.g., add `cancel-in-progress: true`)

**EXAMPLES FOR NEW ADDITIONS:**

**✅ CORRECT - Add concurrency at workflow root:**
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

concurrency:            # ✅ NEW concurrency at workflow root
  group: ${{{{ github.workflow }}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
```

**❌ WRONG - Adding concurrency inside trigger:**
```yaml
on:
  push:
    branches: [main]
    concurrency:        # ❌ NEVER add here
      group: build
```

**EXISTING concurrency - PRESERVE:**
```yaml
# If workflow already has concurrency at job-level:
jobs:
  build:
    concurrency:        # ✅ KEEP existing job-level concurrency
      group: existing
    runs-on: ubuntu-latest
    # Don't add another concurrency at workflow-level
```

#### Rule 7: NO Duplicate Keys When Adding Smells (CRITICAL) 👯
- **CONTEXT:** When fixing smells (e.g., adding `permissions`, `concurrency`, `env`), you might accidentally create duplicate keys
- **RULE:** Before adding a new top-level section, CHECK if it already exists
- **Official Syntax:** YAML mappings cannot have duplicate keys
  - Reference: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions

**STRICT INSTRUCTION:**
1. **CHECK:** Does `jobs:`, `on:`, `permissions:`, `env:`, or `concurrency:` ALREADY EXIST?
2. **IF EXISTS:** MERGE your smell fix INTO the existing block (don't duplicate the key)
3. **IF NOT EXISTS:** Add the new top-level key

**EXAMPLE - Adding permissions (Smell 4):**

**❌ WRONG - Duplicate permissions:**
```yaml
permissions:
  contents: read        # Existing

# ... jobs below ...

permissions:            # ❌ DUPLICATE - Error!
  issues: write         # Smell 4 fix
```

**✅ CORRECT - Merged permissions:**
```yaml
permissions:
  contents: read        # Existing
  issues: write         # ✅ Merged Smell 4 fix
```

**EXAMPLE - Adding concurrency (Smell 6/7):**

**❌ WRONG - Duplicate concurrency:**
```yaml
concurrency:
  group: existing

# ... later ...
concurrency:            # ❌ DUPLICATE - Error!
  group: ${{{{ github.workflow }}}}
  cancel-in-progress: true
```

**✅ CORRECT - Update existing concurrency:**
```yaml
concurrency:
  group: existing
  cancel-in-progress: true  # ✅ Added to existing block
```

#### Rule 8: YAML Structure Types When Fixing Smells (CRITICAL) 🏗️
- **CONTEXT:** When adding filters (Smell 8) or modifying triggers, use correct YAML types
- **RULE:** Follow GitHub Actions syntax for mappings vs. sequences
  - Reference: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions

**A. When Adding Path Filters (Smell 8):**

**❌ WRONG - paths-ignore as mapping:**
```yaml
on:
  push:
    paths-ignore:
      docs: true        # ❌ Wrong - not a mapping
```

**✅ CORRECT - paths-ignore as sequence:**
```yaml
on:
  push:
    paths-ignore:
      - '**.md'          # ✅ List with dash
      - 'docs/**'
```

**B. When Modifying Triggers:**

**✅ CORRECT - Event names are keys (no dash):**
```yaml
on:
  push:                  # ✅ Key (no dash)
    branches: [main]
  pull_request:          # ✅ Key (no dash)
    branches: [main]
```

**❌ WRONG - Events as list:**
```yaml
on:
  - push:                # ❌ Don't use dash for event names
      branches: [main]
```

**C. Special Rules:**

1. **`needs:`** - Can be scalar (string) OR sequence (list), NEVER mapping
   - ✅ CORRECT: `needs: build`
   - ✅ CORRECT: `needs: [build, test]`
   - ❌ WRONG: `needs:\n  build: true`

2. **`secrets:`** - For reusable workflows, can be mapping OR `inherit` keyword
   - ✅ CORRECT: `secrets:\n  TOKEN: ${{{{ secrets.TOKEN }}}}`
   - ✅ CORRECT: `secrets: inherit`
   - ❌ WRONG: `secrets:\n  - TOKEN: value` (not a list)

3. **Empty sections MUST be removed:**
   - ❌ WRONG: `tags:` (no values)
   - ❌ WRONG: `env:` (no variables)
   - ❌ WRONG: `paths-ignore:` (no paths)
   - ✅ CORRECT: Remove the entire empty section

**D. Structure Conversion Patterns (CRITICAL FIXES):**

1. **Shorthand to Full Syntax (Triggers):**
   - ❌ WRONG: `on: [push]` → `push: []` (Empty list - loses event meaning)
   - ❌ WRONG: `on: [push]` → `push: {{}}` (Empty mapping - also wrong)
   - ✅ CORRECT: `on: [push]` → `on:\n  push:`
   
   **Example fix:**
   ```yaml
   # Original shorthand:
   on: [push, pull_request]
   
   # ❌ WRONG - Conversion creates empty sequences:
   on:
     push: []          # ERROR - empty list
     pull_request: []  # ERROR - empty list
   
   # ✅ CORRECT - Proper full syntax:
   on:
     push:             # Correct - empty mapping (or can have filters)
     pull_request:     # Correct - empty mapping (or can have filters)
   ```

2. **Filter Placement (Nesting Rule):**
   - `tags`, `branches`, `paths`, `paths-ignore` MUST be INSIDE the trigger (push/pull_request/etc.)
   - ❌ WRONG: `on:\n  push:\n  tags: [v*]` (tags is sibling to push)
   - ✅ CORRECT: `on:\n  push:\n    tags: [v*]` (tags nested inside push)
   
   **Example fix:**
   ```yaml
   # Original with tags at wrong level:
   on:
     push:
       branches: [main]
     tags:           # ❌ WRONG - tags is sibling to push
       - v*
   
   # ✅ CORRECT - Tags INSIDE push:
   on:
     push:
       branches: [main]
       tags:         # ✅ Correct - nested under push
         - v*
   ```

**EXAMPLES:**

**❌ WRONG - Empty tags:**
```yaml
on:
  push:
    tags:                # ❌ Empty - remove this
```

**✅ CORRECT - Removed empty section:**
```yaml
on:
  push:
    branches: [main]     # ✅ Removed empty tags section
```
"""
    
    prompt = f"""### ROLE ###
You are a "Professional DevOps Engineer" who fixes ONLY the 'Specific Code Smell List' in GitHub Actions workflows according to best practices.

### STRICT INSTRUCTIONS (MOST IMPORTANT) ###
GOAL: Fix ONLY the 'Detected Semantic Smell List' listed below according to GitHub best practices.

### STRICT PROHIBITIONS (Guardrails): ###
- NEVER fix smells or other code quality issues not listed.
- NEVER change code not directly related to smell fixes.
- Fix smells while maintaining the core functionality, behavior sequence, if conditions, and other structural/logical flow of the existing workflow.

{ACTIONLINT_DEFENSE_RULES}

{SMELL_FIX_INSTRUCTIONS}

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

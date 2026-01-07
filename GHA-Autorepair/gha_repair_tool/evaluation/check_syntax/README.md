# 📋 Syntax Checker for GitHub Actions Workflows

## 주요 기능

### 1. YAML 구문 검증
- `yaml.safe_load()`를 사용해 YAML 파싱 가능 여부 확인
- 파싱 실패 시 오류 메시지 수집

### 2. actionlint 검증 (evaluator.py와 동일한 로직)
- `main.py`와 동일한 방식으로 `process_runner.run_actionlint()` 호출
- **syntax-check** 오류와 **expression** 오류만 필터링
- 다른 타입의 오류(permissions, deprecated-commands 등)는 무시
- `evaluator.py`의 `_evaluate_syntax_success()` 메서드와 동일한 로직 사용

### 3. 결과 출력
- 콘솔에 요약 통계 출력 (유효/무효 비율)
- YAML 파싱 실패 파일 목록
- actionlint 검증 실패 파일 목록 (상위 10개)

### 4. 결과 저장
- **JSON 파일**: `syntax_check_{dir_name}_results.json` (상세 결과)
- **CSV 파일**: `syntax_check_{dir_name}_results.csv` (통계용)

---

## 사용법

```bash
# 1. 기본 사용 (data_original 디렉토리, 최대 100개 파일)
python evaluation/check_syntax/check_original_syntax.py

# 2. 다른 디렉토리 지정
python evaluation/check_syntax/check_original_syntax.py --input-dir data_repair_baseline

# 3. 최대 파일 수 지정
python evaluation/check_syntax/check_original_syntax.py --input-dir data_original --max-files 50

# 4. 출력 디렉토리 지정
python evaluation/check_syntax/check_original_syntax.py --input-dir data_gha_repair --output-dir results

# 5. 모든 옵션 조합
python evaluation/check_syntax/check_original_syntax.py \
  --input-dir data_repair_two_phase \
  --max-files 100 \
  --output-dir evaluation_results
```

---

## 검증 결과 (100개 파일 기준)

### 실행 커맨드

```bash
# 가상환경 활성화
cd /Users/nam/Desktop/repository/Catching-Smells/GHA-Autorepair/gha_repair_tool
source venv/bin/activate

# data_original 검증
python evaluation/check_syntax/check_original_syntax.py --input-dir data_original --max-files 100

# data_repair_baseline 검증
python evaluation/check_syntax/check_original_syntax.py --input-dir data_repair_baseline --max-files 100

# data_repair_two_phase 검증
python evaluation/check_syntax/check_original_syntax.py --input-dir data_repair_two_phase --max-files 100

# data_gha_repair 검증
python evaluation/check_syntax/check_original_syntax.py --input-dir data_gha_repair --max-files 100
```

---

### 📊 1. data_original (원본)

```
================================================================================
구문 검증 결과 요약
================================================================================
총 파일 수: 100

YAML 파싱 결과:
  ✅ 유효: 60 (60.0%)
  ❌ 무효: 40 (40.0%)

actionlint 검증 결과:
  ✅ 통과: 0 (0.0%)
  ❌ 실패: 100 (100.0%)
     - syntax-check 오류: 99개 파일
     - expression 오류: 6개 파일
================================================================================
```

**분석**: 100개 파일 모두 구문 오류 존재, YAML 파싱도 40% 실패

---

### 📊 2. data_repair_baseline (Baseline 복구)

```
================================================================================
구문 검증 결과 요약
================================================================================
총 파일 수: 99

YAML 파싱 결과:
  ✅ 유효: 97 (98.0%)
  ❌ 무효: 2 (2.0%)

actionlint 검증 결과:
  ✅ 통과: 87 (87.9%)
  ❌ 실패: 12 (12.1%)
     - syntax-check 오류: 10개 파일
     - expression 오류: 2개 파일
================================================================================
```

**분석**: YAML 파싱 98% 성공, actionlint 통과율 **87.9%** ✅

---

### 📊 3. data_repair_two_phase (Two-Phase 복구)

```
================================================================================
구문 검증 결과 요약
================================================================================
총 파일 수: 100

YAML 파싱 결과:
  ✅ 유효: 98 (98.0%)
  ❌ 무효: 2 (2.0%)

actionlint 검증 결과:
  ✅ 통과: 67 (67.0%)
  ❌ 실패: 33 (33.0%)
     - syntax-check 오류: 26개 파일
     - expression 오류: 9개 파일
================================================================================
```

**분석**: YAML 파싱 98% 성공, actionlint 통과율 **67.0%**

---

### 📊 4. data_gha_repair (GHA-Repair 복구 - 기본 3개 규칙)

```
================================================================================
구문 검증 결과 요약
================================================================================
총 파일 수: 100

YAML 파싱 결과:
  ✅ 유효: 92 (92.0%)
  ❌ 무효: 8 (8.0%)

actionlint 검증 결과:
  ✅ 통과: 59 (59.0%)
  ❌ 실패: 41 (41.0%)
     - syntax-check 오류: 35개 파일
     - expression 오류: 8개 파일
================================================================================
```

**분석**: YAML 파싱 92% 성공, actionlint 통과율 **59.0%**

---

### 📊 5. data_gha_repair (개선된 5개 IRONCLAD 규칙) ✨ NEW

```
================================================================================
구문 검증 결과 요약
================================================================================
총 파일 수: 100

YAML 파싱 결과:
  ✅ 유효: 95 (95.0%)
  ❌ 무효: 5 (5.0%)

actionlint 검증 결과:
  ✅ 통과: 68 (68.0%)
  ❌ 실패: 32 (32.0%)
     - syntax-check 오류: 30개 파일
     - expression 오류: 4개 파일
================================================================================
```

**분석**: YAML 파싱 **95% 성공** ✅, actionlint 통과율 **68.0%** 🎯

#### 프롬프트 개선 내용

기존 3개 규칙을 **5개 IRONCLAD 규칙**으로 개선:

```yaml
#### Rule 1: Quote Wildcards and Globs
- **ALWAYS quote** strings containing wildcards: `*`, `?`, `[`, `]`
- Examples with ✅/❌ format

#### Rule 2: FORCE Block Scalar (`|`) for `run` with Colons
- If a `run` command contains a colon (`:`) followed by a space, you **MUST** use the pipe (`|`) style
- Quoting is NOT enough (it causes conflicts)

#### Rule 3: QUOTE ENTIRE `if` Conditions with Colons
- If an `if` expression contains a colon, quote the **WHOLE** condition

#### Rule 4: Strict Indentation (2 Spaces)
- Use **exactly 2 spaces** per level. NO TABS
- Content inside `|` block must be indented **2 spaces deeper** than the parent key

#### Rule 5: NO MARKDOWN FENCES
- **DO NOT** output ```yaml or ``` tags
- Return **RAW YAML TEXT ONLY**
```

#### 개선 효과

| 지표 | 기존 (3개 규칙) | 개선 (5개 규칙) | 변화 |
|------|----------------|----------------|------|
| **YAML 파싱 성공** | 92/100 (92%) | 95/100 (95%) | **+3%p** ⬆️ |
| **YAML 파싱 실패** | 8개 | 5개 | **-3개** ✅ |
| **actionlint 통과** | 59/100 (59%) | 68/100 (68%) | **+9%p** ⬆️ |
| **syntax-check 오류** | 35개 | 30개 | **-5개** ✅ |
| **expression 오류** | 8개 | 4개 | **-4개** ✅ |

**핵심 개선사항**:
- ✅ YAML 파싱 성공률 92% → **95%** (목표 달성!)
- ✅ actionlint 통과율 59% → **68%** (+9%p 대폭 향상)
- ✅ syntax-check 오류 **5개 감소**
- ✅ expression 오류 **4개 감소**
- ✅ 실패 파일 총 **8개 → 5개**로 감소

---

## 📈 비교 분석 (최종 업데이트)

| 항목 | data_original | baseline | two_phase | gha_repair (기존) | **gha_repair (개선)** |
|------|---------------|----------|-----------|-------------------|----------------------|
| **총 파일** | 100 | 99 | 100 | 100 | 100 |
| **YAML 파싱 성공** | 60 (60%) | 97 (98%) | 98 (98%) | 92 (92%) | **95 (95%)** ⬆️ |
| **actionlint 통과** | 0 (0%) | **87 (87.9%)** | **67 (67.0%)** | 59 (59.0%) | **68 (68.0%)** ⬆️ |
| **syntax-check 오류 파일** | 99 | 10 | 26 | 35 | **30** ⬇️ |
| **expression 오류 파일** | 6 | 2 | 9 | 8 | **4** ⬇️ |

### 핵심 인사이트 (최종)

1. **YAML 파싱 개선**: 
   - 원본 60% → 모든 복구 방법 92~98%로 대폭 개선 ✅
   - **프롬프트 개선으로 92% → 95%** (추가 +3%p) 🎯

2. **actionlint 통과율 순위**: 
   - 🥇 **Baseline: 87.9%** (가장 우수)
   - 🥈 **GHA-Repair (개선): 68.0%** ← NEW! (+9%p)
   - 🥉 **Two-Phase: 67.0%**
   - **GHA-Repair (기존): 59.0%**

3. **프롬프트 개선 효과 (GHA-Repair)**:
   - YAML 파싱: 92% → **95%** (+3개 파일)
   - actionlint 통과: 59% → **68%** (+9개 파일)
   - 총 실패 감소: **8개 → 5개** (-37.5%)

4. **구문 복구 성능**: 
   - Baseline이 여전히 최고 성능 (87.9%)
   - **개선된 GHA-Repair가 Two-Phase 추월** (68% > 67%)

5. **evaluator.py와 일치**: 
   - `syntax-check`와 `expression` 타입 오류만 실패로 간주
   - `permissions`, `deprecated-commands` 등은 무시
   - 일관된 평가 기준 적용 ✅

### 프롬프트 개선 전략 성과

**개선 전 (3개 규칙)**:
- 모호한 표현: "Use block scalar", "2-space indent"
- 예시 부족
- 성공률: 92% (YAML), 59% (actionlint)

**개선 후 (5개 IRONCLAD 규칙)**:
- 강력한 표현: "**MUST use**", "**FORCE**", "**NO EXCEPTIONS**"
- ✅/❌ 구체적 예시 제공
- 명확한 기준: "2 spaces **deeper**", "**WHOLE** condition"
- 성공률: **95% (YAML)**, **68% (actionlint)**

**결론**: 프롬프트 엔지니어링만으로 **+3%p (YAML), +9%p (actionlint)** 향상 달성! �

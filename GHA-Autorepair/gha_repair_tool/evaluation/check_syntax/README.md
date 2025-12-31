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

### 📊 4. data_gha_repair (GHA-Repair 복구)

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

## 📈 비교 분석 (수정된 결과)

| 항목 | data_original | baseline | two_phase | gha_repair |
|------|---------------|----------|-----------|------------|
| **총 파일** | 100 | 99 | 100 | 100 |
| **YAML 파싱 성공** | 60 (60%) | 97 (98%) | 98 (98%) | 92 (92%) |
| **actionlint 통과** | 0 (0%) | **87 (87.9%)** | **67 (67.0%)** | **59 (59.0%)** |
| **syntax-check 오류 파일** | 99 | 10 | 26 | 35 |
| **expression 오류 파일** | 6 | 2 | 9 | 8 |

### 핵심 인사이트 (업데이트)

1. **YAML 파싱 개선**: 모든 복구 방법이 60% → 92~98%로 대폭 개선 ✅
2. **actionlint 통과율 (수정)**: 
   - **Baseline: 87.9%** (가장 우수) 🏆
   - **Two-Phase: 67.0%** 
   - **GHA-Repair: 59.0%**
3. **구문 복구 성능**: Baseline이 압도적으로 우수 (12개 파일만 실패)
4. **evaluator.py와 일치**: 이제 evaluator의 syntax_success 결과와 동일한 기준 적용

### 중요 변경 사항

**이전 (잘못된 기준)**:
- 모든 actionlint 오류를 실패로 간주
- Baseline: 9.1%, Two-Phase: 5.0%, GHA-Repair: 7.0%

**현재 (올바른 기준)**:
- `syntax-check`와 `expression` 타입 오류만 실패로 간주
- `permissions`, `deprecated-commands` 등은 무시
- Baseline: 87.9%, Two-Phase: 67.0%, GHA-Repair: 59.0%

이제 evaluator.py의 결과와 일관성 있는 측정이 가능합니다! 🎯

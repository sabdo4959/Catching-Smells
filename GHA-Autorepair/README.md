# GHA-Autor### 2. 배치 처리 시스템
- 여러 파일을 자동으로 순차 처리
- 진행 상황 모니터링 및 상세 로깅
- 오류 처리 및 복구 통계 제공
- **이중 로그 시스템**: INFO와 DEBUG 레벨 분리

### 3. 고급 로깅 시스템
- **INFO 로그**: 요약 정보 및 진행 상황 (터미널 출력과 동일)
- **DEBUG 로그**: 상세 실행 과정 및 디버깅 정보
- **Smell #23 추적**: 대상 외 스멜(YAML 파싱 오류) 가시성 확보
- **logs 폴더 구조**: 체계적인 로그 파일 관리

### 4. 평가 시스템
- **구문 성공률**: syntax-check/expression 오류 해결 비율
- **스멜 제거율**: 대상 스멜 제거 성공 비율  
- **편집 거리**: 원본 대비 변경량의 적절성tHub Actions 워크플로우 자동 복구 도구

GitHub Actions 워크플로우의 구문 오류와 코드 스멜을 자동으로 감지하고 복구하는 도구입니다.

## 🚀 주요 기능뮴

### 1. Baseline 모드 (통합 복구)
- **actionlint 구문 검사** + **smell detection** + **LLM 복구**를 한 번의 요청으로 처리
- 구문 오류와 코드 스멜을 동시에 감지하여 통합 프롬프트로 복구
- 빠르고 효율적인 단일 패스 복구

### 2. 배치 처리 시스템
- 여러 파일을 자동으로 순차 처리
- 진행 상황 모니터링 및 상세 로깅
- 오류 처리 및 복구 통계 제공

### 3. 평가 시스템
- **구문 성공률**: syntax-check/expression 오류 해결 비율
- **스멜 제거율**: 대상 스멜 제거 성공 비율  
- **편집 거리**: 원본 대비 변경량의 적절성

## 📁 프로젝트 구조

```
GHA-Autorepair/
├── gha_repair_tool/
│   ├── main.py                    # 메인 진입점
│   ├── baseline_auto_repair.py    # 배치 처리 스크립트
│   ├── logs/                      # 로그 파일 저장소
│   │   ├── *_info.log            # INFO 레벨 로그
│   │   └── *_debug.log           # DEBUG 레벨 로그
│   ├── evaluation/
│   │   └── evaluator.py          # 평가 시스템
│   ├── utils/
│   │   ├── process_runner.py     # 외부 도구 실행 (smell #23 추적)
│   │   ├── llm_api.py           # LLM API 인터페이스
│   │   └── yaml_parser.py       # YAML 파싱 및 검증
│   ├── data_original/           # 원본 워크플로우 파일들
│   ├── data_repair_baseline/    # 복구된 파일들
│   ├── failed_files/            # 실패 분석용 파일들
│   └── test_evaluation_results/ # 평가 결과
```

## 🔧 설치 및 설정

### 1. 환경 설정
```bash
cd GHA-Autorepair/gha_repair_tool
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. API 키 설정
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 외부 도구 설정
- **actionlint**: `/Users/nam/Desktop/repository/Catching-Smells/smell_linter/actionlint_mac`
- **gha-ci-detector**: `/Users/nam/Desktop/repository/Catching-Smells/RQ3/gha-ci-detector_paper/src`

## 🚀 사용법

### 1. 단일 파일 복구
```bash
python main.py --input data_original/workflow.yml --output . --mode baseline
```

### 2. 배치 처리 (100개 파일)
```bash
python baseline_auto_repair.py \
    --input-dir data_original \
    --output-dir data_repair_baseline \
    --log-file baseline_repair_20251030 \
    --max-files 100
```

**출력**: 
- `logs/baseline_repair_20251030_info.log` (요약 로그)
- `logs/baseline_repair_20251030_debug.log` (상세 로그)

### 3. 평가 실행
```bash
python -m evaluation.evaluator \
    --original-dir data_original \
    --repaired-dir data_repair_baseline \
    --output-dir test_evaluation_results \
    --results-file evaluation_results.json
```

## 📊 평가 메트릭

### 1. 구문 성공률 (Syntax Success Rate)
```python
syntax_success_rate = (
    resolved_syntax_errors / total_syntax_errors
) * 100
```
- **대상**: `syntax-check`, `expression` 타입 오류만
- **측정**: actionlint로 복구 전후 비교

### 2. 스멜 제거율 (Smell Removal Rate)
```python
smell_removal_rate = (
    (original_smells - remaining_smells) / original_smells
) * 100
```
- **대상 스멜**: `{'1', '4', '5', '10', '11', '15', '16'}`
- **측정**: gha-ci-detector로 복구 전후 비교

### 3. 편집 거리 (Edit Distance)
```python
edit_distance = levenshtein_distance(original, repaired)
normalized_distance = edit_distance / max(len(original), len(repaired))
```
- **측정**: 문자 단위 Levenshtein 거리
- **정규화**: 파일 크기 대비 상대적 변경량

## 🔍 스멜 감지 시스템

### TARGET_SMELLS 필터링
```python
TARGET_SMELLS = {'1', '4', '5', '10', '11', '15', '16'}
```

### Smell #23 추적 시스템
```python
# 대상 스멀이 0개일 때 #23 추적 로그 예시
2025-10-30 11:40:03,860 - utils.process_runner - INFO - 총 0개 대상 스멜 파싱됨 (1,4,5,10,11,15,16번만)
2025-10-30 11:40:03,860 - utils.process_runner - INFO - 대상 스멜 0개이지만 스멜 #23 (YAML 파싱 오류) 12개 발견됨
```

### 이중 로그 시스템
```
INFO 로그: logs/baseline_repair_20251030_info.log (59줄 - 요약)
DEBUG 로그: logs/baseline_repair_20251030_debug.log (832줄 - 상세)
```

## � 실행 결과 분석 (2025-10-30)

### 100개 파일 배치 처리 결과
```
총 처리 시간: 3466.0초 (약 58분)
총 파일: 100
성공: 94 (94.0%)
실패: 6 (6.0%)
평균 처리 시간: 34.66초/파일
```

### 실패 원인 분석
1. **YAML 문법 오류** (2건): LLM이 잘못된 YAML 구조 생성
2. **GitHub Actions 구조 오류** (2건): Job에서 `runs-on`, `steps` 필드 누락  
3. **LLM API 타임아웃** (1건): 대량 오류로 인한 프롬프트 과부하
4. **재시도 성공** (1건): 일시적 오류 후 성공

### 7단계 검증 시스템 효과
- YAML 문법 검증으로 잘못된 파일 저장 방지
- GitHub Actions 필수 필드 검증
- 품질 제어를 통한 신뢰성 확보

## 🔧 주요 컴포넌트

### 1. baseline_auto_repair.py
```python
def process_file_baseline(input_file, output_dir):
    """단일 파일을 baseline 모드로 처리"""
    result = run_baseline_mode(input_file, output_dir)
    return result
```

### 2. evaluation/evaluator.py
```python
class WorkflowEvaluator:
    def evaluate_syntax_success(self, original_path, repaired_path):
        """구문 성공률 계산"""
    
    def evaluate_smell_removal(self, original_path, repaired_path):
        """스멜 제거율 계산"""
    
    def calculate_edit_distance(self, original_content, repaired_content):
        """편집 거리 계산"""
```

### 3. utils/process_runner.py
```python
def run_actionlint(yaml_file_path):
    """actionlint 구문 검사 실행"""

def run_smell_detector(yaml_file_path):
    """GHA CI Detector 스멜 감지 실행"""
```

## 🎯 Baseline 모드 워크플로우

1. **원본 워크플로우 읽기**
2. **actionlint 구문 검사** - syntax-check/expression 오류만 필터링
3. **Smell Detector 실행** - 대상 스멜 감지 및 #23 추적
4. **통합 프롬프트 생성** - 구문 오류 + 스멜 정보 결합
5. **LLM API 호출** - gpt-4o-mini 모델 사용
6. **수정된 YAML 추출** - 코드 블록에서 YAML 파싱
7. **결과 검증 및 저장** - 유효성 검사 후 파일 저장

## 📝 로그 및 모니터링

### 상세 로깅
- 파일별 처리 시간 측정
- 각 단계별 결과 로깅
- 오류 발생 시 상세 정보 기록
- Smell #23 추적으로 필터링 투명성 확보

### 진행 상황 모니터링
- 실시간 진행률 표시 (`[1/100] 처리 중`)
- 성공/실패 통계
- 평균 처리 시간 계산

## 🔬 연구 목적

이 도구는 GitHub Actions 워크플로우 자동 복구에 대한 연구를 위해 개발되었습니다:

- **Baseline 평가**: 구문+스멜 통합 복구의 효과성 측정
- **성능 지표**: 구문 성공률, 스멜 제거율, 편집 거리
- **대규모 실험**: 100개 파일 배치 처리로 통계적 신뢰성 확보

## ⚡ 성능 특성

- **처리 속도**: 파일당 평균 15-20초 (LLM API 응답 시간 포함)
- **성공률**: 초기 테스트에서 95% 이상
- **메모리 사용량**: 파일별 독립 처리로 최적화
- **확장성**: 배치 크기 조정 가능

## 🛠️ 개발 히스토리

- **2025-10-30**: 
  - Baseline 모드 구현 및 평가 시스템 완성
  - **Smell #23 추적**: 대상 외 스멜 가시성 확보
  - **이중 로그 시스템**: INFO/DEBUG 레벨 분리로 상세 분석 가능
  - **배치 처리**: 100개 파일 자동 복구 시스템 (94% 성공률)
  - **7단계 검증**: YAML 품질 제어 시스템으로 신뢰성 확보
  - **실패 분석**: 6개 실패 케이스 상세 원인 분석 완료

## 🔬 검증된 성능 지표

- **처리 속도**: 파일당 평균 34.66초 (LLM API 응답 포함)
- **성공률**: 94% (100개 파일 중 94개 성공)
- **로그 정확도**: 터미널 출력과 100% 일치하는 파일 로깅
- **품질 제어**: 7단계 검증으로 잘못된 YAML 저장 방지
- **확장성**: 배치 크기 조정 가능, 실패 파일 재처리 지원

## 🚀 최신 업데이트 (2025-10-30)

### ✨ 주요 개선사항
1. **이중 로그 시스템**: 
   - INFO 로그: 요약 정보 (59줄/2파일)
   - DEBUG 로그: 상세 정보 (832줄/2파일)
   - 터미널과 동일한 출력을 파일로 저장

2. **Smell #23 추적 기능**:
   - 대상 외 스멜(YAML 파싱 오류) 개수 로깅
   - 필터링 투명성 확보로 분석 정확도 향상

3. **7단계 검증 시스템**:
   - YAML 문법 검증
   - GitHub Actions 필수 필드 검증
   - 품질 제어를 통한 신뢰성 확보

4. **실패 원인 분석**:
   - 6개 실패 케이스 상세 분석 완료
   - LLM 품질 이슈 및 복잡도 한계 파악

### 📁 로그 파일 구조
```
logs/
├── baseline_repair_20251030_info.log    # 요약 로그 (터미널 출력 수준)
├── baseline_repair_20251030_debug.log   # 상세 로그 (디버깅 정보 포함)
├── failed_analysis_info.log             # 실패 파일 재분석 요약
└── failed_analysis_debug.log            # 실패 파일 재분석 상세
```

---

*이 도구는 GitHub Actions 워크플로우의 품질 향상과 자동화된 복구 연구를 목적으로 개발되었습니다.*

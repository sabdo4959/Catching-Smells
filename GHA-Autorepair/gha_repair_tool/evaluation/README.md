# 베이스라인 평가 시스템

GitHub Actions 워크플로우의 베이스라인 복구 성능을 평가하는 종합적인 시스템입니다.

## 📊 평가 지표

### 1. 구문 성공률 (Syntax Success Rate %) 💯
- **측정**: 최종 결과물이 actionlint 구문/스키마 검사를 통과하는 비율
- **의미**: 얼마나 자주 실행 가능한(Valid) 결과물을 안정적으로 만들어내는가?

### 2. 타겟 스멜 제거율 (Target Smell Removal Rate %)
- **측정**: 
  - 구문 성공한 파일: `[(초기 스멜 수 - 최종 스멜 수) / 초기 스멜 수] * 100%`
  - 구문 실패한 파일: 0% (페널티)
  - 그룹 전체 평균 계산
- **의미**: 목표했던 **핵심 품질 문제(스멜)**를 얼마나 효과적으로 해결했는가?
- **타겟 스멀**: 1, 4, 5, 10, 11, 15, 16번

### 3. 수정 범위 적절성 (Edit Scope Appropriateness) ✂️
- **측정**: 구문 성공한 파일에 대해 원본과 최종 결과물 간의 Tree Edit Distance
- **의미**: 얼마나 최소한의 변경으로 복구를 수행했는가? (값이 낮을수록 정밀함)

## 🏗️ 시스템 구조

```
evaluation/
├── evaluator.py           # 핵심 평가 엔진
├── batch_evaluator.py     # 배치 처리 시스템
├── test_evaluator.py      # 테스트 스크립트
├── demo.py               # 사용 예제
└── README.md             # 이 문서
```

## 🚀 사용법

### 1. 단일 파일 평가

```bash
python evaluation/evaluator.py \
  --original input.yml \
  --repaired output.yml \
  --group-name "test"
```

### 2. 여러 파일 배치 처리

```bash
python evaluation/batch_evaluator.py \
  --files file1.yml file2.yml file3.yml \
  --output-dir ./results
```

### 3. 디렉토리 전체 처리

```bash
python evaluation/batch_evaluator.py \
  --directory /path/to/workflows \
  --pattern "*.yml" \
  --max-files 100
```

### 4. CSV 파일에서 파일 목록 읽기

```bash
python evaluation/batch_evaluator.py \
  --csv file_list.csv \
  --column file_path \
  --max-files 50
```

## 📋 출력 파일

### JSON 결과 파일
```json
{
  "group_name": "baseline_batch",
  "total_files": 10,
  "syntax_success_rate": 80.0,
  "avg_smell_removal_rate": 75.5,
  "avg_edit_distance": 42.3,
  "detailed_results": [...],
  "evaluation_time": "2025-10-30T11:02:22.744277"
}
```

### CSV 상세 결과
```csv
original_file,repaired_file,syntax_success,initial_smells,final_smells,smell_removal_rate,edit_distance,processing_time,error_message
input1.yml,output1.yml,True,4,0,100.00,43,1.004,
input2.yml,output2.yml,True,4,2,50.00,39,0.558,
```

## 🧪 테스트

### 평가 시스템 테스트
```bash
python evaluation/test_evaluator.py
```

### 데모 실행
```bash
python evaluation/demo.py
```

## 📦 의존성

### 필수 패키지
- `ruamel.yaml`: YAML 파싱 및 처리
- `pathlib`: 파일 경로 처리 
- `dataclasses`: 데이터 구조
- `difflib`: Edit Distance 계산

### 외부 도구
- **actionlint**: 구문 검사
- **gha-ci-detector**: 스멀 탐지

## 🔧 설정

### 타겟 스멀 번호 변경
```python
# evaluator.py의 BaselineEvaluator 클래스에서
self.TARGET_SMELLS = {'1', '4', '5', '10', '11', '15', '16'}
```

### 출력 디렉토리 설정
```python
evaluator = BaselineEvaluator(output_dir="./custom_results")
```

## 📈 성능 고려사항

### 처리 시간
- **단일 파일**: ~1초 (actionlint + smell detection)
- **배치 처리**: 파일당 ~1초 + 오버헤드
- **대용량 배치**: `max_files` 옵션으로 제한 권장

### 메모리 사용량
- **파일당**: ~1-5MB (YAML 크기에 따라)
- **배치 결과**: 상세 결과를 메모리에 유지
- **대용량 처리**: 청크 단위 처리 권장

## 🐛 트러블슈팅

### 일반적인 문제

1. **actionlint 바이너리 없음**
   ```
   해결: smell_linter/ 디렉토리에 actionlint_mac 또는 actionlint_linux 확인
   ```

2. **gha-ci-detector 모듈 없음**
   ```
   해결: RQ3/gha-ci-detector_paper/ 디렉토리와 Python 환경 확인
   ```

3. **파일 경로 오류**
   ```
   해결: 절대 경로 사용 권장
   ```

### 로그 레벨 조정
```bash
python evaluation/batch_evaluator.py --log-level DEBUG [다른 옵션들]
```

## 📊 예제 결과

### 베이스라인 평가 결과 예시
```
📊 baseline_batch 그룹 평가 결과
==================================================
총 파일 수: 50

1. 구문 성공률: 82.0% (41/50)
2. 평균 타겟 스멀 제거율: 67.8%
3. 평균 수정 범위 (Edit Distance): 38.5

평가 완료 시각: 2025-10-30T11:02:22.744277
```

## 🔄 확장 가능성

### 새로운 평가 지표 추가
1. `evaluator.py`의 `EvaluationResult` 클래스에 필드 추가
2. `evaluate_file()` 메서드에 계산 로직 추가
3. `GroupEvaluationSummary`에 집계 로직 추가

### 다른 복구 방법 평가
1. `batch_evaluator.py`의 `run_baseline_mode()` 호출 부분 변경
2. 새로운 평가 모드 추가

## 📚 참고 자료

- [actionlint 문서](https://github.com/rhysd/actionlint)
- [gha-ci-detector 프로젝트](../../../RQ3/gha-ci-detector_paper/)
- [GitHub Actions 스펙](https://docs.github.com/en/actions)

## 📄 라이선스

이 프로젝트의 라이선스를 따릅니다.

# GitHub Actions YAML 자동 복구 도구

## 📋 개요

GitHub Actions YAML 파일의 구문 오류와 코드 스멜을 자동으로 수정하는 도구입니다. 베이스라인 방법과 혁신적인 2단계 아키텍처를 모두 지원합니다.

## 🏗️ 지원 방법

### 1. 베이스라인 방법 (기존)
- 모든 문제를 한 번에 처리하는 단일 단계 접근법
- 높은 구문 성공률 (87.9%)

### 2. 2단계 아키텍처 (신규) 🆕
- Phase 1: 구문 오류 수정 (actionlint → LLM)
- Phase 2: 코드 스멜 제거 (smell detection → LLM)
- **코드 스멜 제거에서 54% 향상 달성!**

## 🚀 빠른 시작

### 환경 설정
```bash
cd GHA-Autorepair/gha_repair_tool
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### API 키 설정
`.env` 파일 생성:
```
OPENAI_API_KEY=your_api_key_here
```

## 📖 사용법

### 단일 파일 처리

#### 베이스라인 방법
```bash
python main.py --input data_original/파일명 --output . --mode baseline
```

#### 2단계 방법 (추천)
```bash
python main.py --input data_original/파일명 --output . --mode two_phase
```

### 배치 처리 (대량 파일)

#### 2단계 복구 (100개 파일)
```bash
python batch_two_phase_repair.py \
  --input-dir data_original \
  --output-dir data_repair_two_phase \
  --max-files 100
```

#### 베이스라인 복구
```bash
python baseline_auto_repair.py \
  --input-dir data_original \
  --output-dir data_repair_baseline \
  --max-files 100
```

### 성능 평가

#### 2단계 결과 평가
```bash
python evaluation/batch_two_phase_evaluator.py \
  --original-dir data_original \
  --repaired-dir data_repair_two_phase
```

## 📊 성능 비교

| 지표 | 베이스라인 | 2단계 방법 | 개선도 |
|------|------------|------------|--------|
| 구문 성공률 | 87.9% | 68.0% | -19.9% |
| **스멸 제거율** | 23.9% | **36.9%** | **+54%** |
| Edit Distance | 32.1 | 32.7 | +0.6 |

## 📁 주요 파일

- `main.py`: 단일 파일 처리
- `batch_two_phase_repair.py`: 2단계 배치 복구
- `baseline_auto_repair.py`: 베이스라인 배치 복구
- `evaluation/batch_two_phase_evaluator.py`: 2단계 평가
- `batch_evaluator.py`: 베이스라인 평가

## 📈 평가 결과

- `evaluation_results/two_phase/`: 2단계 방법 평가 결과
- `evaluation_results/baseline/`: 베이스라인 평가 결과
- `final_comparison_report.md`: 상세 비교 분석

## 🎯 추천 사용 시나리오

### 코드 품질 개선이 중요한 경우
- **추천**: 2단계 방법
- **이유**: 54% 향상된 스멜 제거율

### 구문 오류 수정이 우선인 경우
- **추천**: 베이스라인 방법
- **이유**: 87.9%의 높은 구문 성공률

## 📚 상세 문서

자세한 내용은 [상세 문서](README_TWO_PHASE.md)를 참조하세요.

---

**최신 업데이트**: 2025년 11월 1일  
**주요 성과**: 2단계 아키텍처로 스멜 제거 54% 향상 달성

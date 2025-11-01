# Catching-Smells
SCAM2024 논문 - GitHub Actions YAML 코드 스멜 탐지 및 자동 수정

## 📋 프로젝트 개요

이 리포지토리는 GitHub Actions YAML 파일의 코드 스멜을 탐지하고 자동으로 수정하는 연구 프로젝트입니다. 특히 혁신적인 2단계 아키텍처를 통해 기존 방법 대비 **스멜 제거에서 54% 향상**을 달성했습니다.

## 🚀 주요 성과

### 2단계 아키텍처 구현 및 검증
- **Phase 1**: 구문 오류 수정 (actionlint → LLM)
- **Phase 2**: 코드 스멀 제거 (smell detection → LLM)
- **결과**: 100개 파일 평가에서 스멀 제거율 54% 향상 (23.9% → 36.9%)

## 📁 프로젝트 구조

### 🔧 GHA-Autorepair/
GitHub Actions YAML 자동 복구 시스템
- **2단계 아키텍처**: 문제 분리를 통한 전문화된 처리
- **베이스라인 비교**: 기존 방법과의 정량적 성능 비교
- **대규모 평가**: 100개 실제 파일을 통한 실증 검증

**주요 파일:**
- `batch_two_phase_repair.py`: 2단계 배치 복구 시스템
- `evaluation/batch_two_phase_evaluator.py`: 성능 평가 시스템
- `final_comparison_report.md`: 상세 성능 비교 분석

### 🔍 RQ3/
코드 스멀 탐지 도구 평가
- `gha-ci-detector/`: GitHub Actions CI 스멀 탐지기
- `gha-ci-detector_paper/`: 논문용 탐지기 구현

### 👃 smell_linter/
actionlint 기반 구문 오류 탐지
- GitHub Actions YAML 구문 검증 도구

### 📊 data/
연구 데이터셋
- 실제 GitHub 리포지토리에서 수집한 YAML 파일들
- 다양한 처리 단계별 결과 파일들

## 🎯 핵심 기여도

### 1. 문제 분리 접근법의 효과 입증
기존의 모든 문제를 한 번에 해결하려는 접근법과 달리, 구문 오류와 코드 스멜을 단계별로 분리하여 처리함으로써 각 문제에 특화된 해결책을 제공했습니다.

### 2. 실증적 성능 검증
100개의 실제 GitHub Actions 파일을 대상으로 한 대규모 평가를 통해 2단계 방법의 우수성을 정량적으로 증명했습니다.

### 3. 재현 가능한 연구 환경
모든 코드, 데이터, 평가 결과를 공개하여 연구의 투명성과 재현성을 보장했습니다.

## 📊 주요 결과

| 지표 | 베이스라인 | 2단계 방법 | 개선도 |
|------|------------|------------|--------|
| **구문 성공률** | 87.9% | 68.0% | -19.9% |
| **스멀 제거율** | 23.9% | **36.9%** | **+54%** 🎯 |
| **Edit Distance** | 32.1 | 32.7 | +0.6 |

## 🚀 시작하기

### 1. 2단계 자동 복구 시스템 사용
```bash
cd GHA-Autorepair/gha_repair_tool
python batch_two_phase_repair.py --input-dir data_original --output-dir output
```

### 2. 성능 평가 실행
```bash
python evaluation/batch_two_phase_evaluator.py --original-dir data_original --repaired-dir output
```

자세한 사용법은 [GHA-Autorepair README](GHA-Autorepair/gha_repair_tool/README.md)를 참조하세요.

## 📚 관련 논문

이 프로젝트는 SCAM2024에 제출된 논문의 구현체입니다. 논문에서는 GitHub Actions YAML 파일의 코드 스멜 탐지 및 분류에 대한 연구를 다루고 있으며, 본 리포지토리는 탐지된 스멀의 자동 수정에 대한 후속 연구입니다.

## 🔗 관련 도구

- **actionlint**: GitHub Actions YAML 구문 검증
- **gha-ci-detector**: GitHub Actions 코드 스멀 탐지
- **OpenAI GPT-4**: 자동 수정을 위한 언어 모델

---

**연구 기간**: 2024년 ~ 2025년  
**주요 성과**: 2단계 아키텍처로 스멀 제거 54% 향상 달성  
**평가 규모**: 100개 실제 GitHub Actions YAML 파일

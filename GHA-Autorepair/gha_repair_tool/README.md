# GitHub Actions YAML 자동 복구 도구

## 📋 개요

GitHub Actions YAML 파일의 구문 오류와 코드 스멜을 자동으로 수정하는 도구입니다. OpenAI GPT 모델과 Ollama 로컬 모델을 모두 지원## 📊 성능 비교

### 기존 OpenAI 모델 성능
| 지표 | 베이스라인 | 2단계 방법 | 개선도 |
|------|------------|------------|----## 📚 상세 문서

- [2단계 아키텍처 상세 문서](README_TWO_PHASE.md)
- [검증 시스템 문서](verification/README.md)
- [LLM API 사용법](utils/llm_api.py) - 코드 내 문서화

## 🔗 관련 링크

- [Ollama 공식 사이트](https://ollama.ai/)
- [Llama 3.1 모델](https://ollama.ai/library/llama3.1)
- [CodeGemma 모델](https://ollama.ai/library/codegemma)
- [CodeLlama 모델](https://ollama.ai/library/codellama)

---

**최신 업데이트**: 2025년 11월 5일  
**주요 성과**: 
- 2단계 아키텍처로 스멜 제거 54% 향상 달성
- Ollama 로컬 모델 지원으로 API 비용 제로화
- llama3.1:8b 모델 66.7% 성공률 달성구문 성공률 | 87.9% | 68.0% | -19.9% |
| **스멜 제거율** | 23.9% | **36.9%** | **+54%** |
| Edit Distance | 32.1 | 32.7 | +0.6 |

### Ollama 모델 테스트 결과 🆕 (100개 파일)
| 모드 | 성공률 | 실제 파일 | 평균 처리 시간 | 총 처리 시간 | 특징 |
|------|---------|----------|---------------|-------------|------|
| **베이스라인** | **85%** | 99/100 | 79.6초/파일 | 2.2시간 | 한 번에 모든 문제 해결, 가장 안정적 |
| GHA-Repair | 30% | 100/100 | 99.3초/파일 | 2.8시간 | 가이드 프롬프트 사용 |
| 2단계 | 10% | 100/100 | 93.3초/파일 | 2.6시간 | Phase별 처리, 복잡한 로직 |

### 소규모 테스트 vs 대규모 테스트 비교 (llama3.1:8b)
| 테스트 규모 | 베이스라인 | 2단계 | 특징 |
|------------|------------|-------|------|
| **3개 파일** | **100%** (3/3) | 20% (1/5) | 소규모에서 높은 성능 |
| **100개 파일** | **85%** (85/100) | 10% (10/100) | 대규모에서 성능 저하 |

### 성능 분석
- **베이스라인 모드**: 가장 안정적, 대규모 처리에 적합
- **GHA-Repair 모드**: 중간 성능, 가이드 프롬프트 효과
- **2단계 모드**: 복잡한 로직으로 성능 저하, 추가 최적화 필요

### 주요 개선사항 �
- **환경변수 기반 모델 전환**: 기존 배치 스크립트 수정 없이 LLM 모델 변경 가능
- **영어 프롬프트 최적화**: Llama 모델 성능 향상
- **다중 모델 지원**: 3개 Ollama 모델 동시 지원 
- **하위 호환성**: 기존 main.py, 배치 스크립트 코드 변경 없이 동작
- **일관된 파일명 규칙**: 모든 모델에서 동일한 출력 파일명 사용라인 방법과 혁신적인 2단계 아키텍처를 제공합니다.

## 🤖 지원 LLM 모델

### OpenAI 모델
- `gpt-4o-mini` (기본값)
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`

### Ollama 로컬 모델 🆕
- `llama3.1:8b` - 범용 모델 (추천)
- `codegemma:7b` - 코드 전문 모델
- `codellama:7b` - 코드 전문 모델

## 🏗️ 지원 방법

### 1. 베이스라인 방법 (기존)
- 모든 문제를 한 번에 처리하는 단일 단계 접근법
- 높은 구문 성공률 (87.9%)

### 2. 2단계 아키텍처 (신규) 🆕
- Phase 1: 구문 오류 수정 (actionlint → LLM)
- Phase 2: 코드 스멜 제거 (smell detection → LLM)
- **코드 스멜 제거에서 54% 향상 달성!**
- **영어 프롬프트 최적화로 Llama 모델 성능 개선**

## 🚀 빠른 시작

### 환경 설정
```bash
cd GHA-Autorepair/gha_repair_tool
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### LLM 설정

#### OpenAI 사용 (기본값)
`.env` 파일 생성:
```
OPENAI_API_KEY=your_api_key_here
```

#### Ollama 로컬 모델 사용 🆕
```bash
# 환경변수 설정
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=llama3.1:8b
export OLLAMA_URL=http://115.145.178.160:11434/api/chat

# 또는 직접 명령줄에서 실행
LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1:8b python main.py --input file.yml --output . --mode baseline
```

## 📖 사용법

### 단일 파일 처리

#### OpenAI 모델 사용 (기본값)
```bash
# 베이스라인 방법
python main.py --input data_original/파일명 --output . --mode baseline

# 2단계 방법 (추천)
python main.py --input data_original/파일명 --output . --mode two_phase

# 2단계 플러스 가이드 프롬프트 
python main.py --input data_original/파일명 --output . --mode gha_repair
```

#### Ollama 로컬 모델 사용 🆕


### 배치 처리 (대량 파일)

#### 기존 스크립트 + 환경변수 방식 🆕 (추천)
기존 배치 스크립트를 **수정 없이** 환경변수만으로 다양한 모델 사용 가능:

```bash
# llama3.1:8b 베이스라인 복구 (100개 파일)
LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1:8b python baseline_auto_repair.py \
  --input-dir data_original \
  --output-dir llama3_8b/data_repair_baseline \
  --max-files 100 \
  --log-file llama3_baseline_100files

# llama3.1:8b 2단계 복구 (5개 파일 테스트)
LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1:8b python batch_two_phase_repair.py \
  --input-dir data_original \
  --output-dir llama3_8b/data_repair_two_phase \
  --max-files 5 \
  --log-file llama3_two_phase_test_5files

# CodeGemma 모델로 테스트
LLM_PROVIDER=ollama OLLAMA_MODEL=codegemma:7b python baseline_auto_repair.py \
  --input-dir data_original \
  --output-dir codegemma_7b/data_repair_baseline \
  --max-files 50 \
  --log-file codegemma_baseline_50files

# CodeLlama 모델로 GHA-Repair 모드
LLM_PROVIDER=ollama OLLAMA_MODEL=codellama:7b python batch_gha_repair.py \
  --input-dir data_original \
  --output-dir codellama_7b/data_gha_repair \
  --max-files 50 \
  --log-file codellama_gha_repair_50files
```

#### OpenAI 기본 배치 처리

##### 베이스라인 복구
```bash
python baseline_auto_repair.py \
  --input-dir data_original \
  --output-dir data_repair_baseline \
  --max-files 100 \
  --log-file baseline_repair_100files
```

##### 2단계 복구
```bash
python batch_two_phase_repair.py \
  --input-dir data_original \
  --output-dir data_repair_two_phase \
  --max-files 100 \
  --log-file two_phase_repair_100files
```

##### GHA-Repair 복구
```bash
python batch_gha_repair.py \
  --input-dir data_original \
  --output-dir data_gha_repair \
  --max-files 100 \
  --log-file gha_repair_100files
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

### 핵심 스크립트
- `main.py`: 단일 파일 처리 (다중 모델 지원)
- `utils/llm_api.py`: 통합 LLM API (OpenAI + Ollama) 🆕

### 배치 처리
- `batch_two_phase_repair.py`: 2단계 배치 복구
- `baseline_auto_repair.py`: 베이스라인 배치 복구

### 평가 및 검증
- `evaluation/batch_two_phase_evaluator.py`: 2단계 평가
- `batch_evaluator.py`: 베이스라인 평가
- `verification/enhanced_batch_verification.py`: 향상된 검증 시스템 🆕

### 출력 디렉토리 구조 🆕
```
llama3.1_8b/
├── data_repair_baseline/     # llama3.1:8b 베이스라인 결과
└── data_repair_gha_repair/   # llama3.1:8b GHA-Repair 결과

codegemma_7b/
├── data_repair_baseline/     # codegemma:7b 베이스라인 결과
└── data_repair_gha_repair/   # codegemma:7b GHA-Repair 결과

evaluation_results/
├── baseline/                 # OpenAI 베이스라인 평가
├── two_phase/               # OpenAI 2단계 평가
├── gha_repair/              # OpenAI GHA-Repair 평가
└── llama_comparisons/       # Ollama 모델 비교 🆕
```

## 📈 평가 결과

- `evaluation_results/two_phase/`: 2단계 방법 평가 결과
- `evaluation_results/baseline/`: 베이스라인 평가 결과
- `final_comparison_report.md`: 상세 비교 분석

## 🎯 추천 사용 시나리오

### 로컬 환경에서 안정적 처리 🆕
- **추천**: Ollama + llama3.1:8b + 베이스라인 모드
- **성능**: 85% 성공률, 79.6초/파일
- **이유**: 로컬 실행, API 비용 없음, 가장 안정적 성능
- **용도**: 대량 배치 처리, 프로덕션 환경

### 코드 품질 개선이 중요한 경우
- **추천**: OpenAI + 2단계 방법
- **이유**: 54% 향상된 스멜 제거율 (OpenAI 기준)
- **용도**: 코드 품질 중시, 정밀한 스멜 제거

### 구문 오류 수정이 우선인 경우
- **추천**: Ollama llama3.1:8b + 베이스라인 모드
- **이유**: 85%의 높은 구문 성공률, 빠른 처리
- **용도**: 신속한 문법 수정, CI/CD 파이프라인

### 실험적 접근이 필요한 경우
- **추천**: Ollama llama3.1:8b + GHA-Repair 모드
- **성능**: 30% 성공률
- **이유**: 가이드 프롬프트로 향상된 성능
- **용도**: 특별한 프롬프트 최적화 실험

### 대량 배치 처리
- **추천**: 환경변수 + 베이스라인 스크립트 🆕
- **명령어**: `LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1:8b python baseline_auto_repair.py --max-files 100`
- **이유**: 기존 코드 재사용, 안정적 처리, 비용 효율적
- **성능**: 85% 성공률로 검증됨

## 🔄 최신 업데이트 (2025.11.06)

### 새로운 기능
- ✅ **Ollama 로컬 모델 지원**: llama3.1:8b, codegemma:7b, codellama:7b
- ✅ **환경변수 기반 모델 전환**: 기존 배치 스크립트 수정 없이 사용 가능
- ✅ **영어 프롬프트 최적화**: Llama 모델 성능 개선
- ✅ **다중 모델 통합 API**: 하나의 인터페이스로 모든 모델 지원
- ✅ **일관된 파일명 규칙**: 모든 모델에서 동일한 출력 파일명 사용
- ✅ **하위 호환성 보장**: 기존 코드 수정 없이 동작

### 대규모 테스트 결과 (100개 파일)
- **llama3.1:8b 베이스라인**: **85% 성공률** (85/100 파일)
- **llama3.1:8b GHA-Repair**: 30% 성공률 (30/100 파일)  
- **llama3.1:8b 2단계**: 10% 성공률 (10/100 파일)
- 총 처리 시간: 2.2-2.8시간 (100개 파일)
- 평균 처리 시간: 79.6-99.3초/파일

### 성능 분석
- **베이스라인 모드가 가장 안정적**: 대규모 배치 처리에 적합
- **2단계 모드는 추가 최적화 필요**: 복잡한 로직으로 성능 저하
- **환경변수 방식 완벽 호환**: 기존 배치 스크립트 그대로 사용 가능

### 배치 처리 검증
- **코드 수정 불필요**: `LLM_PROVIDER=ollama OLLAMA_MODEL=llama3.1:8b python baseline_auto_repair.py`
- **일관된 출력 파일명**: `{파일명}_baseline_repaired.yml` 유지
- **기존 평가 시스템 호환**: 이전 실험 결과와 직접 비교 가능

## 📚 상세 문서

자세한 내용은 [상세 문서](README_TWO_PHASE.md)를 참조하세요.

---

**최신 업데이트**: 2025년 11월 1일  
**주요 성과**: 2단계 아키텍처로 스멜 제거 54% 향상 달성

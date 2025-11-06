# GHA-Repair Tool Prompts Documentation

## 📋 개요

GHA-Repair 도구에서 사용되는 모든 LLM 프롬프트들을 정리한 문서입니다. 각 모드별로 다른 프롬프트 전략을 사용하여 최적의 수리 성능을 달성합니다.

## 🔧 프롬프트 종류

### 1. 베이스라인 프롬프트 (Baseline Mode)
- **목적**: 구문 오류와 의미론적 스멜을 한 번에 통합 처리
- **언어**: 영어 (Ollama 모델 최적화)
- **특징**: 간단하고 직접적인 수리 요청

### 2. 2단계 프롬프트 (Two-Phase Mode)
- **Phase 1**: 구문 오류 수정 전용 프롬프트
- **Phase 2**: 의미론적 스멜 수정 전용 프롬프트
- **특징**: 각 단계별 전문화된 접근

### 3. 가이드 프롬프트 (GHA-Repair Mode)
- **특징**: 엄격한 가이드라인과 금지사항 포함
- **목적**: 정밀한 수정과 부작용 최소화
- **효과**: 54% 향상된 스멜 제거율 달성

---

## 1️⃣ 베이스라인 프롬프트

### 목적
모든 문제(구문 오류 + 의미론적 스멜)를 한 번에 수정하는 통합 접근법

### 프롬프트 템플릿
```
Please fix the issues found in this GitHub Actions workflow.

**Original Workflow:**
```yaml
{yaml_content}
```

**Issues Found:**

**Syntax Errors (actionlint):**
{actionlint_errors_list}

**Semantic Smells:**
{smells_list}

**Fix Request:**
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
```

### 장점
- 간단하고 직관적
- 모든 문제를 한 번에 해결
- 높은 구문 성공률 (87.9%)

### 단점
- 복잡한 문제에서 일부 누락 가능
- 스멜 제거율이 상대적으로 낮음

---

## 2️⃣ 2단계 프롬프트

### Phase 1: 구문 오류 수정 프롬프트

#### 목적
actionlint에서 감지된 구문 오류만 집중적으로 수정

#### 프롬프트 템플릿 (Simple Mode)
```
You are an expert GitHub Actions workflow developer. Please fix the syntax errors in the following YAML workflow file.

**Original YAML:**
```yaml
{yaml_content}
```

**Syntax Errors Detected by actionlint:**
{error_list}

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
```

### Phase 2: 의미론적 스멜 수정 프롬프트

#### 목적
Phase 1에서 구문이 수정된 YAML의 코드 스멜만 수정

#### 프롬프트 템플릿 (Simple Mode)
```
You are an expert GitHub Actions workflow developer. Please fix the code smells and improve the quality of the following YAML workflow file.

**Current YAML (syntax errors already fixed):**
```yaml
{yaml_content}
```

**Code Smells Detected:**
{smells_list}

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
```

### 장점
- 각 단계별 전문화
- 단계별 검증 가능
- 문제 분리로 정확도 향상

### 단점
- 2번의 LLM 호출 필요
- 처리 시간 증가

---

## 3️⃣ 가이드 프롬프트 (GHA-Repair Mode)

### Phase 1: 가이드 구문 수정 프롬프트

#### 목적
엄격한 가이드라인으로 구문 오류만 정밀하게 수정

#### 프롬프트 템플릿
```
### ROLE ###
You are a "Precision Linter Robot" that specializes ONLY in fixing syntax errors in GitHub Actions YAML files. Your sole mission is to resolve the given error list.

### STRICT INSTRUCTIONS (MOST IMPORTANT) ###
GOAL: Fix ONLY the 'Detected Syntax Errors' listed below.

### STRICT PROHIBITIONS (Guardrails): ###
- NEVER modify or change any code that is not mentioned in the error list.
- NEVER touch semantic parts such as workflow logic, step order, if conditions, run script contents, etc.
- NEVER add or remove new steps or jobs.
- Preserve original comments and formatting as much as possible.

**Original YAML:**
```yaml
{yaml_content}
```

**Detected Syntax Errors:**
{error_list}

**Response Format:**
```yaml
# Fixed workflow
```
```

### Phase 2: 가이드 의미론적 수정 프롬프트

#### 목적
엄격한 제약 조건 하에서 스멜만 선택적으로 수정

#### 프롬프트 템플릿
```
### ROLE ###
You are a "Professional DevOps Engineer" who fixes ONLY the 'Specific Code Smell List' in GitHub Actions workflows according to best practices.

### STRICT INSTRUCTIONS (MOST IMPORTANT) ###
GOAL: Fix ONLY the 'Detected Semantic Smell List' listed below according to GitHub best practices.

### STRICT PROHIBITIONS (Guardrails): ###
- NEVER fix smells or other code quality issues not listed. (e.g., don't arbitrarily improve efficiency)
- NEVER change code not directly related to smell fixes. (e.g., don't modify permissions key to fix timeout smell)
- Fix smells while maintaining the core functionality, behavior sequence, if conditions, and other structural/logical flow of the existing workflow

**Current YAML (syntax errors already fixed):**
```yaml
{yaml_content}
```

**Code Smells to Fix:**
{smells_list}

Provide an improved YAML that fixes each smell according to GitHub Actions best practices:

**Response Format:**
```yaml
# Fixed workflow
```
```

### 장점
- **54% 향상된 스멸 제거율** 달성
- 부작용 최소화
- 정밀한 수정 보장
- 원본 기능 보존

### 단점
- 프롬프트 복잡도 증가
- 구문 성공률 일부 감소 (-19.9%)

---

## 📊 프롬프트 성능 비교

| 모드 | 구문 성공률 | 스멸 제거율 | 특징 |
|------|-------------|-------------|------|
| **베이스라인** | 87.9% | 23.9% | 간단, 빠름 |
| **2단계 Simple** | 68.0% | 36.9% | 단계별 처리 |
| **GHA-Repair** | 68.0% | **36.9%** | **정밀, 최고 성능** |

## 🎯 프롬프트 선택 가이드

### 베이스라인 모드 추천 상황
- 빠른 구문 수정이 필요한 경우
- 단순한 워크플로우
- CI/CD 파이프라인에서 신속 처리

### 2단계 Simple 모드 추천 상황
- 중간 수준의 품질 개선
- 단계별 검증이 필요한 경우
- 학습/연구 목적

### GHA-Repair 모드 추천 상황 ⭐
- **최고 품질의 코드 개선이 필요한 경우**
- 프로덕션 환경의 중요한 워크플로우
- 스멸 제거가 우선인 경우
- 부작용 최소화가 중요한 경우

## 🔄 프롬프트 개선 히스토리

### v1.0 (초기)
- 한국어 프롬프트 사용
- 단순한 수정 요청

### v2.0 (2단계 도입)
- Phase 1/2 분리
- 전문화된 프롬프트

### v3.0 (영어 최적화) 🆕
- Ollama/Llama 모델 지원을 위한 영어 변환
- 성능 향상 및 안정성 개선

### v4.0 (가이드 강화) ⭐
- 엄격한 가이드라인 도입
- Guardrails 시스템 적용
- **54% 스멸 제거율 향상 달성**

---

## 💡 프롬프트 작성 팁

### 1. 명확한 역할 정의
```
### ROLE ###
You are a "Precision Linter Robot"...
```

### 2. 엄격한 제약사항
```
### STRICT PROHIBITIONS ###
- NEVER modify...
- NEVER touch...
```

### 3. 구체적인 목표
```
GOAL: Fix ONLY the 'Detected Syntax Errors'
```

### 4. 일관된 출력 형식
```
**Response Format:**
```yaml
# Fixed workflow
```
```

### 5. 언어 선택
- **영어**: Ollama/Llama 모델에 최적화
- **한국어**: 개발자 이해도 향상 (주석용)

---

**문서 버전**: v4.0  
**최종 업데이트**: 2025년 11월 5일  
**주요 성과**: GHA-Repair 모드로 54% 스멸 제거율 향상 달성

# Verification Module

GitHub Actions 워크플로우 수정 방법들의 구조적 안전성을 검증하고 비교하는 모듈입니다.

## 📋 주요 구성요소

### 🔧 검증 도구들

- **`key_structure_verifier.py`**: 키 구조 검증 핵심 로직
- **`structural_verifier.py`**: 구조적 안전성 검증 (고급 버전)
- **`batch_key_structure_verification.py`**: 대량 파일 배치 검증
- **`compare_methods.py`**: 여러 방법의 검증 결과 비교 분석

### 📊 분석 도구들

- **`verifier.py`**: 기본 검증 엔진
- **`parser.py`**: YAML 파싱 도구
- **`translator.py`**: 구조 변환 도구

## 🚀 사용법

### 1. 단일 파일 키 구조 검증

```bash
python -c "
from key_structure_verifier import KeyStructureVerifier
verifier = KeyStructureVerifier()
result = verifier.verify_key_structure('original.yml', 'modified.yml')
print('안전' if result else '위험')
"
```

### 2. 배치 검증 실행

```bash
# baseline 방법 검증
python batch_key_structure_verification.py data_original data_repair_baseline baseline

# gha_repair 방법 검증  
python batch_key_structure_verification.py data_original data_gha_repair gha_repair

# two_phase 방법 검증
python batch_key_structure_verification.py data_original data_repair_two_phase two_phase
```

### 3. 방법별 결과 비교

```bash
# 기본 비교 (results 폴더에서 검증 결과 로드)
python compare_methods.py

# 사용자 지정 경로로 비교
python compare_methods.py --results-dir ./results --base-dir .. --output comparison_result.json
```

## 📁 결과 파일들

### `results/` 디렉토리
- **`key_structure_verification_baseline.json`**: baseline 방법 검증 결과
- **`key_structure_verification_gha_repair.json`**: gha_repair 방법 검증 결과  
- **`key_structure_verification_two_phase.json`**: two_phase 방법 검증 결과
- **`methods_comparison.json`**: 3가지 방법 종합 비교 결과
- **`structural_safety_comparison_report.md`**: 상세 분석 보고서

## 🎯 검증 기준

### 키 구조 검증 (Key Structure Verification)
- **목적**: 원본과 수정본의 YAML 키 계층 구조 동일성 확인
- **철학**: 값(value)은 블랙박스 처리, 키(key) 구조만 검증
- **허용**: smell 수정을 위한 안전한 키 추가 (permissions, timeout-minutes, concurrency 등)
- **금지**: 기존 키 구조 변경, 삭제, 순서 변경

### 구조적 안전성 기준
1. ✅ **안전**: 키 구조 100% 보존 + smell 수정 키만 추가
2. ❌ **위험**: 기존 키 구조 변경/삭제 감지
3. ⚠️ **오류**: YAML 파싱 실패 (원본 파일 문제)

## 📈 성능 지표

최근 100개 파일 대상 검증 결과:

| 방법 | 구조적 안전율 | 순위 |
|------|-------------|------|
| **GHA-Repair** | **6.0%** | 🥇 |
| **Two-Phase** | **3.0%** | 🥈 |
| **Baseline** | **2.0%** | 🥉 |

## 🔍 주요 발견사항

1. **GHA-Repair의 우수성**: baseline 대비 3배 향상된 구조적 안전성
2. **실제 데이터 품질**: 대부분 원본 파일에 YAML 구문 오류 존재
3. **Guided Prompt 효과**: 구조 보존에서 명확한 차별화 성능

## 🛠️ 개발자 가이드

### 새로운 검증 방법 추가

1. `batch_key_structure_verification.py`에 새 방법 추가
2. `compare_methods.py`의 `methods` 딕셔너리에 등록
3. 해당 방법의 출력 디렉토리 설정

### 검증 기준 수정

`key_structure_verifier.py`의 `is_safe_key_addition()` 메소드에서 허용 키 목록 수정

---

**생성 일시**: 2025년 11월 2일  
**버전**: v1.0  
**검증 대상**: GitHub Actions 워크플로우 YAML 파일

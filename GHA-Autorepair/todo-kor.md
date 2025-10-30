GHA-Repair 프로젝트 설정 에이전트 업무 목록 (Ablation Study 포함 최종)
⭐ 전체 목표: 현재 Visual Studio 솔루션 내에 GHA-Repair 시스템을 위한 초기 Python 프로젝트 구조와 기본 코드 파일들을 생성합니다. 
이 시스템은 GitHub Actions 워크플로우를 위한 2단계 자동 복구 프로세스와 SMT 기반 정형 검증을 구현하며, Ablation Study를 위한 다양한 실행 모드를 지원해야 합니다.

✅ 핵심 요구사항:

언어: Python

모듈성: 기능을 논리적인 모듈/파일로 분리합니다.

명확성: 각 함수/클래스의 목적을 설명하는 기본 docstring과 주석을 추가합니다.

자리 표시자: 상세 구현이 필요한 영역에는 명확한 # TODO: 주석을 사용합니다.

Ablation 지원: main.py에서 실행 모드(예: --mode=baseline, --mode=two_phase_simple, --mode=gha_repair)를 선택할 수 있도록 하고, 각 모듈은 해당 모드에 맞게 동작하도록 구현합니다.

📌 업무 목록:

프로젝트 루트 디렉토리 생성:

이름: gha_repair_tool

메인 스크립트 생성:

파일: gha_repair_tool/main.py

목적: 도구의 진입점. 명령줄 인수 처리(실행 모드 포함), 선택된 모드에 따라 1단계/2단계/검증 프로세스 총괄.

기본 구조:

필요한 모듈 임포트 (argparse, logging, 사용자 정의 모듈).

argparse를 사용하여 --input, --output, --mode (choices=['baseline', 'two_phase_simple', 'gha_repair']) 인수를 처리하는 로직 구현.

main() 함수 내에서 선택된 --mode에 따라 조건 분기하여 각 단계 함수를 호출하는 로직 구현.

baseline 모드: utils.llm_api.call_llm_for_baseline() 호출 (구문+스멜 통합 요청).

two_phase_simple 모드: syntax_repair.repair_syntax(use_guided_prompt=False) 호출 후, 성공 시 semantic_repair.detect_smells() 및 semantic_repair.repair_smells(use_guided_prompt=False) 호출.

gha_repair 모드: syntax_repair.repair_syntax(use_guided_prompt=True) 호출 후, 성공 시 semantic_repair.detect_smells() 및 semantic_repair.repair_smells(use_guided_prompt=True) 호출.

(선택) 최종 결과에 대해 verification.verifier.verify_equivalence() 호출하는 로직 추가.

기본 로깅 설정 구현.

1단계: 구문 복구 모듈 생성:

디렉토리: gha_repair_tool/syntax_repair

파일: gha_repair_tool/syntax_repair/repairer.py

목적: actionlint를 사용하여 기본적인 YAML 포맷 및 GHA 스키마 오류 수정. 다양한 프롬프트 모드 지원.

기본 구조:

repair_syntax(input_yaml_path, use_guided_prompt=True) 함수 정의:

use_guided_prompt 매개변수를 추가하여 프롬프트 종류 결정.

# TODO: utils.process_runner.run_command('actionlint ...')를 호출하여 오류 탐지 및 정보 추출 로직 구현.

# TODO: use_guided_prompt 값에 따라 단순 프롬프트 또는 가이드 프롬프트(오류 정보 포함, 다른 부분 변경 금지 제약)를 생성하는 로직 구현.

# TODO: utils.llm_api.call_llm()를 호출하는 자리 표시자 로직 구현.

# TODO: LLM의 출력을 다시 actionlint로 검증하는 로직 구현.

구문적으로 유효한 YAML 파일 경로 또는 실패 여부를 반환합니다.

파일: gha_repair_tool/syntax_repair/__init__.py (빈 파일)

2단계: 의미론적 복구 모듈 생성:

디렉토리: gha_repair_tool/semantic_repair

파일: gha_repair_tool/semantic_repair/detector.py

목적: 구문적으로 유효한 워크플로우에서 Tier-1 의미론적 스멜 탐지.

기본 구조:

detect_smells(valid_yaml_path) 함수 정의:

# TODO: 커스텀 smell_detector 실행 로직 구현.

# TODO: actionlint(의미론적 체크 위주) 실행 로직 구현.

탐지된 스멜과 위치 정보를 담은 구조화된 데이터(예: list of dicts) 반환.

파일: gha_repair_tool/semantic_repair/repairer.py

목적: 탐지된 의미론적 스멜 수정. 다양한 프롬프트 모드 지원.

기본 구조:

repair_smells(valid_yaml_path, detected_smells, use_guided_prompt=True) 함수 정의:

use_guided_prompt 매개변수를 추가하여 프롬프트 종류 결정.

# TODO: use_guided_prompt 값에 따라 단순 프롬프트 또는 가이드 프롬프트(탐지된 스멜 정보 포함, 다른 부분 변경 금지 제약)를 생성하는 로직 구현.

# TODO: utils.llm_api.call_llm()를 호출하는 자리 표시자 로직 구현.

후보 복구된 YAML 파일 경로를 반환합니다.

파일: gha_repair_tool/semantic_repair/__init__.py (빈 파일)

검증 모듈 생성:

디렉토리: gha_repair_tool/verification

파일: gha_repair_tool/verification/verifier.py

목적: SMT 기반 정형 검증으로 동작 동치성 확인.

기본 구조:

verify_equivalence(original_yaml_path, repaired_yaml_path) 함수 정의:

# TODO: utils.yaml_parser를 사용하여 두 YAML 파일 파싱.

# TODO: 파싱된 구조를 SMT 인코딩용 내부 표현으로 변환하는 자리 표시자 로직 구현.

# TODO: "구조적 및 제어 흐름 동치성" 속성을 z3-solver 제약 조건으로 인코딩하는 자리 표시자 로직 구현.

# TODO: Z3 솔버 호출 및 결과('SAFE'/'UNSAFE', 반례) 반환 로직 구현.

파일: gha_repair_tool/verification/__init__.py (빈 파일)

유틸리티 모듈 생성:

디렉토리: gha_repair_tool/utils

파일: gha_repair_tool/utils/yaml_parser.py

목적: YAML 파일 처리 (로드, 파싱, 저장) 헬퍼 함수.

기본 구조: PyYAML을 사용한 load_yaml, save_yaml 함수 (오류 처리 포함).

파일: gha_repair_tool/utils/llm_api.py

목적: LLM API 호출 래퍼 함수 및 Baseline 모드 지원.

기본 구조:

call_llm(prompt) 자리 표시자 함수.

call_llm_for_baseline(invalid_yaml_path) 함수 정의:

# TODO: invalid_yaml_path 파일을 읽고, 구문 오류와 스멜 정보를 통합한 단일 프롬프트를 생성하는 로직 구현.

# TODO: call_llm() 함수를 호출하고 결과를 반환하는 로직 구현.

파일: gha_repair_tool/utils/process_runner.py

목적: 외부 프로세스(actionlint) 실행 헬퍼 함수.

기본 구조: subprocess 모듈을 사용한 run_command(command) 함수 (stdout, stderr, 종료 코드 반환).

파일: gha_repair_tool/utils/__init__.py (빈 파일)

Requirements 파일 생성:

파일: gha_repair_tool/requirements.txt

내용: 필요한 Python 라이브러리 목록 (예: pyyaml, openai, z3-solver, pandas, scikit-learn, deepdiff, zss).

🚀 최종 지시: 위에 설명된 대로 파일 구조와 기본 Python 파일들을 생성해주세요. 특히 main.py와 각 repairer.py, llm_api.py 파일은 Ablation Study를 위한 다양한 실행 모드와 프롬프트 옵션을 처리할 수 있도록 기본 구조를 갖춰야 합니다.
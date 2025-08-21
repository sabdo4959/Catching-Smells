# collect_actionlint_results.py
# 지정된 디렉토리의 모든 GHA 워크플로우에 대해 actionlint를 실행하고,
# 그 결과를 JSON 파일로 저장합니다.

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from pprint import pprint

def check_actionlint_installed():
    """
    시스템에 actionlint가 설치되어 있는지 확인합니다.
    """
    try:
        # actionlint의 버전을 확인하는 명령어를 실행하여 설치 여부 판단
        subprocess.run(
            ["./actionlint", "-version"],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        print("✅ actionlint가 성공적으로 감지되었습니다.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ERROR: actionlint가 설치되어 있지 않거나 PATH에 없습니다.", file=sys.stderr)
        print("  Homebrew를 사용하신다면 'brew install actionlint' 명령어로 설치해주세요.", file=sys.stderr)
        print("  자세한 정보: https://github.com/rhysd/actionlint", file=sys.stderr)
        return False

def run_actionlint_on_directory(target_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    지정된 디렉토리의 모든 .yml, .yaml 파일에 대해 actionlint를 실행합니다.

    Args:
        target_dir: 분석할 워크플로우 파일들이 있는 디렉토리 경로.

    Returns:
        파일 경로를 키로, actionlint가 발견한 문제점 리스트를 값으로 하는 딕셔너리.
    """
    if not target_dir.is_dir():
        print(f"ERROR: 디렉토리를 찾을 수 없습니다: {target_dir}", file=sys.stderr)
        return {}

    all_results = {}
    # .yml과 .yaml 파일을 모두 찾습니다.
    workflow_files = list(target_dir.glob("**/*")) 
    
    total_files = len(workflow_files)
    if total_files == 0:
        print(f"WARNING: '{target_dir}' 디렉토리에서 워크플로우 파일을 찾을 수 없습니다.")
        return {}
        
    print(f"\n총 {total_files}개의 워크플로우 파일을 분석합니다...")

    for i, file_path in enumerate(workflow_files):
        # 프로젝트 루트 기준 상대 경로를 키로 사용
        relative_path_str = str(file_path)
        print(f"  [{i+1}/{total_files}] 분석 중: {relative_path_str}")

        try:
            # -format "{{json .}}" 옵션으로 각 문제를 JSON 형태로 출력
            command = ["./actionlint", "-format", "{{json .}}", str(file_path)]
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=False # actionlint는 문제를 찾으면 non-zero 코드를 반환하므로 check=False로 설정
            )

            # actionlint는 문제를 찾지 못하면 아무것도 출력하지 않습니다.
            if not process.stdout:
                all_results[relative_path_str] = []
                continue

            file_issues = []
            # 출력을 한 줄씩 읽어 JSON으로 파싱
            for line in process.stdout.strip().split('\n'):
                if line:
                    try:
                        issue = json.loads(line)
                        file_issues.append(issue)
                    except json.JSONDecodeError:
                        print(f"    WARNING: '{line}' 은(는) 유효한 JSON이 아닙니다. 건너뜁니다.", file=sys.stderr)
            
            all_results[relative_path_str] = file_issues

        except Exception as e:
            print(f"    ERROR: '{file_path}' 파일 분석 중 오류 발생: {e}", file=sys.stderr)
            all_results[relative_path_str] = [{"error": str(e)}]

    return all_results

if __name__ == "__main__":
    # 1. actionlint 설치 확인
    if not check_actionlint_installed():
        sys.exit(1)

    # 2. 커맨드라인 인자로 분석할 디렉토리 경로 받기
    if len(sys.argv) != 2:
        print(f"\n사용법: python {sys.argv[0]} <분석할_디렉토리_경로>", file=sys.stderr)
        print(f"예시: python {sys.argv[0]} .github/workflows", file=sys.stderr)
        sys.exit(1)

    target_directory = Path(sys.argv[1])

    # 3. actionlint 실행 및 결과 수집
    results = run_actionlint_on_directory(target_directory)
    
    if not results:
        print("\n분석된 결과가 없습니다. 프로그램을 종료합니다.")
        sys.exit(0)

    # 4. 최종 결과를 JSON 파일로 저장
    output_path = Path("actionlint_results.json")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 모든 분석이 완료되었습니다. 결과가 현재 디렉토리의 '{output_path}' 파일에 저장되었습니다.")
        
        # 저장된 내용 일부 출력
        print("\n--- 저장된 결과 (일부) ---")
        pprint(dict(list(results.items())[:1]))
        print("--------------------------")

    except Exception as e:
        print(f"ERROR: 결과를 파일에 저장하는 중 오류 발생: {e}", file=sys.stderr)
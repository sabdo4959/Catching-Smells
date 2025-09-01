# collect_actionlint_results_from_csv.py
# 지정된 CSV 파일에 명시된 file_hash를 기반으로 워크플로우 파일에 대해 actionlint를 실행하고,
# 그 결과를 JSON 파일로 저장합니다.

import subprocess
import json
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from pprint import pprint

def check_actionlint_installed():
    """
    시스템에 actionlint가 설치되어 있는지 확인합니다.
    """
    try:
        # actionlint의 버전을 확인하는 명령어를 실행하여 설치 여부 판단
        # Mac 환경을 고려하여 actionlint_mac 실행 파일을 사용합니다.
        subprocess.run(
            ["./actionlint_mac", "-version"],
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

def run_actionlint_on_files(csv_path: Path, workflows_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    CSV 파일에서 file_hash 목록을 읽어 해당 파일들에 대해 actionlint를 실행합니다.

    Args:
        csv_path: 분석할 파일 정보가 담긴 CSV 파일 경로.
        workflows_dir: 워크플로우 파일들이 있는 디렉토리 경로.

    Returns:
        파일 해시를 키로, actionlint가 발견한 문제점 리스트를 값으로 하는 딕셔너리.
    """
    if not csv_path.is_file():
        print(f"ERROR: CSV 파일을 찾을 수 없습니다: {csv_path}", file=sys.stderr)
        return {}
    if not workflows_dir.is_dir():
        print(f"ERROR: 워크플로우 디렉토리를 찾을 수 없습니다: {workflows_dir}", file=sys.stderr)
        return {}

    try:
        df = pd.read_csv(
            csv_path,
            encoding='utf-8',          # 인코딩을 UTF-8로 명시
            encoding_errors='ignore'   # 인코딩 오류 발생 시 무시
        )
        if 'file_hash' not in df.columns:
            print(f"ERROR: CSV 파일에 'file_hash' 컬럼이 없습니다.", file=sys.stderr)
            return {}
        # 중복 제거
        file_hashes = df['file_hash'].unique()
    except Exception as e:
        print(f"ERROR: CSV 파일 처리 중 오류 발생: {e}", file=sys.stderr)
        return {}

    all_results = {}
    total_files = len(file_hashes)
    print(f"\n총 {total_files}개의 워크플로우 파일을 분석합니다...")

    for i, file_hash in enumerate(file_hashes):
        file_path = workflows_dir / file_hash
        print(f"  [{i+1}/{total_files}] 분석 중: {file_hash}")

        if not file_path.is_file():
            print(f"    WARNING: 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
            all_results[file_hash] = [{"error": "File not found"}]
            continue

        try:
            command = ["./actionlint_mac", "-format", "{{json .}}", str(file_path)]
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=False
            )

            if not process.stdout:
                all_results[file_hash] = []
                continue

            file_issues = []
            for line in process.stdout.strip().split('\n'):
                if line:
                    try:
                        issue = json.loads(line)
                        file_issues.append(issue)
                    except json.JSONDecodeError:
                        print(f"    WARNING: '{line}' 은(는) 유효한 JSON이 아닙니다. 건너뜁니다.", file=sys.stderr)
            
            all_results[file_hash] = file_issues

        except Exception as e:
            print(f"    ERROR: '{file_path}' 파일 분석 중 오류 발생: {e}", file=sys.stderr)
            all_results[file_hash] = [{"error": str(e)}]

    return all_results

if __name__ == "__main__":
    # 1. actionlint 설치 확인
    if not check_actionlint_installed():
        sys.exit(1)

    # 2. 커맨드라인 인자로 CSV 파일 경로와 워크플로우 디렉토리 경로 받기
    if len(sys.argv) != 3:
        print(f"\n사용법: python {sys.argv[0]} <CSV_파일_경로> <워크플로우_디렉토리_경로>", file=sys.stderr)
        print(f"예시: python {sys.argv[0]} ../data/workflow_valid_false.csv /path/to/workflow_files", file=sys.stderr)
        sys.exit(1)

    csv_file_path = Path(sys.argv[1])
    workflows_directory = Path(sys.argv[2])

    # 3. actionlint 실행 및 결과 수집
    results = run_actionlint_on_files(csv_file_path, workflows_directory)
    
    if not results:
        print("\n분석된 결과가 없습니다. 프로그램을 종료합니다.")
        sys.exit(0)

    # 4. 최종 결과를 JSON 파일로 저장
    output_filename = f"actionlint_results_{csv_file_path.stem}.json"
    output_path = Path(output_filename)
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
import json
import sys
import csv
from pathlib import Path

def create_checklist_mapping() -> dict:
    """
    actionlint의 'kind' 필드를 사용자 정의 체크리스트 설명으로 매핑합니다.
    이 함수는 모든 가능한 'kind' 목록을 얻기 위해 사용됩니다.
    """
    return {
        # actionlint 'kind' -> Checklist Description
        "action": "Outdated popular actions detection at uses:",
        "deprecated-commands": "Deprecated workflow commands",
        "expression": "Type checks for expression syntax in ${{ }}",
        "runner-label": "Runner labels",
        "shell-name": "Shell name validation at shell:",
        "if-cond": "Conditions always evaluated to true at if:",
        "shellcheck": "shellcheck integration for run:",
        "pyflakes": "pyflakes integration for run:",
        "untrusted-input": "Script injection by potentially untrusted inputs",
        "job-dependency": "Job dependencies validation",
        "matrix": "Matrix values",
        "webhook-event": "Webhook events validation",
        "workflow-dispatch": "Workflow dispatch event validation",
        "glob": "Glob filter pattern syntax validation",
        "cron": "CRON syntax check at schedule:",
        "local-action": "Local action inputs validation at with:",
        "popular-action": "Popular action inputs validation at with:",
        "job-id": "Job ID and step ID uniqueness",
        "credentials": "Hardcoded credentials",
        "env-var-name": "Environment variable names",
        "permissions": "Permissions",
        "reusable-workflow": "Reusable workflows",
        "id-name": "ID naming convention",
        "context": "Availability of contexts and special functions",
        "metadata": "Action metadata syntax validation",
        "syntax-check": "Syntax check for expression ${{ }}",
    }

def create_kind_presence_csv(results_file: Path, all_kinds: list):
    """
    결과 파일을 읽고, 파일 해시별로 각 'kind'의 포함 여부를 CSV로 출력합니다.
    """
    if not results_file.is_file():
        print(f"ERROR: 결과 파일을 찾을 수 없습니다: {results_file}", file=sys.stderr)
        return

    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON 파일 파싱 실패. 파일이 손상되었을 수 있습니다. 원인: {e}", file=sys.stderr)
        return

    # CSV 출력을 위해 stdout 사용
    writer = csv.writer(sys.stdout)

    # 1. CSV 헤더 생성 및 출력
    header = ['file_hash'] + all_kinds
    writer.writerow(header)

    # 2. 각 파일(해시)별로 데이터 처리
    for file_path, issues in data.items():
        file_hash = Path(file_path).name
        
        # 해당 파일에서 발견된 모든 'kind'를 중복 없이 저장
        found_kinds = set()

        # BUG FIX: JSON 데이터의 값이 [[...]] 처럼 이중 리스트로 감싸진 경우를 처리
        actual_issues = issues
        if isinstance(issues, list) and len(issues) > 0 and isinstance(issues[0], list):
            actual_issues = issues[0]

        if not isinstance(actual_issues, list):
            continue

        for issue in actual_issues:
            if isinstance(issue, dict) and "kind" in issue:
                found_kinds.add(issue["kind"])
        
        # 3. CSV 행(row) 생성
        row = [file_hash]
        for kind in all_kinds:
            # 해당 kind가 발견되었으면 1, 아니면 0
            row.append(1 if kind in found_kinds else 0)
        
        # 4. CSV 행 출력
        writer.writerow(row)


if __name__ == "__main__":
    # 커맨드라인 인자로 분석할 JSON 파일 경로 받기
    if len(sys.argv) != 2:
        print(f"\n사용법: python {sys.argv[0]} <actionlint_결과_json_파일>", file=sys.stderr)
        print(f"예시: python {sys.argv[0]} actionlint_results.json", file=sys.stderr)
        sys.exit(1)

    results_json_path = Path(sys.argv[1])
    
    # 모든 가능한 'kind' 목록을 가져와서 정렬 (CSV 컬럼 순서 고정)
    all_possible_kinds = sorted(list(create_checklist_mapping().keys()))
    
    # CSV 생성 함수 실행
    create_kind_presence_csv(results_json_path, all_possible_kinds)

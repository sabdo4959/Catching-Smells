# summarize_actionlint_results.py
# actionlint_results.json 파일을 분석하여,
# 체크리스트별로 발견된 문제점의 총 개수를 요약합니다.

import json
import sys
from pathlib import Path
from collections import Counter
from pprint import pprint

def create_checklist_mapping() -> dict:
    """
    actionlint의 'kind' 필드를 사용자 정의 체크리스트 설명으로 매핑합니다.
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
        # 아래는 리스트에 없지만 actionlint가 출력할 수 있는 기타 항목들
        "syntax-check": "Syntax check for expression ${{ }}",
    }

def summarize_results(results_file: Path, checklist_map: dict):
    """
    결과 파일을 읽고 체크리스트별로 문제점 개수를 요약합니다.
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

    # Counter 객체를 사용하여 종류별 개수를 효율적으로 집계
    kind_counter = Counter()

    for file_path, issues in data.items():
        # BUG FIX: JSON 데이터의 값이 [[...]] 처럼 이중 리스트로 감싸진 경우를 처리합니다.
        actual_issues = issues
        if isinstance(issues, list) and len(issues) > 0 and isinstance(issues[0], list):
            actual_issues = issues[0]

        if not isinstance(actual_issues, list):
            continue

        for issue in actual_issues:
            # 각 issue가 딕셔너리 형태인지 한 번 더 확인하여 안정성 확보
            if isinstance(issue, dict):
                kind = issue.get("kind")
                if kind:
                    kind_counter[kind] += 1

    print("\n" + "="*70)
    print("📊 actionlint 체크리스트별 발견된 문제점 개수 요약")
    print("="*70)
    
    # Counter 결과를 체크리스트 설명으로 변환하여 출력
    summary_table = {}
    for kind, count in kind_counter.items():
        description = checklist_map.get(kind, f"기타 ({kind})")
        summary_table[description] = summary_table.get(description, 0) + count
        
    # 발견된 개수 순으로 정렬하여 출력
    sorted_summary = sorted(summary_table.items(), key=lambda item: item[1], reverse=True)

    if not sorted_summary:
        print("🎉 발견된 문제점이 없습니다!")
    else:
        print(f"{'체크리스트 항목':<55} {'발견된 개수'}")
        print("-" * 70)
        total_issues = 0
        for description, count in sorted_summary:
            print(f"{description:<55} {count}")
            total_issues += count
        print("-" * 70)
        print(f"{'총합':<55} {total_issues}")
    
    print("="*70)


if __name__ == "__main__":
    # 1. 커맨드라인 인자로 분석할 JSON 파일 경로 받기
    if len(sys.argv) != 2:
        print(f"\n사용법: python {sys.argv[0]} <actionlint_결과_json_파일>", file=sys.stderr)
        print(f"예시: python {sys.argv[0]} actionlint_results.json", file=sys.stderr)
        sys.exit(1)

    results_json_path = Path(sys.argv[1])
    checklist_mapping = create_checklist_mapping()
    
    # 2. 요약 함수 실행
    summarize_results(results_json_path, checklist_mapping)
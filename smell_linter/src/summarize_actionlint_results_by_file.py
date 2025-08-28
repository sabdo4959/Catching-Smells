# compare_lint_results.py
# '수정 전'과 '수정 후'의 actionlint 결과를 파일별로 비교하여,
# 수정된 이슈, 새로 생긴 이슈, 남아있는 이슈를 분석합니다.

import json
import sys
from pathlib import Path
from pprint import pprint

def compare_actionlint_results(invalid_file: Path, valid_file: Path, output_file: Path):
    """
    두 actionlint 결과 JSON 파일을 비교하여 상세 분석 결과를 생성합니다.
    """
    try:
        with open(invalid_file, 'r', encoding='utf-8') as f:
            invalid_data = json.load(f)
        with open(valid_file, 'r', encoding='utf-8') as f:
            valid_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: 파일을 읽거나 파싱하는 중 오류 발생: {e}", file=sys.stderr)
        return

    comparison_results = {}
    
    # 두 결과에 모두 존재하는 파일 경로들을 찾습니다.
    common_files = set(invalid_data.keys()) & set(valid_data.keys())
    print(f"총 {len(common_files)}개의 공통 파일을 비교합니다...")

    for file_path in common_files:
        # 비교를 용이하게 하기 위해 각 이슈를 고유한 튜플로 변환합니다.
        # (kind, line, message) - snippet은 내용이 길 수 있어 제외
        def create_issue_signature(issue):
            return (issue.get('kind'), issue.get('line'), issue.get('message'))

        # 중첩된 리스트 구조를 처리하는 로직 추가
        issues_before_raw = invalid_data.get(file_path, [])
        if issues_before_raw and isinstance(issues_before_raw[0], list):
            issues_before_raw = issues_before_raw[0]

        issues_after_raw = valid_data.get(file_path, [])
        if issues_after_raw and isinstance(issues_after_raw[0], list):
            issues_after_raw = issues_after_raw[0]
            
        before_set = {create_issue_signature(i) for i in issues_before_raw if isinstance(i, dict)}
        after_set = {create_issue_signature(i) for i in issues_after_raw if isinstance(i, dict)}

        fixed_issues = before_set - after_set
        new_issues = after_set - before_set
        persistent_issues = before_set & after_set

        # 분석 결과가 있는 파일만 저장
        if fixed_issues or new_issues or persistent_issues:
            comparison_results[file_path] = {
                'fixed_issues': [list(i) for i in fixed_issues],
                'new_issues': [list(i) for i in new_issues],
                'persistent_issues': [list(i) for i in persistent_issues],
                'summary': {
                    'fixed_count': len(fixed_issues),
                    'new_count': len(new_issues),
                    'persistent_count': len(persistent_issues),
                }
            }
            
    # 최종 결과를 JSON 파일로 저장
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 파일별 비교 분석이 완료되었습니다. 결과가 '{output_file}' 파일에 저장되었습니다.")
    except Exception as e:
        print(f"ERROR: 비교 결과를 파일에 저장하는 중 오류 발생: {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"\n사용법: python {sys.argv[0]} <invalid_json_경로> <valid_json_경로> <결과_저장_경로>", file=sys.stderr)
        print(f"예시: python {sys.argv[0]} actionlint_invalid.json actionlint_valid.json comparison_results.json", file=sys.stderr)
        sys.exit(1)

    invalid_json_path = Path(sys.argv[1])
    valid_json_path = Path(sys.argv[2])
    output_json_path = Path(sys.argv[3])

    compare_actionlint_results(invalid_json_path, valid_json_path, output_json_path)

    # 저장된 파일의 샘플 데이터 출력
    print("\n--- 저장된 결과 (샘플) ---")
    try:
        with open(output_json_path, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
            pprint(dict(list(sample_data.items())[:2]))
    except Exception as e:
        print(f"샘플 출력 실패: {e}")
    print("--------------------------")

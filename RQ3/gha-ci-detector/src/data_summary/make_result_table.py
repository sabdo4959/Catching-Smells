import pandas as pd
import re
import argparse
import os

def extract_path_info(yaml_path: str) -> tuple:
    """
    YAML 파일 경로에서 조직, 저장소, 파일 이름을 추출합니다.
    
    Args:
        yaml_path (str): YAML 파일 경로
    
    Returns:
        tuple: (조직명, 저장소명, YAML 파일명)
    """
    # 여러 가지 경로 패턴을 시도합니다
    patterns = [
        r'\./\.github/workflows/(.+?)_(.+?)__(.+)',  # 기존 패턴
        r'(?:.*/)?([^/]+)/([^/]+)/\.github/workflows/(.+)',  # GitHub 표준 경로
        r'(?:.*/)?([^/]+)_([^/]+)__(.+)',  # 대체 형식
        r'([^/]+)/([^/]+)/(.+\.ya?ml)$'  # 단순 조직/저장소/파일 패턴
    ]
    
    for pattern in patterns:
        match = re.match(pattern, yaml_path)
        if match:
            return match.groups()
    
    # 패턴이 매치되지 않으면 경로를 분리하여 처리
    parts = yaml_path.split('/')
    if len(parts) >= 3:
        return parts[-3], parts[-2], parts[-1]
    else:
        return "unknown", "unknown", yaml_path.strip()

def process_log_file(log_file_path: str, output_path: str = "result_table.csv"):
    """
    로그 파일을 처리하여 결과 테이블을 생성합니다.
    
    Args:
        log_file_path (str): 로그 파일 경로
        output_path (str): 결과 CSV 파일 저장 경로
    """
    # 입력 파일 존재 여부 확인
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {log_file_path}")

    with open(log_file_path, encoding="utf-8") as f:
        log_content = f.read()

    # 데이터프레임 구조 생성
    columns = ['Org', 'Repo', 'Yaml'] + [f'Smell {i}' for i in range(1, 24)]
    data = []

    # 로그를 "Detecting smells for " 기준으로 분리하여 각 워크플로우별로 처리
    log_blocks = log_content.split('Detecting smells for ')[1:]

    for block in log_blocks:
        lines = block.splitlines()
        if not lines:
            continue

        # 워크플로우 경로 추출
        yaml_path = lines[0].strip()
        org, repo, yaml_file = extract_path_info(yaml_path)

        # 스멜 플래그 초기화
        smell_flags = {f'Smell {i}': '' for i in range(1, 24)}
        
        # 해당 블록에서 발견된 모든 스멜 번호를 저장할 집합(set)
        found_smells = set()

        # 1. 명시적으로 나열된 스멜 번호 추출
        # 예: "- 2. Use commit hash..." 또는 "- 23. Avoid incorrectly..."
        listed_smells = re.findall(r'^\s*-\s*(\d+)\.', block, re.MULTILINE)
        for smell_num in listed_smells:
            found_smells.add(smell_num)

        # 2. "YAML parsing error"가 있으면 23번 스멜로 간주
        if 'YAML parsing error' in block:
            found_smells.add('23')

        # 집합에 저장된 스멜 번호들을 기반으로 플래그 설정
        for smell_num in found_smells:
            smell_id = f'Smell {smell_num}'
            if smell_id in smell_flags:
                smell_flags[smell_id] = 'Tool'

        row = [org, repo, yaml_file] + [smell_flags[f'Smell {i}'] for i in range(1, 24)]
        data.append(row)

    df = pd.DataFrame(data, columns=columns)
    df.to_csv(output_path, index=False)
    print(f"결과가 다음 파일에 저장되었습니다: {output_path}")
    return df

def main():
    parser = argparse.ArgumentParser(description='GitHub Actions 워크플로우 스멜 분석 결과를 요약합니다.')
    parser.add_argument('log_file', help='분석할 로그 파일 경로')
    parser.add_argument('--output', '-o', 
                       default="result_table.csv",
                       help='결과를 저장할 CSV 파일 경로 (기본값: result_table.csv)')

    args = parser.parse_args()

    try:
        process_log_file(args.log_file, args.output)
    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    main()

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
        return "unknown", "unknown", yaml_path

"""
python make_result_table.py path/to/your/logfile.log
python make_result_table.py path/to/your/logfile.log -o custom_output.csv
"""


def process_log_file(log_file_path: str, output_path: str = "result_table.csv"):
    """
    Process the log file and create a result table
    
    Args:
        log_file_path (str): Path to the log file
        output_path (str): Path where the result CSV should be saved
    """
    # Check if input file exists
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file not found: {log_file_path}")

    # Log file content
    with open(log_file_path, encoding="utf-8") as f:
        log_content = f.read()

    # Extract data
    pattern = re.compile(r'Detecting smells for (.+)\nWe have found (\d+) smells((?:\n\t-.+)+)', re.MULTILINE)
    matches = pattern.findall(log_content)

    # Smell IDs and Descriptions
    smell_ids = {str(i): f'Smell {i}' for i in range(1, 23)}

    # Create dataframe structure
    columns = ['Org', 'Repo', 'Yaml'] + [f'Smell {i}' for i in range(1, 23)]
    data = []

    for match in matches:
        yaml_path, smell_count, smells_block = match
        # 새로운 extract_path_info 함수 사용
        org, repo, yaml_file = extract_path_info(yaml_path)
        
        smell_flags = {f'Smell {i}': '' for i in range(1, 23)}
        smells = re.findall(r'- (\d+)\.', smells_block)
        
        for smell in smells:
            smell_id = f'Smell {smell}'
            smell_flags[smell_id] = 'Tool'

        row = [org, repo, yaml_file] + [smell_flags[f'Smell {i}'] for i in range(1, 23)]
        data.append(row)

    df = pd.DataFrame(data, columns=columns)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Results have been saved to: {output_path}")
    return df

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process GitHub Actions workflow analysis log file')
    parser.add_argument('log_file', help='Path to the log file to process')
    parser.add_argument('--output', '-o', 
                       default="result_table.csv",
                       help='Path where to save the result CSV file (default: result_table.csv)')

    args = parser.parse_args()

    try:
        df = process_log_file(args.log_file, args.output)
        print("\nSample of processed data:")
        print(df.head())
    except Exception as e:
        print(f"Error processing file: {e}")
        exit(1)

if __name__ == "__main__":
    main()

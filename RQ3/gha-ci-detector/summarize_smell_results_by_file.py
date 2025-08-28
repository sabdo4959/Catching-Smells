import pandas as pd
from collections import defaultdict
import argparse
import os

def summarize_smells(csv_file: str):
    """
    CSV 파일에서 각 스멜별 발견 횟수를 분석하고 요약합니다.
    
    Args:
        csv_file (str): 분석할 CSV 파일 경로
    """
    # CSV 파일 존재 확인
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {csv_file}")

    # CSV 파일 읽기
    df = pd.read_csv(csv_file)
    
    # 스멜 컬럼들만 선택 (Smell 1 ~ Smell 22)
    smell_columns = [f'Smell {i}' for i in range(1, 23)]
    
    # 각 스멜별 발견 횟수 계산
    smell_counts = {}
    total_workflows = len(df)
    
    for smell in smell_columns:
        count = len(df[df[smell] == 'Tool'])
        smell_counts[smell] = count
    
    # 결과 출력
    print("\n=== 스멜 발견 분석 결과 ===")
    print(f"분석한 파일: {csv_file}")
    print(f"전체 워크플로우 수: {total_workflows}")
    print("\n각 스멜별 발견 횟수:")
    print("-" * 40)
    
    # 스멜을 발견 횟수 기준으로 내림차순 정렬하여 출력
    sorted_smells = sorted(smell_counts.items(), key=lambda x: x[1], reverse=True)
    
    for smell, count in sorted_smells:
        percentage = (count / total_workflows) * 100
        # 막대 그래프 문자로 표현 (최대 50칸)
        bar = '█' * int((count / max(smell_counts.values()) * 50))
        print(f"{smell:8} : {count:3} 회 발견 ({percentage:5.1f}%) {bar}")

def main():
    parser = argparse.ArgumentParser(description='GitHub Actions 워크플로우 스멜 분석 결과를 요약합니다.')
    parser.add_argument('csv_file', help='분석할 CSV 파일 경로')

    args = parser.parse_args()

    try:
        summarize_smells(args.csv_file)
    except Exception as e:
        print(f"오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    main()
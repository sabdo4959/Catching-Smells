import pandas as pd
import argparse
import sys

def summarize_csv_with_style(file_path: str):
    """
    주어진 CSV 파일에서 각 오류 유형의 발생 횟수를 요약하고,
    지정된 스타일로 시각화하여 출력합니다.
    """
    try:
        # CSV 파일을 읽어옵니다.
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"오류: 파일을 읽는 중 문제가 발생했습니다: {e}")
        sys.exit(1)

    # 'file_hash' 컬럼을 제외한 나머지 컬럼들이 요약 대상입니다.
    if 'file_hash' not in df.columns:
        print(f"오류: 필수 컬럼인 'file_hash'를 파일에서 찾을 수 없습니다: {file_path}")
        sys.exit(1)
        
    summary_columns = [col for col in df.columns if col != 'file_hash']

    # 각 컬럼의 합계를 계산합니다. (값이 0 또는 1이므로, 합계가 곧 발생 횟수입니다.)
    summary = df[summary_columns].sum()

    # 0보다 큰 (즉, 한 번이라도 발생한) 오류만 필터링합니다.
    summary = summary[summary > 0]

    # 결과를 발생 횟수 기준으로 내림차순 정렬합니다.
    summary = summary.sort_values(ascending=False)
    
    total_rows = len(df)

    # --- 결과 출력 ---
    print("\n=== actionlint 발견 분석 결과 ===")
    print(f"분석한 파일: {file_path}")
    print(f"전체 워크플로우 수: {total_rows}")
    print("\n각 오류 유형별 발견 횟수:")
    print("-" * 40)

    if summary.empty:
        print("발견된 오류가 없습니다.")
        return

    # 막대 그래프의 최대 길이를 계산하기 위해 가장 큰 카운트 값을 가져옵니다.
    max_count = summary.max()
    
    for kind, count in summary.items():
        # 전체 대비 비율 계산
        percentage = (count / total_rows) * 100 if total_rows > 0 else 0
        
        # 막대 그래프 문자열 생성 (최대 50칸)
        bar_length = int((count / max_count * 50)) if max_count > 0 else 0
        bar = '█' * bar_length
        
        # 정해진 형식에 맞춰 출력
        # f-string을 사용하여 정렬과 포맷팅을 깔끔하게 처리합니다.
        # {kind:<20} : 20칸을 차지하며 왼쪽 정렬
        # {count:5}    : 5칸을 차지하며 오른쪽 정렬
        # {percentage:5.1f} : 5칸 차지, 소수점 첫째 자리까지 표시
        print(f"{kind:<20} : {count:5} 회 발견 ({percentage:5.1f}%) {bar}")


if __name__ == "__main__":
    # 커맨드 라인에서 파일 경로를 인자로 받도록 설정
    parser = argparse.ArgumentParser(description="Summarize the result table with a visual style.")
    parser.add_argument("csv_file", help="Path to the input CSV file.")
    
    args = parser.parse_args()
    
    summarize_csv_with_style(args.csv_file)
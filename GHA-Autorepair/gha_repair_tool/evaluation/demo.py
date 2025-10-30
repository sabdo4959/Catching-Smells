#!/usr/bin/env python3
"""
베이스라인 평가 시스템 사용 예제

실제 워크플로우 파일들에 대해 베이스라인 복구와 평가를 수행하는 예제입니다.
"""

import logging
import sys
import os
from pathlib import Path

# 로컬 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.batch_evaluator import BaselineBatchProcessor


def demo_single_file():
    """단일 파일 처리 데모"""
    print("🚀 단일 파일 베이스라인 처리 데모")
    print("=" * 50)
    
    # 예제 파일 (실제 경로로 변경 필요)
    input_file = "/Users/nam/workflows/3dc192b8f93f3ff1e0a922558a1a71f041ca95396e9f2f06a218f6ca70f3af8b"
    
    if not Path(input_file).exists():
        print(f"❌ 입력 파일이 없습니다: {input_file}")
        print("실제 워크플로우 파일 경로로 변경해주세요.")
        return False
    
    try:
        processor = BaselineBatchProcessor("./demo_results")
        summary = processor.process_file_list([input_file], max_files=1)
        
        print(f"✅ 처리 완료!")
        print(f"   성공률: {summary['success_rate']:.1f}%")
        print(f"   처리 시간: {summary['processing_time']:.1f}초")
        
        if summary.get('evaluation_summary'):
            eval_summary = summary['evaluation_summary']
            print(f"   구문 성공률: {eval_summary.get('syntax_success_rate', 0):.1f}%")
            print(f"   평균 스멜 제거율: {eval_summary.get('avg_smell_removal_rate', 0):.1f}%")
            print(f"   평균 Edit Distance: {eval_summary.get('avg_edit_distance', 0):.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 처리 중 오류: {e}")
        return False


def demo_directory_batch():
    """디렉토리 배치 처리 데모"""
    print("\n🚀 디렉토리 배치 처리 데모")
    print("=" * 50)
    
    # 예제 디렉토리 (실제 경로로 변경 필요)
    input_dir = "/Users/nam/workflows"
    
    if not Path(input_dir).exists():
        print(f"❌ 입력 디렉토리가 없습니다: {input_dir}")
        print("실제 워크플로우 디렉토리 경로로 변경해주세요.")
        return False
    
    try:
        processor = BaselineBatchProcessor("./demo_batch_results")
        summary = processor.process_from_directory(
            input_dir, 
            pattern="*",  # 모든 파일 (확장자 상관없이)
            max_files=5   # 최대 5개 파일만 테스트
        )
        
        print(f"✅ 배치 처리 완료!")
        print(f"   총 파일: {summary['total_files']}")
        print(f"   성공: {summary['successful_repairs']}")
        print(f"   실패: {summary['failed_repairs']}")
        print(f"   성공률: {summary['success_rate']:.1f}%")
        print(f"   처리 시간: {summary['processing_time']:.1f}초")
        
        if summary.get('evaluation_summary'):
            eval_summary = summary['evaluation_summary']
            print(f"\n📊 평가 결과:")
            print(f"   구문 성공률: {eval_summary.get('syntax_success_rate', 0):.1f}%")
            print(f"   평균 스멜 제거율: {eval_summary.get('avg_smell_removal_rate', 0):.1f}%")
            print(f"   평균 Edit Distance: {eval_summary.get('avg_edit_distance', 0):.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 배치 처리 중 오류: {e}")
        return False


def show_usage_examples():
    """사용법 예제 출력"""
    print("\n📚 베이스라인 평가 시스템 사용법")
    print("=" * 50)
    
    print("1. 단일 파일 평가:")
    print("   python evaluation/evaluator.py --original input.yml --repaired output.yml")
    print()
    
    print("2. 여러 파일 배치 처리:")
    print("   python evaluation/batch_evaluator.py --files file1.yml file2.yml file3.yml")
    print()
    
    print("3. 디렉토리 전체 처리:")
    print("   python evaluation/batch_evaluator.py --directory /path/to/workflows --pattern '*.yml'")
    print()
    
    print("4. CSV 파일에서 파일 목록 읽기:")
    print("   python evaluation/batch_evaluator.py --csv file_list.csv --column file_path")
    print()
    
    print("📊 평가 지표:")
    print("   • 구문 성공률: actionlint 통과 비율")
    print("   • 타겟 스멸 제거율: 목표 스멀(1,4,5,10,11,15,16번) 제거 비율") 
    print("   • 수정 범위 적절성: Edit Distance (낮을수록 정밀)")
    print()
    
    print("💾 출력 파일:")
    print("   • JSON: 전체 평가 결과 및 메타데이터")
    print("   • CSV: 파일별 상세 평가 결과")
    print("   • 수정된 YAML: 베이스라인으로 복구된 워크플로우")


def main():
    """메인 데모 함수"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 베이스라인 평가 시스템 데모")
    print("=" * 60)
    
    # 사용법 먼저 표시
    show_usage_examples()
    
    # 데모 실행 (실제 파일이 있을 때만)
    try:
        # 주석 해제하여 실제 파일로 테스트
        # demo_single_file()
        # demo_directory_batch()
        
        print("\n💡 실제 테스트를 위해서는:")
        print("   1. demo_single_file() 함수의 input_file 경로를 실제 파일로 변경")
        print("   2. demo_directory_batch() 함수의 input_dir 경로를 실제 디렉토리로 변경")
        print("   3. 해당 함수 호출 주석 해제")
        
    except Exception as e:
        print(f"❌ 데모 실행 중 오류: {e}")
        return False
    
    return True


if __name__ == "__main__":
    main()

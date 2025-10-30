#!/usr/bin/env python3
"""
베이스라인 평가 시스템 테스트 스크립트

기존에 생성된 테스트 파일들을 사용하여 평가 시스템을 테스트합니다.
"""

import logging
import sys
import os
from pathlib import Path

# 로컬 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluator import BaselineEvaluator


def test_single_evaluation():
    """단일 파일 평가 테스트"""
    print("🧪 단일 파일 평가 테스트")
    print("=" * 40)
    
    # 테스트 파일 경로
    test_dir = Path(__file__).parent.parent
    original_file = test_dir / "test_smell_detection.yml"
    repaired_file = test_dir / "test_baseline_output.yml"
    
    if not original_file.exists():
        print(f"❌ 원본 파일이 없습니다: {original_file}")
        return False
    
    if not repaired_file.exists():
        print(f"❌ 수정된 파일이 없습니다: {repaired_file}")
        return False
    
    # 평가 실행
    evaluator = BaselineEvaluator("./test_evaluation_results")
    
    try:
        # 단일 파일 평가
        result = evaluator.evaluate_file(str(original_file), str(repaired_file))
        
        print(f"✅ 단일 파일 평가 완료:")
        print(f"   원본: {result.original_file}")
        print(f"   수정본: {result.repaired_file}")
        print(f"   구문 성공: {result.syntax_success}")
        print(f"   스멜 변화: {result.initial_smells_count} -> {result.final_smells_count}")
        print(f"   스멜 제거율: {result.smell_removal_rate:.1f}%")
        print(f"   Edit Distance: {result.edit_distance}")
        print(f"   처리 시간: {result.processing_time:.3f}초")
        
        if result.error_message:
            print(f"   오류: {result.error_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ 평가 중 오류: {e}")
        return False


def test_group_evaluation():
    """그룹 평가 테스트"""
    print("\n🧪 그룹 평가 테스트")
    print("=" * 40)
    
    # 테스트 파일들 찾기
    test_dir = Path(__file__).parent.parent
    test_files = [
        ("test_smell_detection.yml", "test_baseline_output.yml"),
        ("test_smell_detection2.yml", "test_output2.yml"),
        ("test_smell_detection_final.yml", "test_output3.yml")
    ]
    
    file_pairs = []
    for original, repaired in test_files:
        original_path = test_dir / original
        repaired_path = test_dir / repaired
        
        if original_path.exists() and repaired_path.exists():
            file_pairs.append((str(original_path), str(repaired_path)))
            print(f"✅ 파일 쌍 추가: {original} -> {repaired}")
        else:
            print(f"⚠️ 파일 쌍 누락: {original} -> {repaired}")
    
    if not file_pairs:
        print("❌ 테스트할 파일 쌍이 없습니다.")
        return False
    
    # 그룹 평가 실행
    evaluator = BaselineEvaluator("./test_evaluation_results")
    
    try:
        summary = evaluator.evaluate_group(file_pairs, "test_baseline")
        
        # 결과 출력
        evaluator.print_summary(summary)
        
        # 결과 저장
        json_file, csv_file = evaluator.save_results(summary)
        print(f"\n💾 결과 저장:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 그룹 평가 중 오류: {e}")
        return False


def test_metrics_calculation():
    """평가 지표 계산 로직 테스트"""
    print("\n🧪 평가 지표 계산 테스트")
    print("=" * 40)
    
    evaluator = BaselineEvaluator("./test_evaluation_results")
    
    # 1. Target Smell Counting 테스트
    test_smells = [
        {"message": "- 10. Avoid jobs without timeouts (line: 6)"},
        {"message": "- 3. Use fixed version for runs-on argument (line 7)"},
        {"message": "- 15. Some other smell"},
        {"message": "- 8. Use commit hash instead of tags"}
    ]
    
    target_count = evaluator._count_target_smells(test_smells)
    print(f"Target Smell Count 테스트:")
    print(f"   입력: {len(test_smells)}개 스멜")
    print(f"   타겟 스멜: {target_count}개 (예상: 2개 - #10, #15)")
    
    # 2. Edit Distance 계산 테스트
    test_dir = Path(__file__).parent.parent
    original_file = test_dir / "test_smell_detection.yml"
    repaired_file = test_dir / "test_baseline_output.yml"
    
    if original_file.exists() and repaired_file.exists():
        edit_distance = evaluator._calculate_edit_distance(str(original_file), str(repaired_file))
        print(f"Edit Distance 테스트:")
        print(f"   원본: {original_file.name}")
        print(f"   수정본: {repaired_file.name}")
        print(f"   Edit Distance: {edit_distance}")
    else:
        print("⚠️ Edit Distance 테스트용 파일이 없습니다.")
    
    return True


def main():
    """메인 테스트 함수"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 베이스라인 평가 시스템 테스트 시작")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # 테스트 실행
    if test_single_evaluation():
        success_count += 1
    
    if test_group_evaluation():
        success_count += 1
    
    if test_metrics_calculation():
        success_count += 1
    
    # 결과 요약
    print(f"\n🎯 테스트 결과: {success_count}/{total_tests} 성공")
    if success_count == total_tests:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    
    return success_count == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

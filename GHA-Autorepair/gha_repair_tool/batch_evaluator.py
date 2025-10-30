#!/usr/bin/env python3
"""
배치 평가 스크립트

data_original과 data_repair_baseline 디렉토리의 모든 파일을 비교하여
3가지 평가 지표를 계산합니다.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import statistics

# 로컬 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from evaluation.evaluator import BaselineEvaluator


def find_matching_files(original_dir: Path, repaired_dir: Path) -> List[tuple]:
    """
    원본과 복구된 파일들의 매칭 쌍을 찾습니다.
    
    Returns:
        List[tuple]: (원본파일경로, 복구파일경로) 튜플 리스트
    """
    matches = []
    
    for original_file in original_dir.glob("*"):
        if not original_file.is_file():
            continue
            
        # 복구된 파일명 패턴: {원본명}_baseline_repaired.yml
        repaired_name = f"{original_file.name}_baseline_repaired.yml"
        repaired_file = repaired_dir / repaired_name
        
        if repaired_file.exists():
            matches.append((str(original_file), str(repaired_file)))
    
    return matches


def batch_evaluate(original_dir: str, repaired_dir: str, output_dir: str) -> Dict:
    """
    배치 평가를 실행합니다.
    """
    logger = logging.getLogger(__name__)
    
    # 디렉토리 경로 설정
    original_path = Path(original_dir)
    repaired_path = Path(repaired_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 매칭 파일 찾기
    file_pairs = find_matching_files(original_path, repaired_path)
    logger.info(f"매칭된 파일 쌍: {len(file_pairs)}개")
    
    if not file_pairs:
        logger.error("매칭된 파일이 없습니다.")
        return {}
    
    # 평가 시스템 초기화
    evaluator = BaselineEvaluator()
    
    # 결과 저장용
    results = []
    syntax_successes = []
    smell_removal_rates = []
    edit_distances = []
    
    # 각 파일 쌍 평가
    for i, (original_file, repaired_file) in enumerate(file_pairs, 1):
        logger.info(f"[{i}/{len(file_pairs)}] 평가 중: {Path(original_file).name}")
        
        try:
            # 평가 실행
            result = evaluator.evaluate_file(original_file, repaired_file)
            results.append(result)
            
            # 지표 수집
            syntax_successes.append(1 if result.syntax_success else 0)
            smell_removal_rates.append(result.smell_removal_rate)
            edit_distances.append(result.edit_distance)
            
            logger.info(f"  구문 성공: {result.syntax_success}")
            logger.info(f"  스멜 제거율: {result.smell_removal_rate:.1f}%")
            logger.info(f"  편집 거리: {result.edit_distance}")
            
        except Exception as e:
            logger.error(f"평가 실패 ({Path(original_file).name}): {e}")
    
    # 전체 통계 계산
    total_files = len(results)
    syntax_success_rate = (sum(syntax_successes) / total_files * 100) if total_files > 0 else 0
    avg_smell_removal_rate = statistics.mean(smell_removal_rates) if smell_removal_rates else 0
    avg_edit_distance = statistics.mean(edit_distances) if edit_distances else 0
    
    # 결과 요약
    summary = {
        "evaluation_date": datetime.now().isoformat(),
        "total_files": total_files,
        "original_directory": str(original_path),
        "repaired_directory": str(repaired_path),
        
        # 주요 지표
        "syntax_success_rate": round(syntax_success_rate, 2),
        "average_smell_removal_rate": round(avg_smell_removal_rate, 2),
        "average_edit_distance": round(avg_edit_distance, 2),
        
        # 상세 통계
        "syntax_successes": sum(syntax_successes),
        "syntax_failures": total_files - sum(syntax_successes),
        "smell_removal_stats": {
            "min": min(smell_removal_rates) if smell_removal_rates else 0,
            "max": max(smell_removal_rates) if smell_removal_rates else 0,
            "median": statistics.median(smell_removal_rates) if smell_removal_rates else 0,
            "stdev": statistics.stdev(smell_removal_rates) if len(smell_removal_rates) > 1 else 0
        },
        "edit_distance_stats": {
            "min": min(edit_distances) if edit_distances else 0,
            "max": max(edit_distances) if edit_distances else 0,
            "median": statistics.median(edit_distances) if edit_distances else 0,
            "stdev": statistics.stdev(edit_distances) if len(edit_distances) > 1 else 0
        }
    }
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 요약 결과 JSON
    summary_file = output_path / f"evaluation_summary_{timestamp}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # 2. 상세 결과 JSON
    detailed_file = output_path / f"evaluation_detailed_{timestamp}.json"
    detailed_results = [result.__dict__ for result in results]
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    # 결과 출력
    logger.info("=" * 60)
    logger.info("배치 평가 완료!")
    logger.info(f"총 파일: {total_files}")
    logger.info(f"구문 성공률: {syntax_success_rate:.2f}% ({sum(syntax_successes)}/{total_files})")
    logger.info(f"평균 스멀 제거율: {avg_smell_removal_rate:.2f}%")
    logger.info(f"평균 편집 거리: {avg_edit_distance:.2f}")
    logger.info(f"요약 결과: {summary_file}")
    logger.info(f"상세 결과: {detailed_file}")
    logger.info("=" * 60)
    
    return summary


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="배치 평가 도구")
    parser.add_argument("--original-dir", required=True, help="원본 디렉토리")
    parser.add_argument("--repaired-dir", required=True, help="복구된 디렉토리")
    parser.add_argument("--output-dir", default="./evaluation_results", help="출력 디렉토리")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    try:
        summary = batch_evaluate(args.original_dir, args.repaired_dir, args.output_dir)
        
        print(f"\n🎉 배치 평가 완료!")
        print(f"총 파일: {summary.get('total_files', 0)}")
        print(f"구문 성공률: {summary.get('syntax_success_rate', 0):.2f}%")
        print(f"평균 스멸 제거율: {summary.get('average_smell_removal_rate', 0):.2f}%")
        print(f"평균 편집 거리: {summary.get('average_edit_distance', 0):.2f}")
        
        return True
        
    except Exception as e:
        logging.error(f"배치 평가 중 오류 발생: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

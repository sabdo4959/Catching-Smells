#!/usr/bin/env python3
"""
베이스라인 배치 평가 스크립트

이미 복구된 베이스라인 파일들을 평가합니다.
"""

import logging
import argparse
import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict
import time
import json
from datetime import datetime

# 로컬 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluator import BaselineEvaluator


class BaselineBatchEvaluator:
    """베이스라인 배치 평가 클래스"""
    
    def __init__(self, output_dir: str = "./evaluation_results/baseline"):
        """
        Args:
            output_dir: 결과를 저장할 디렉토리
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.evaluator = BaselineEvaluator(str(self.output_dir))
    
    def evaluate_baseline_files(self, original_dir: str, repaired_dir: str, 
                               max_files: int = None) -> Dict[str, any]:
        """
        베이스라인 복구된 파일들을 평가합니다.
        
        Args:
            original_dir: 원본 파일 디렉토리
            repaired_dir: 베이스라인 복구된 파일 디렉토리
            max_files: 평가할 최대 파일 수
            
        Returns:
            Dict: 평가 결과 요약
        """
        original_path = Path(original_dir)
        repaired_path = Path(repaired_dir)
        
        if not original_path.exists():
            raise FileNotFoundError(f"원본 디렉토리가 없습니다: {original_dir}")
        if not repaired_path.exists():
            raise FileNotFoundError(f"복구된 디렉토리가 없습니다: {repaired_dir}")
        
        # 원본 파일 목록 가져오기
        original_files = list(original_path.glob("*"))
        original_files = [f for f in original_files if f.is_file()]
        
        if max_files:
            original_files = original_files[:max_files]
        
        self.logger.info(f"평가 시작: {len(original_files)}개 원본 파일")
        
        # 파일 쌍 매칭
        file_pairs = []
        missing_files = []
        
        for original_file in original_files:
            # 베이스라인 복구 파일명 패턴: {파일명}_baseline_repaired.yml
            repaired_file = repaired_path / f"{original_file.name}_baseline_repaired.yml"
            
            if repaired_file.exists():
                file_pairs.append((str(original_file), str(repaired_file)))
                self.logger.debug(f"파일 쌍 매칭: {original_file.name} -> {repaired_file.name}")
            else:
                missing_files.append(str(original_file))
                self.logger.warning(f"복구 파일 없음: {repaired_file}")
        
        if not file_pairs:
            raise ValueError(f"매칭되는 파일 쌍이 없습니다: {original_dir} <-> {repaired_dir}")
        
        self.logger.info(f"매칭된 파일 쌍: {len(file_pairs)}개")
        if missing_files:
            self.logger.warning(f"누락된 파일: {len(missing_files)}개")
        
        # 평가 실행
        start_time = datetime.now()
        evaluation_summary = self.evaluator.evaluate_group(
            file_pairs, 
            group_name="llama3.1_8b_baseline"
        )
        evaluation_time = (datetime.now() - start_time).total_seconds()
        
        # 결과 저장
        json_file, csv_file = self.evaluator.save_results(evaluation_summary)
        
        # 요약 출력
        self.evaluator.print_summary(evaluation_summary)
        
        # 상세 결과 반환
        result = {
            'evaluation_summary': evaluation_summary.__dict__,
            'evaluation_time': evaluation_time,
            'total_original_files': len(original_files),
            'matched_file_pairs': len(file_pairs),
            'missing_files': missing_files,
            'success_rate': (len(file_pairs) / len(original_files)) * 100.0 if original_files else 0.0,
            'json_report': str(json_file),
            'csv_report': str(csv_file),
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"평가 완료: {evaluation_time:.1f}초")
        self.logger.info(f"파일 매칭률: {result['success_rate']:.1f}% ({len(file_pairs)}/{len(original_files)})")
        
        return result


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="베이스라인 배치 평가 도구")
    
    parser.add_argument("--original-dir", required=True, help="원본 파일 디렉토리")
    parser.add_argument("--repaired-dir", required=True, help="베이스라인 복구된 파일 디렉토리")
    parser.add_argument("--max-files", type=int, help="평가할 최대 파일 수")
    parser.add_argument("--output-dir", default="./evaluation_results/llama3.1_8b_baseline", help="출력 디렉토리")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        evaluator = BaselineBatchEvaluator(args.output_dir)
        
        result = evaluator.evaluate_baseline_files(
            original_dir=args.original_dir,
            repaired_dir=args.repaired_dir,
            max_files=args.max_files
        )
        
        eval_summary = result['evaluation_summary']
        
        print(f"\n🎉 베이스라인 배치 평가 완료!")
        print(f"원본 파일: {result['total_original_files']}")
        print(f"매칭된 파일 쌍: {result['matched_file_pairs']}")
        print(f"파일 매칭률: {result['success_rate']:.1f}%")
        print(f"평가 시간: {result['evaluation_time']:.1f}초")
        
        print(f"\n📊 평가 결과:")
        print(f"구문 성공률: {eval_summary.get('syntax_success_rate', 0):.1f}%")
        print(f"평균 스멜 제거율: {eval_summary.get('avg_smell_removal_rate', 0):.1f}%")
        print(f"평균 Edit Distance: {eval_summary.get('avg_edit_distance', 0):.1f}")
        
        print(f"\n📁 결과 파일:")
        print(f"JSON 보고서: {result['json_report']}")
        print(f"CSV 보고서: {result['csv_report']}")
        
        if result['missing_files']:
            print(f"\n⚠️  누락된 파일 {len(result['missing_files'])}개:")
            for missing in result['missing_files'][:5]:  # 처음 5개만 표시
                print(f"  - {Path(missing).name}")
            if len(result['missing_files']) > 5:
                print(f"  ... 및 {len(result['missing_files']) - 5}개 더")
        
    except Exception as e:
        logging.error(f"배치 평가 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

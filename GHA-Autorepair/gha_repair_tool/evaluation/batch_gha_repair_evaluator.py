#!/usr/bin/env python3
"""
GHA-Repair 배치 평가 스크립트

GHA-Repair 모드로 복구된 파일들에 대해 평가를 수행합니다.
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


class GHARepairEvaluator(BaselineEvaluator):
    """GHA-Repair 평가 클래스 (베이스라인 평가 상속)"""
    
    def __init__(self, output_dir: str = "./evaluation_results/gha_repair"):
        """
        Args:
            output_dir: 결과를 저장할 디렉토리
        """
        super().__init__(output_dir)
        self.logger = logging.getLogger(__name__)


class GHARepairBatchProcessor:
    """GHA-Repair 배치 처리 클래스"""
    
    def __init__(self, output_dir: str = "./evaluation_results/gha_repair"):
        """
        Args:
            output_dir: 결과를 저장할 디렉토리
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 평가 결과를 저장할 디렉토리
        self.evaluation_dir = self.output_dir
        
        self.evaluator = GHARepairEvaluator(str(self.evaluation_dir))
    
    def evaluate_gha_repair_files(self, original_dir: str, repaired_dir: str, 
                                 max_files: int = None) -> Dict[str, any]:
        """
        GHA-Repair 모드로 복구된 파일들을 평가합니다.
        
        Args:
            original_dir: 원본 파일 디렉토리
            repaired_dir: GHA-Repair 모드로 복구된 파일 디렉토리
            max_files: 평가할 최대 파일 수
            
        Returns:
            Dict: 평가 결과 요약
        """
        original_path = Path(original_dir)
        repaired_path = Path(repaired_dir)
        
        if not original_path.exists():
            raise FileNotFoundError(f"원본 디렉토리가 없습니다: {original_dir}")
        if not repaired_path.exists():
            raise FileNotFoundError(f"복구된 파일 디렉토리가 없습니다: {repaired_dir}")
        
        # 원본 파일들 찾기
        original_files = list(original_path.glob("*"))
        original_files = [f for f in original_files if f.is_file()]
        
        # 파일 쌍 매칭
        file_pairs = []
        for original_file in original_files:
            # GHA-Repair 복구된 파일 경로 생성
            repaired_file = repaired_path / f"{original_file.name}_gha_repaired.yml"
            
            if repaired_file.exists():
                file_pairs.append((str(original_file), str(repaired_file)))
            else:
                self.logger.warning(f"복구된 파일 없음: {repaired_file}")
        
        if not file_pairs:
            raise ValueError(f"매칭되는 파일 쌍이 없습니다: {original_dir} <-> {repaired_dir}")
        
        # 최대 파일 수 제한
        if max_files and len(file_pairs) > max_files:
            file_pairs = file_pairs[:max_files]
            self.logger.info(f"평가 파일 수를 {max_files}개로 제한")
        
        total_files = len(file_pairs)
        self.logger.info(f"GHA-Repair 평가 시작: {total_files}개 파일 쌍")
        
        start_time = datetime.now()
        
        # 평가 실행
        evaluation_summary = self.evaluator.evaluate_group(
            file_pairs, 
            group_name="gha_repair"
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 결과 저장
        summary_file, detailed_file = self.evaluator.save_results(evaluation_summary)
        self.evaluator.print_summary(evaluation_summary)
        
        # 배치 처리 결과 반환
        batch_summary = {
            'processing_time': processing_time,
            'total_files': total_files,
            'evaluation_summary': evaluation_summary.__dict__,
            'original_dir': original_dir,
            'repaired_dir': repaired_dir,
            'summary_file': summary_file,
            'detailed_file': detailed_file,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"GHA-Repair 평가 완료: {processing_time:.1f}초")
        
        return batch_summary
    
    def evaluate_file_list(self, file_pairs: List[Tuple[str, str]], 
                          group_name: str = "gha_repair_test") -> Dict[str, any]:
        """
        파일 쌍 리스트를 직접 평가합니다.
        
        Args:
            file_pairs: (원본파일, 복구파일) 쌍의 리스트
            group_name: 그룹 이름
            
        Returns:
            Dict: 평가 결과 요약
        """
        total_files = len(file_pairs)
        self.logger.info(f"GHA-Repair 파일 리스트 평가 시작: {total_files}개 파일 쌍")
        
        start_time = datetime.now()
        
        # 평가 실행
        evaluation_summary = self.evaluator.evaluate_group(file_pairs, group_name)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 결과 저장
        summary_file, detailed_file = self.evaluator.save_results(evaluation_summary)
        self.evaluator.print_summary(evaluation_summary)
        
        # 배치 처리 결과 반환
        batch_summary = {
            'processing_time': processing_time,
            'total_files': total_files,
            'evaluation_summary': evaluation_summary.__dict__,
            'file_pairs': file_pairs,
            'summary_file': summary_file,
            'detailed_file': detailed_file,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"GHA-Repair 파일 리스트 평가 완료: {processing_time:.1f}초")
        
        return batch_summary


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="GHA-Repair 배치 평가 도구")
    
    parser.add_argument("--original-dir", required=True, help="원본 파일 디렉토리")
    parser.add_argument("--repaired-dir", required=True, help="GHA-Repair 모드로 복구된 파일 디렉토리")
    parser.add_argument("--max-files", type=int, help="평가할 최대 파일 수")
    parser.add_argument("--output-dir", default="./evaluation_results/gha_repair", help="출력 디렉토리")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        processor = GHARepairBatchProcessor(args.output_dir)
        
        summary = processor.evaluate_gha_repair_files(
            args.original_dir, 
            args.repaired_dir, 
            args.max_files
        )
        
        print(f"\n🎉 GHA-Repair 평가 완료!")
        print(f"총 파일: {summary['total_files']}")
        print(f"처리 시간: {summary['processing_time']:.1f}초")
        
        if summary.get('evaluation_summary'):
            eval_summary = summary['evaluation_summary']
            print(f"\n📊 평가 결과:")
            print(f"구문 성공률: {eval_summary.get('syntax_success_rate', 0):.1f}%")
            print(f"평균 스멜 제거율: {eval_summary.get('avg_smell_removal_rate', 0):.1f}%")
            print(f"평균 Edit Distance: {eval_summary.get('avg_edit_distance', 0):.1f}")
        
    except Exception as e:
        logging.error(f"GHA-Repair 평가 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
베이스라인 배치 평가 스크립트

여러 파일에 대해 베이스라인 복구를 실행하고 평가를 수행합니다.
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

from main import run_baseline_mode
from evaluation.evaluator import BaselineEvaluator


class BaselineBatchProcessor:
    """베이스라인 배치 처리 클래스"""
    
    def __init__(self, output_dir: str = "./evaluation_results/baseline"):
        """
        Args:
            output_dir: 결과를 저장할 디렉토리
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 수정된 파일들을 저장할 디렉토리
        self.repaired_dir = self.output_dir / "repaired_files"
        self.repaired_dir.mkdir(exist_ok=True)
        
        # 평가 결과를 저장할 디렉토리 (베이스라인은 같은 레벨에)
        self.evaluation_dir = self.output_dir
        
        self.evaluator = BaselineEvaluator(str(self.evaluation_dir))
    
    def process_file_list(self, input_files: List[str], 
                         max_files: int = None) -> Dict[str, any]:
        """
        파일 리스트를 처리합니다.
        
        Args:
            input_files: 입력 파일 경로 리스트
            max_files: 처리할 최대 파일 수 (None이면 모든 파일)
            
        Returns:
            Dict: 처리 결과 요약
        """
        if max_files:
            input_files = input_files[:max_files]
        
        total_files = len(input_files)
        self.logger.info(f"배치 처리 시작: {total_files}개 파일")
        
        start_time = datetime.now()
        successful_repairs = []
        failed_repairs = []
        file_pairs = []
        
        for i, input_file in enumerate(input_files, 1):
            self.logger.info(f"[{i}/{total_files}] 처리 중: {input_file}")
            
            try:
                # 수정된 파일 경로 생성
                input_path = Path(input_file)
                repaired_file = self.repaired_dir / f"{input_path.stem}_baseline_repaired.yml"
                
                # 베이스라인 복구 실행
                success = run_baseline_mode(input_file, str(repaired_file))
                
                if success and repaired_file.exists():
                    successful_repairs.append({
                        'original': input_file,
                        'repaired': str(repaired_file)
                    })
                    file_pairs.append((input_file, str(repaired_file)))
                    self.logger.info(f"✅ 성공: {repaired_file}")
                else:
                    failed_repairs.append({
                        'original': input_file,
                        'error': 'Baseline repair failed'
                    })
                    self.logger.error(f"❌ 실패: {input_file}")
                    
            except Exception as e:
                failed_repairs.append({
                    'original': input_file,
                    'error': str(e)
                })
                self.logger.error(f"❌ 오류: {input_file} - {e}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 평가 실행
        evaluation_summary = None
        if file_pairs:
            self.logger.info(f"평가 시작: {len(file_pairs)}개 파일 쌍")
            evaluation_summary = self.evaluator.evaluate_group(
                file_pairs, 
                group_name="baseline_batch"
            )
            
            # 결과 저장
            json_file, csv_file = self.evaluator.save_results(evaluation_summary)
            self.evaluator.print_summary(evaluation_summary)
        
        # 배치 처리 요약 저장
        batch_summary = {
            'processing_time': processing_time,
            'total_files': total_files,
            'successful_repairs': len(successful_repairs),
            'failed_repairs': len(failed_repairs),
            'success_rate': (len(successful_repairs) / total_files) * 100.0 if total_files > 0 else 0.0,
            'successful_files': successful_repairs,
            'failed_files': failed_repairs,
            'evaluation_summary': evaluation_summary.__dict__ if evaluation_summary else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # 배치 요약 저장
        batch_file = self.output_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_summary, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"배치 처리 완료: {processing_time:.1f}초")
        self.logger.info(f"성공률: {batch_summary['success_rate']:.1f}% ({len(successful_repairs)}/{total_files})")
        self.logger.info(f"배치 요약 저장: {batch_file}")
        
        return batch_summary
    
    def process_from_directory(self, input_dir: str, pattern: str = "*.yml",
                              max_files: int = None) -> Dict[str, any]:
        """
        디렉토리에서 파일을 찾아 처리합니다.
        
        Args:
            input_dir: 입력 디렉토리
            pattern: 파일 패턴 (예: "*.yml", "*.yaml")
            max_files: 처리할 최대 파일 수
            
        Returns:
            Dict: 처리 결과 요약
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"입력 디렉토리가 없습니다: {input_dir}")
        
        # 파일 찾기
        input_files = list(input_path.glob(pattern))
        input_files = [str(f) for f in input_files if f.is_file()]
        
        if not input_files:
            raise ValueError(f"디렉토리에서 파일을 찾을 수 없습니다: {input_dir}/{pattern}")
        
        self.logger.info(f"디렉토리에서 {len(input_files)}개 파일 발견: {input_dir}")
        
        return self.process_file_list(input_files, max_files)
    
    def process_from_csv(self, csv_file: str, file_path_column: str = "file_path",
                        max_files: int = None) -> Dict[str, any]:
        """
        CSV 파일에서 파일 경로를 읽어 처리합니다.
        
        Args:
            csv_file: CSV 파일 경로
            file_path_column: 파일 경로가 있는 컬럼명
            max_files: 처리할 최대 파일 수
            
        Returns:
            Dict: 처리 결과 요약
        """
        import pandas as pd
        
        try:
            df = pd.read_csv(csv_file)
            if file_path_column not in df.columns:
                raise ValueError(f"CSV에서 컬럼을 찾을 수 없습니다: {file_path_column}")
            
            input_files = df[file_path_column].dropna().tolist()
            input_files = [str(f) for f in input_files if Path(f).exists()]
            
            if not input_files:
                raise ValueError(f"CSV에서 유효한 파일을 찾을 수 없습니다: {csv_file}")
            
            self.logger.info(f"CSV에서 {len(input_files)}개 파일 로드: {csv_file}")
            
            return self.process_file_list(input_files, max_files)
            
        except ImportError:
            raise ImportError("pandas가 필요합니다: pip install pandas")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="베이스라인 배치 평가 도구")
    
    # 입력 방식 선택
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--files", nargs="+", help="개별 파일 경로들")
    input_group.add_argument("--directory", help="입력 디렉토리 경로")
    input_group.add_argument("--csv", help="파일 경로가 있는 CSV 파일")
    
    # 옵션
    parser.add_argument("--pattern", default="*.yml", help="파일 패턴 (디렉토리 모드용)")
    parser.add_argument("--column", default="file_path", help="파일 경로 컬럼명 (CSV 모드용)")
    parser.add_argument("--max-files", type=int, help="처리할 최대 파일 수")
    parser.add_argument("--output-dir", default="./evaluation_results/baseline", help="출력 디렉토리")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        processor = BaselineBatchProcessor(args.output_dir)
        
        # 입력 방식에 따라 처리
        if args.files:
            summary = processor.process_file_list(args.files, args.max_files)
        elif args.directory:
            summary = processor.process_from_directory(args.directory, args.pattern, args.max_files)
        elif args.csv:
            summary = processor.process_from_csv(args.csv, args.column, args.max_files)
        
        print(f"\n🎉 배치 처리 완료!")
        print(f"총 파일: {summary['total_files']}")
        print(f"성공: {summary['successful_repairs']}")
        print(f"실패: {summary['failed_repairs']}")
        print(f"성공률: {summary['success_rate']:.1f}%")
        print(f"처리 시간: {summary['processing_time']:.1f}초")
        
        if summary.get('evaluation_summary'):
            eval_summary = summary['evaluation_summary']
            print(f"\n📊 평가 결과:")
            print(f"구문 성공률: {eval_summary.get('syntax_success_rate', 0):.1f}%")
            print(f"평균 스멜 제거율: {eval_summary.get('avg_smell_removal_rate', 0):.1f}%")
            print(f"평균 Edit Distance: {eval_summary.get('avg_edit_distance', 0):.1f}")
        
    except Exception as e:
        logging.error(f"배치 처리 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

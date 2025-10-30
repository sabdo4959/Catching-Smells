#!/usr/bin/env python3
"""
베이스라인 자동 복구 배치 스크립트

data_original의 파일들을 베이스라인 모드로 복구하여 data_repair_baseline에 저장
"""

import logging
import sys
import os
from pathlib import Path
from typing import List, Dict
import time
from datetime import datetime

# 로컬 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import run_baseline_mode


class BaselineAutoRepairer:
    """베이스라인 자동 복구 클래스"""
    
    def __init__(self, input_dir: str, output_dir: str, log_file: str = None):
        """
        Args:
            input_dir: 입력 디렉토리 (data_original)
            output_dir: 출력 디렉토리 (data_repair_baseline)
            log_file: 기본 로그 파일명 (확장자 제외)
        """
        self.logger = logging.getLogger(__name__)
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.log_file = log_file
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(exist_ok=True)
        
        # logs 디렉토리 생성
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # 로그 파일 설정 (INFO와 DEBUG 레벨 분리)
        if log_file:
            # 파일명에서 확장자 제거
            base_name = Path(log_file).stem
            
            # 루트 로거 설정
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)
            
            # 기존 핸들러 제거 (중복 방지)
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # 1. INFO 레벨 파일 핸들러 (요약 로그)
            info_file_handler = logging.FileHandler(
                logs_dir / f"{base_name}_info.log", 
                encoding='utf-8'
            )
            info_file_handler.setLevel(logging.INFO)
            info_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            info_file_handler.setFormatter(info_formatter)
            
            # INFO 레벨만 필터링하는 필터 추가
            info_filter = logging.Filter()
            info_filter.filter = lambda record: record.levelno >= logging.INFO and record.levelno < logging.ERROR
            info_file_handler.addFilter(info_filter)
            root_logger.addHandler(info_file_handler)
            
            # 2. DEBUG 레벨 파일 핸들러 (상세 로그)
            debug_file_handler = logging.FileHandler(
                logs_dir / f"{base_name}_debug.log", 
                encoding='utf-8'
            )
            debug_file_handler.setLevel(logging.DEBUG)
            debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_file_handler.setFormatter(debug_formatter)
            root_logger.addHandler(debug_file_handler)
            
            # 3. 콘솔 핸들러 (터미널 출력 - INFO 레벨만)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(info_formatter)
            root_logger.addHandler(console_handler)
            
            self.info_log_path = logs_dir / f"{base_name}_info.log"
            self.debug_log_path = logs_dir / f"{base_name}_debug.log"
    
    def repair_all_files(self, max_files: int = None) -> Dict[str, any]:
        """
        모든 파일을 베이스라인 모드로 복구합니다.
        
        Args:
            max_files: 처리할 최대 파일 수 (None이면 모든 파일)
            
        Returns:
            Dict: 처리 결과 요약
        """
        # 입력 파일 목록 가져오기
        input_files = list(self.input_dir.glob("*"))
        input_files = [f for f in input_files if f.is_file()]
        
        if max_files:
            input_files = input_files[:max_files]
        
        total_files = len(input_files)
        self.logger.info(f"베이스라인 자동 복구 시작: {total_files}개 파일")
        self.logger.info(f"입력 디렉토리: {self.input_dir}")
        self.logger.info(f"출력 디렉토리: {self.output_dir}")
        
        start_time = datetime.now()
        successful_repairs = []
        failed_repairs = []
        
        for i, input_file in enumerate(input_files, 1):
            self.logger.info(f"[{i}/{total_files}] 처리 중: {input_file.name}")
            self.logger.info(f"입력 파일 경로: {input_file}")
            
            try:
                # 출력 파일 경로 생성
                output_file = self.output_dir / f"{input_file.name}_baseline_repaired.yml"
                self.logger.info(f"출력 파일 경로: {output_file}")
                
                # 베이스라인 복구 실행
                self.logger.info(f"=== 파일 {i}/{total_files} 베이스라인 복구 시작 ===")
                file_start_time = time.time()
                success = run_baseline_mode(str(input_file), str(output_file))
                processing_time = time.time() - file_start_time
                self.logger.info(f"=== 파일 {i}/{total_files} 베이스라인 복구 완료 ===")
                
                if success and output_file.exists():
                    successful_repairs.append({
                        'input_file': str(input_file),
                        'output_file': str(output_file),
                        'processing_time': processing_time
                    })
                    self.logger.info(f"✅ 성공 ({processing_time:.2f}초): {input_file.name} -> {output_file.name}")
                else:
                    failed_repairs.append({
                        'input_file': str(input_file),
                        'error': 'Baseline repair failed or output file not created',
                        'processing_time': processing_time
                    })
                    self.logger.error(f"❌ 실패 ({processing_time:.2f}초): {input_file.name}")
                    
            except Exception as e:
                failed_repairs.append({
                    'input_file': str(input_file),
                    'error': str(e),
                    'processing_time': 0.0
                })
                self.logger.error(f"❌ 오류: {input_file.name} - {e}")
                self.logger.exception(f"상세 오류 정보:")  # 스택 트레이스 포함
        
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        # 결과 요약
        summary = {
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_processing_time': total_processing_time,
            'total_files': total_files,
            'successful_repairs': len(successful_repairs),
            'failed_repairs': len(failed_repairs),
            'success_rate': (len(successful_repairs) / total_files) * 100.0 if total_files > 0 else 0.0,
            'avg_processing_time': sum(r.get('processing_time', 0) for r in successful_repairs + failed_repairs) / total_files if total_files > 0 else 0.0,
            'successful_files': successful_repairs,
            'failed_files': failed_repairs
        }
        
        # 결과 로깅
        self.logger.info("=" * 60)
        self.logger.info("베이스라인 자동 복구 완료!")
        self.logger.info(f"총 처리 시간: {total_processing_time:.1f}초")
        self.logger.info(f"총 파일: {total_files}")
        self.logger.info(f"성공: {len(successful_repairs)} ({summary['success_rate']:.1f}%)")
        self.logger.info(f"실패: {len(failed_repairs)}")
        self.logger.info(f"평균 처리 시간: {summary['avg_processing_time']:.2f}초/파일")
        self.logger.info(f"출력 파일 위치: {self.output_dir}")
        if hasattr(self, 'info_log_path') and hasattr(self, 'debug_log_path'):
            self.logger.info(f"INFO 로그 파일: {self.info_log_path}")
            self.logger.info(f"DEBUG 로그 파일: {self.debug_log_path}")
        self.logger.info("=" * 60)
        
        return summary


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="베이스라인 자동 복구 도구")
    parser.add_argument("--input-dir", required=True, help="입력 디렉토리 경로")
    parser.add_argument("--output-dir", required=True, help="출력 디렉토리 경로")
    parser.add_argument("--max-files", type=int, help="처리할 최대 파일 수")
    parser.add_argument("--log-file", help="로그 파일 경로")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # 로그 파일 경로 자동 생성
    if not args.log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.log_file = f"baseline_repair_log_{timestamp}.log"
    
    # 기본 로깅 설정 (BaselineAutoRepairer에서 추가 설정됨)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]  # 핸들러는 BaselineAutoRepairer에서 설정
    )
    
    try:
        repairer = BaselineAutoRepairer(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            log_file=args.log_file
        )
        
        summary = repairer.repair_all_files(max_files=args.max_files)
        
        print(f"\n🎉 베이스라인 자동 복구 완료!")
        print(f"총 파일: {summary['total_files']}")
        print(f"성공: {summary['successful_repairs']}")
        print(f"실패: {summary['failed_repairs']}")
        print(f"성공률: {summary['success_rate']:.1f}%")
        print(f"총 처리 시간: {summary['total_processing_time']:.1f}초")
        if hasattr(repairer, 'info_log_path') and hasattr(repairer, 'debug_log_path'):
            print(f"INFO 로그: {repairer.info_log_path}")
            print(f"DEBUG 로그: {repairer.debug_log_path}")
        else:
            print(f"로그 파일: {args.log_file}")
        
        return summary['failed_repairs'] == 0
        
    except Exception as e:
        logging.error(f"배치 처리 중 오류 발생: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

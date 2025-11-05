#!/usr/bin/env python3
"""
향상된 베이스라인 자동 복구 배치 스크립트

data_original의 파일들을 베이스라인 모드로 복구하여 출력 디렉토리에 저장
llama3.1:8b, codegemma:7b, codellama:7b 등 다양한 모델 지원
"""

import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional
import time
from datetime import datetime
import json

# 로컬 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import run_baseline_mode
from utils.llm_api import get_model_info, get_available_providers


class EnhancedBaselineAutoRepairer:
    """향상된 베이스라인 자동 복구 클래스"""
    
    def __init__(self, 
                 input_dir: str, 
                 output_dir: str, 
                 log_file: str = None,
                 llm_provider: str = None,
                 llm_model: str = None,
                 ollama_url: str = None):
        """
        Args:
            input_dir: 입력 디렉토리 (data_original)
            output_dir: 출력 디렉토리 (llama3.1_8b/data_repair_baseline 등)
            log_file: 기본 로그 파일명 (확장자 제외)
            llm_provider: LLM 제공자 (openai, ollama)
            llm_model: 사용할 모델명
            ollama_url: Ollama 서버 URL
        """
        self.logger = logging.getLogger(__name__)
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.log_file = log_file
        
        # LLM 설정
        self.llm_provider = llm_provider or os.getenv("LLM_PROVIDER", "openai")
        self.llm_model = llm_model or self._get_default_model()
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://115.145.178.160:11434/api/chat")
        
        # 환경변수 설정
        if self.llm_provider.lower() == "ollama":
            os.environ["LLM_PROVIDER"] = "ollama"
            if self.llm_model:
                os.environ["OLLAMA_MODEL"] = self.llm_model
            if self.ollama_url:
                os.environ["OLLAMA_URL"] = self.ollama_url
        else:
            os.environ["LLM_PROVIDER"] = "openai"
            if self.llm_model:
                os.environ["OPENAI_MODEL"] = self.llm_model
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # logs 디렉토리 생성
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # 모델 정보 로깅
        self._log_model_info()
        
        # 로그 파일 설정
        if log_file:
            self._setup_logging(logs_dir, log_file)
    
    def _get_default_model(self) -> str:
        """제공자에 따른 기본 모델 반환"""
        if self.llm_provider.lower() == "ollama":
            return "llama3.1:8b"
        else:
            return "gpt-4o-mini"
    
    def _log_model_info(self):
        """현재 LLM 설정 정보 로깅"""
        try:
            model_info = get_model_info()
            available_providers = get_available_providers()
            
            self.logger.info("=" * 60)
            self.logger.info("🤖 LLM 설정 정보")
            self.logger.info(f"사용 가능한 제공자: {available_providers}")
            self.logger.info(f"현재 제공자: {model_info.get('provider', 'unknown')}")
            self.logger.info(f"모델 키: {model_info.get('model_key', 'unknown')}")
            self.logger.info(f"실제 모델: {model_info.get('actual_model', 'unknown')}")
            if model_info.get('url'):
                self.logger.info(f"서버 URL: {model_info.get('url')}")
            self.logger.info("=" * 60)
        except Exception as e:
            self.logger.warning(f"모델 정보 가져오기 실패: {e}")
    
    def _setup_logging(self, logs_dir: Path, log_file: str):
        """로깅 설정"""
        # 파일명에서 확장자 제거 및 모델 정보 추가
        base_name = Path(log_file).stem
        provider_model = f"{self.llm_provider}_{self.llm_model.replace(':', '_').replace('.', '_')}"
        base_name = f"{base_name}_{provider_model}"
        
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
    
    def repair_all_files(self, max_files: int = None, start_from: int = 0) -> Dict[str, any]:
        """
        모든 파일을 베이스라인 모드로 복구합니다.
        
        Args:
            max_files: 처리할 최대 파일 수 (None이면 모든 파일)
            start_from: 시작할 파일 인덱스 (0부터 시작)
            
        Returns:
            Dict: 처리 결과 요약
        """
        # 입력 파일 목록 가져오기
        input_files = list(self.input_dir.glob("*"))
        input_files = [f for f in input_files if f.is_file()]
        input_files.sort()  # 일관된 순서 보장
        
        # 시작점과 최대 파일 수 적용
        if start_from > 0:
            input_files = input_files[start_from:]
        
        if max_files:
            input_files = input_files[:max_files]
        
        total_files = len(input_files)
        self.logger.info(f"향상된 베이스라인 자동 복구 시작: {total_files}개 파일")
        self.logger.info(f"입력 디렉토리: {self.input_dir}")
        self.logger.info(f"출력 디렉토리: {self.output_dir}")
        if start_from > 0:
            self.logger.info(f"시작 인덱스: {start_from}")
        
        start_time = datetime.now()
        successful_repairs = []
        failed_repairs = []
        
        for i, input_file in enumerate(input_files, 1):
            actual_index = start_from + i
            self.logger.info(f"[{i}/{total_files}] (전체 #{actual_index}) 처리 중: {input_file.name}")
            
            try:
                # 출력 파일 경로 생성 (모델 정보 포함)
                provider_model = f"{self.llm_provider}_{self.llm_model.replace(':', '_').replace('.', '_')}"
                output_file = self.output_dir / f"{input_file.name}_{provider_model}_baseline_repaired.yml"
                
                # 이미 처리된 파일 건너뛰기 (재시작 지원)
                if output_file.exists():
                    self.logger.info(f"⏭️  건너뛰기 (이미 존재): {output_file.name}")
                    successful_repairs.append({
                        'input_file': str(input_file),
                        'output_file': str(output_file),
                        'processing_time': 0.0,
                        'skipped': True
                    })
                    continue
                
                # 베이스라인 복구 실행
                self.logger.info(f"=== 파일 {i}/{total_files} 베이스라인 복구 시작 ===")
                file_start_time = time.time()
                success = run_baseline_mode(str(input_file), str(output_file))
                processing_time = time.time() - file_start_time
                self.logger.info(f"=== 파일 {i}/{total_files} 베이스라인 복구 완료 ===")
                
                if success and output_file.exists():
                    file_size = output_file.stat().st_size
                    successful_repairs.append({
                        'input_file': str(input_file),
                        'output_file': str(output_file),
                        'processing_time': processing_time,
                        'file_size': file_size,
                        'skipped': False
                    })
                    self.logger.info(f"✅ 성공 ({processing_time:.2f}초, {file_size} bytes): {input_file.name}")
                else:
                    failed_repairs.append({
                        'input_file': str(input_file),
                        'error': 'Baseline repair failed or output file not created',
                        'processing_time': processing_time
                    })
                    self.logger.error(f"❌ 실패 ({processing_time:.2f}초): {input_file.name}")
                    
            except KeyboardInterrupt:
                self.logger.warning(f"사용자 중단 요청 (Ctrl+C)")
                break
                    
            except Exception as e:
                failed_repairs.append({
                    'input_file': str(input_file),
                    'error': str(e),
                    'processing_time': 0.0
                })
                self.logger.error(f"❌ 오류: {input_file.name} - {e}")
                self.logger.exception(f"상세 오류 정보:")
                
                # 치명적 오류인 경우 중단 고려
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    self.logger.error("네트워크 오류 감지. 잠시 대기 후 계속...")
                    time.sleep(5)
        
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        # 결과 요약
        summary = {
            'model_info': {
                'provider': self.llm_provider,
                'model': self.llm_model,
                'url': self.ollama_url if self.llm_provider.lower() == "ollama" else None
            },
            'execution_info': {
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_processing_time': total_processing_time,
                'start_from': start_from,
                'requested_files': max_files,
                'processed_files': len(input_files)
            },
            'results': {
                'total_files': total_files,
                'successful_repairs': len(successful_repairs),
                'failed_repairs': len(failed_repairs),
                'success_rate': (len(successful_repairs) / total_files) * 100.0 if total_files > 0 else 0.0,
                'avg_processing_time': sum(r.get('processing_time', 0) for r in successful_repairs + failed_repairs) / total_files if total_files > 0 else 0.0,
            },
            'detailed_results': {
                'successful_files': successful_repairs,
                'failed_files': failed_repairs
            }
        }
        
        # 결과 JSON 저장
        self._save_results(summary)
        
        # 결과 로깅
        self._log_summary(summary)
        
        return summary
    
    def _save_results(self, summary: Dict):
        """결과를 JSON 파일로 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            provider_model = f"{self.llm_provider}_{self.llm_model.replace(':', '_').replace('.', '_')}"
            results_file = self.output_dir / f"batch_results_{provider_model}_{timestamp}.json"
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"결과 JSON 저장: {results_file}")
            
        except Exception as e:
            self.logger.error(f"결과 저장 실패: {e}")
    
    def _log_summary(self, summary: Dict):
        """결과 요약 로깅"""
        results = summary['results']
        model_info = summary['model_info']
        
        self.logger.info("=" * 60)
        self.logger.info("🎉 향상된 베이스라인 자동 복구 완료!")
        self.logger.info(f"사용 모델: {model_info['provider']} / {model_info['model']}")
        self.logger.info(f"총 처리 시간: {summary['execution_info']['total_processing_time']:.1f}초")
        self.logger.info(f"총 파일: {results['total_files']}")
        self.logger.info(f"성공: {results['successful_repairs']} ({results['success_rate']:.1f}%)")
        self.logger.info(f"실패: {results['failed_repairs']}")
        self.logger.info(f"평균 처리 시간: {results['avg_processing_time']:.2f}초/파일")
        self.logger.info(f"출력 파일 위치: {self.output_dir}")
        if hasattr(self, 'info_log_path') and hasattr(self, 'debug_log_path'):
            self.logger.info(f"INFO 로그 파일: {self.info_log_path}")
            self.logger.info(f"DEBUG 로그 파일: {self.debug_log_path}")
        self.logger.info("=" * 60)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="향상된 베이스라인 자동 복구 도구")
    parser.add_argument("--input-dir", required=True, help="입력 디렉토리 경로")
    parser.add_argument("--output-dir", required=True, help="출력 디렉토리 경로")
    parser.add_argument("--max-files", type=int, help="처리할 최대 파일 수")
    parser.add_argument("--start-from", type=int, default=0, help="시작할 파일 인덱스")
    parser.add_argument("--log-file", help="로그 파일 경로")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    # LLM 설정
    parser.add_argument("--llm-provider", choices=["openai", "ollama"], help="LLM 제공자")
    parser.add_argument("--llm-model", help="사용할 모델명")
    parser.add_argument("--ollama-url", help="Ollama 서버 URL")
    
    args = parser.parse_args()
    
    # 로그 파일 경로 자동 생성
    if not args.log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        provider = args.llm_provider or os.getenv("LLM_PROVIDER", "openai")
        args.log_file = f"enhanced_baseline_repair_{provider}_{timestamp}"
    
    # 기본 로깅 설정
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]  # 핸들러는 EnhancedBaselineAutoRepairer에서 설정
    )
    
    try:
        repairer = EnhancedBaselineAutoRepairer(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            log_file=args.log_file,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            ollama_url=args.ollama_url
        )
        
        summary = repairer.repair_all_files(
            max_files=args.max_files,
            start_from=args.start_from
        )
        
        results = summary['results']
        model_info = summary['model_info']
        
        print(f"\n🎉 향상된 베이스라인 자동 복구 완료!")
        print(f"사용 모델: {model_info['provider']} / {model_info['model']}")
        print(f"총 파일: {results['total_files']}")
        print(f"성공: {results['successful_repairs']}")
        print(f"실패: {results['failed_repairs']}")
        print(f"성공률: {results['success_rate']:.1f}%")
        print(f"총 처리 시간: {summary['execution_info']['total_processing_time']:.1f}초")
        
        if hasattr(repairer, 'info_log_path') and hasattr(repairer, 'debug_log_path'):
            print(f"INFO 로그: {repairer.info_log_path}")
            print(f"DEBUG 로그: {repairer.debug_log_path}")
        
        return results['failed_repairs'] == 0
        
    except KeyboardInterrupt:
        print("\n❌ 사용자 중단 (Ctrl+C)")
        return False
        
    except Exception as e:
        logging.error(f"배치 처리 중 오류 발생: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

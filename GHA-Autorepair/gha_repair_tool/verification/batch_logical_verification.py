#!/usr/bin/env python3
"""
대규모 논리적 동치성 검증 스크립트
LogicalVerifier를 사용하여 원본과 복구된 워크플로우의 논리적 동치성을 일괄 검증
"""

import os
import sys
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import argparse

# 프로젝트 루트를 Python 경로에 추가
sys.path.append('.')

from verification.logical_verifier import LogicalVerifier

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """로깅 설정"""
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, log_level.upper()))
    return logger

def find_matching_files(original_dir: str, repaired_dir: str, max_files: int = None, repair_suffix: str = "baseline") -> List[tuple]:
    """원본과 복구 파일의 매칭 쌍을 찾기"""
    matches = []
    original_files = set(os.listdir(original_dir))
    
    # 수정된 파일 패턴들 지원
    if repair_suffix == "baseline":
        suffix_pattern = "_baseline_repaired.yml"
    elif repair_suffix == "two_phase":
        suffix_pattern = "_two_phase_repaired.yml"
    elif repair_suffix == "gha_repair":
        suffix_pattern = "_gha_repaired.yml"
    else:
        suffix_pattern = f"_{repair_suffix}_repaired.yml"
    
    for repaired_file in os.listdir(repaired_dir):
        if repaired_file.endswith(suffix_pattern):
            # 원본 파일명 추출
            original_name = repaired_file.replace(suffix_pattern, '')
            
            if original_name in original_files:
                original_path = os.path.join(original_dir, original_name)
                repaired_path = os.path.join(repaired_dir, repaired_file)
                matches.append((original_path, repaired_path, original_name))
    
    if max_files:
        matches = matches[:max_files]
    
    return matches

def read_file_content(file_path: str) -> str:
    """파일 내용을 읽기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"파일 읽기 실패 {file_path}: {e}")

def analyze_logical_differences(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """논리적 차이 상세 분석"""
    analysis = {
        'total_logical_mismatches': 0,
        'trigger_mismatches': 0,
        'if_mismatches': 0,
        'concurrency_mismatches': 0,
        'yaml_parsing_errors': 0,
        'logical_mismatch_files': [],
        'trigger_mismatch_files': [],
        'if_mismatch_files': [],
        'concurrency_mismatch_files': [],
        'yaml_error_files': []
    }
    
    for result in results:
        file_id = result['file_id']
        verification_result = result['verification_result']
        
        if not verification_result.get('is_safe', True):
            # YAML 파싱 오류 확인
            if 'message' in verification_result and '검증 오류' in verification_result['message']:
                analysis['yaml_parsing_errors'] += 1
                analysis['yaml_error_files'].append(file_id)
                continue
            
            # SMT 검증 결과 분석
            if 'results' in verification_result:
                has_logical_mismatch = False
                results_detail = verification_result['results']
                
                # 트리거 조건 불일치
                trigger_result = results_detail.get('trigger_verification', {})
                if not trigger_result.get('is_safe', True):
                    analysis['trigger_mismatches'] += 1
                    analysis['trigger_mismatch_files'].append(file_id)
                    has_logical_mismatch = True
                
                # if 조건 불일치
                if_result = results_detail.get('if_verification', {})
                if not if_result.get('is_safe', True):
                    analysis['if_mismatches'] += 1
                    analysis['if_mismatch_files'].append(file_id)
                    has_logical_mismatch = True
                
                # 동시성 제어 불일치
                concurrency_result = results_detail.get('concurrency_verification', {})
                if not concurrency_result.get('is_safe', True):
                    analysis['concurrency_mismatches'] += 1
                    analysis['concurrency_mismatch_files'].append(file_id)
                    has_logical_mismatch = True
                
                if has_logical_mismatch:
                    analysis['total_logical_mismatches'] += 1
                    analysis['logical_mismatch_files'].append(file_id)
    
    return analysis

def verify_workflow_pair(
    verifier: LogicalVerifier, 
    original_path: str, 
    repaired_path: str, 
    file_id: str,
    strict_mode: bool = False
) -> Dict[str, Any]:
    """단일 워크플로우 쌍 검증"""
    try:
        # 복구된 파일 내용 읽기
        repaired_content = read_file_content(repaired_path)
        
        # 논리적 동치성 검증
        result = verifier.verify_logical_equivalence(
            original_path, 
            repaired_content, 
            strict_mode=strict_mode
        )
        
        return {
            'file_id': file_id,
            'original_path': original_path,
            'repaired_path': repaired_path,
            'verification_result': result,
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'file_id': file_id,
            'original_path': original_path,
            'repaired_path': repaired_path,
            'verification_result': None,
            'error': str(e),
            'status': 'error'
        }

def main():
    parser = argparse.ArgumentParser(description='대규모 논리적 동치성 검증')
    parser.add_argument('--original-dir', required=True, help='원본 워크플로우 디렉토리')
    parser.add_argument('--repaired-dir', required=True, help='복구된 워크플로우 디렉토리')
    parser.add_argument('--repair-method', default='baseline', 
                        choices=['baseline', 'two_phase', 'gha_repair'], 
                        help='복구 방법 (default: baseline)')
    parser.add_argument('--output-file', help='결과 JSON 파일 경로')
    parser.add_argument('--max-files', type=int, default=100, help='최대 처리 파일 수')
    parser.add_argument('--strict-mode', action='store_true', help='엄격 모드 사용')
    parser.add_argument('--log-level', default='INFO', help='로깅 레벨')
    
    args = parser.parse_args()
    
    # 로깅 설정
    logger = setup_logging(args.log_level)
    
    logger.info(f"=== 대규모 논리적 동치성 검증 시작 ===")
    logger.info(f"원본 디렉토리: {args.original_dir}")
    logger.info(f"복구 디렉토리: {args.repaired_dir}")
    logger.info(f"복구 방법: {args.repair_method}")
    logger.info(f"최대 파일 수: {args.max_files}")
    logger.info(f"엄격 모드: {args.strict_mode}")
    
    # LogicalVerifier 초기화
    verifier = LogicalVerifier()
    
    # 매칭 파일 찾기
    matches = find_matching_files(args.original_dir, args.repaired_dir, args.max_files, args.repair_method)
    logger.info(f"매칭된 파일 쌍: {len(matches)}개")
    
    if not matches:
        logger.error("매칭되는 파일이 없습니다.")
        return
    
    # 검증 실행
    results = []
    safe_count = 0
    unsafe_count = 0
    error_count = 0
    
    start_time = time.time()
    
    for i, (original_path, repaired_path, file_id) in enumerate(matches, 1):
        logger.info(f"[{i}/{len(matches)}] 검증 중: {file_id}")
        
        result = verify_workflow_pair(
            verifier, 
            original_path, 
            repaired_path, 
            file_id,
            args.strict_mode
        )
        
        if result['status'] == 'error':
            logger.error(f"❌ 오류: {file_id} - {result['error']}")
            error_count += 1
        else:
            verification_result = result['verification_result']
            is_safe = verification_result.get('is_safe', False)
            
            if is_safe:
                logger.info(f"✅ 안전: {file_id}")
                safe_count += 1
            else:
                logger.warning(f"⚠️  위험: {file_id}")
                unsafe_count += 1
                
                # 위험한 경우 상세 정보 출력
                if 'results' in verification_result:
                    for check_name, check_result in verification_result['results'].items():
                        if not check_result['is_safe']:
                            logger.warning(f"  - {check_name}: {check_result['message']}")
        
        results.append(result)
    
    elapsed_time = time.time() - start_time
    
    # 논리적 차이 상세 분석
    logical_analysis = analyze_logical_differences(results)
    
    # 요약 통계
    total_verified = safe_count + unsafe_count
    logger.info(f"\n=== 검증 완료 ===")
    logger.info(f"총 처리: {len(matches)}개")
    logger.info(f"검증 성공: {total_verified}개")
    logger.info(f"  - 안전: {safe_count}개 ({safe_count/total_verified*100:.1f}%)")
    logger.info(f"  - 위험: {unsafe_count}개 ({unsafe_count/total_verified*100:.1f}%)")
    logger.info(f"오류: {error_count}개")
    logger.info(f"소요 시간: {elapsed_time:.2f}초")
    
    # 논리적 차이 상세 통계 출력
    logger.info(f"\n=== 논리적 차이 분석 ===")
    logger.info(f"실제 논리적 불일치: {logical_analysis['total_logical_mismatches']}개")
    logger.info(f"  - 트리거 조건 불일치: {logical_analysis['trigger_mismatches']}개")
    logger.info(f"  - if 조건 불일치: {logical_analysis['if_mismatches']}개")
    logger.info(f"  - 동시성 제어 불일치: {logical_analysis['concurrency_mismatches']}개")
    logger.info(f"YAML 파싱 오류: {logical_analysis['yaml_parsing_errors']}개")
    
    # 결과 저장
    summary = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'configuration': {
            'original_dir': args.original_dir,
            'repaired_dir': args.repaired_dir,
            'repair_method': args.repair_method,
            'max_files': args.max_files,
            'strict_mode': args.strict_mode
        },
        'statistics': {
            'total_files': len(matches),
            'verified_files': total_verified,
            'safe_files': safe_count,
            'unsafe_files': unsafe_count,
            'error_files': error_count,
            'safety_rate': safe_count / total_verified if total_verified > 0 else 0,
            'elapsed_time': elapsed_time
        },
        'logical_analysis': logical_analysis,
        'results': results
    }
    
    # JSON 파일로 저장
    if args.output_file:
        output_path = args.output_file
    else:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        # results 폴더에 저장
        results_dir = "verification/results"
        os.makedirs(results_dir, exist_ok=True)
        output_path = f"{results_dir}/logical_verification_{args.repair_method}_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"결과 저장: {output_path}")

if __name__ == "__main__":
    main()

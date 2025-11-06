#!/usr/bin/env python3
"""
통합 검증기 배치 실행기

3가지 복구 방법(baseline, two_phase, gha_repair)에 대해
구조적 + 논리적 통합 검증을 수행합니다.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# 현재 디렉토리를 path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrated_verifier import IntegratedVerifier

def setup_logging(log_level: str = "WARNING") -> logging.Logger:
    """로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def find_matching_files(original_dir: str, repaired_dir: str, repair_method: str, max_files: int = None):
    """원본과 복구 파일 매칭"""
    matches = []
    original_files = set(os.listdir(original_dir))
    
    # 복구 방법별 파일명 패턴
    if repair_method == "baseline":
        suffix = "_baseline_repaired.yml"
    elif repair_method == "two_phase":
        suffix = "_two_phase_repaired.yml"
    elif repair_method == "gha_repair":
        suffix = "_gha_repaired.yml"
    else:
        suffix = f"_{repair_method}_repaired.yml"
    
    for repaired_file in os.listdir(repaired_dir):
        if repaired_file.endswith(suffix):
            original_name = repaired_file.replace(suffix, '')
            if original_name in original_files:
                original_path = os.path.join(original_dir, original_name)
                repaired_path = os.path.join(repaired_dir, repaired_file)
                matches.append((original_path, repaired_path, original_name))
    
    if max_files:
        matches = matches[:max_files]
    
    return matches

def run_integrated_verification(
    original_dir: str,
    repaired_dir: str,
    repair_method: str,
    max_files: int = 100,
    verification_mode: str = "hybrid"
):
    """통합 검증 실행"""
    logger = setup_logging()
    
    logger.info(f"=== 통합 검증 시작 ===")
    logger.info(f"원본 디렉토리: {original_dir}")
    logger.info(f"복구 디렉토리: {repaired_dir}")
    logger.info(f"복구 방법: {repair_method}")
    logger.info(f"검증 모드: {verification_mode}")
    logger.info(f"최대 파일 수: {max_files}")
    
    # 파일 매칭
    matches = find_matching_files(original_dir, repaired_dir, repair_method, max_files)
    logger.info(f"매칭된 파일 쌍: {len(matches)}개")
    
    if not matches:
        logger.error("매칭되는 파일이 없습니다.")
        return None
    
    # 통합 검증기 초기화
    verifier = IntegratedVerifier()
    
    # 결과 수집
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'configuration': {
            'original_dir': original_dir,
            'repaired_dir': repaired_dir,
            'repair_method': repair_method,
            'verification_mode': verification_mode,
            'max_files': max_files
        },
        'statistics': {
            'total_files': len(matches),
            'verified_files': 0,
            'safe_files': 0,
            'unsafe_files': 0,
            'error_files': 0,
            'safety_rate': 0.0,
            'elapsed_time': 0.0
        },
        'verification_details': {
            'structural_only_safe': 0,
            'logical_only_safe': 0,
            'both_safe': 0,
            'both_unsafe': 0,
            'mixed_results': 0,
            'average_confidence': 0.0,
            'structural_safe_count': 0,
            'structural_unsafe_count': 0,
            'logical_safe_count': 0,
            'logical_unsafe_count': 0,
            'structural_error_count': 0,
            'logical_error_count': 0
        },
        'file_results': []
    }
    
    start_time = datetime.now()
    total_confidence = 0.0
    
    # 파일별 검증 수행
    for i, (original_path, repaired_path, file_id) in enumerate(matches, 1):
        logger.info(f"[{i}/{len(matches)}] 검증 중: {file_id}")
        
        try:
            verification_result = verifier.verify_repair_safety(
                original_path,
                repaired_path,
                verification_mode=verification_mode
            )
            
            results['statistics']['verified_files'] += 1
            
            if verification_result.get('is_safe', False):
                results['statistics']['safe_files'] += 1
            else:
                results['statistics']['unsafe_files'] += 1
            
            # 상세 통계 업데이트
            structural_safe = verification_result.get('structural_result', {}).get('is_safe', False)
            logical_safe = verification_result.get('logical_result', {}).get('is_safe', False)
            
            # 구조적 검증 결과 카운트
            if 'structural_result' in verification_result:
                if verification_result['structural_result'].get('error'):
                    results['verification_details']['structural_error_count'] += 1
                elif structural_safe:
                    results['verification_details']['structural_safe_count'] += 1
                else:
                    results['verification_details']['structural_unsafe_count'] += 1
            
            # 논리적 검증 결과 카운트
            if 'logical_result' in verification_result:
                if verification_result['logical_result'].get('error'):
                    results['verification_details']['logical_error_count'] += 1
                elif logical_safe:
                    results['verification_details']['logical_safe_count'] += 1
                else:
                    results['verification_details']['logical_unsafe_count'] += 1
            
            if verification_mode == "hybrid":
                if structural_safe and logical_safe:
                    results['verification_details']['both_safe'] += 1
                elif not structural_safe and not logical_safe:
                    results['verification_details']['both_unsafe'] += 1
                else:
                    results['verification_details']['mixed_results'] += 1
            elif verification_mode == "structural":
                if structural_safe:
                    results['verification_details']['structural_only_safe'] += 1
            elif verification_mode == "logical":
                if logical_safe:
                    results['verification_details']['logical_only_safe'] += 1
            
            confidence = verification_result.get('confidence_score', 0.0)
            total_confidence += confidence
            
            # 파일 결과 저장
            results['file_results'].append({
                'file_id': file_id,
                'is_safe': verification_result.get('is_safe', False),
                'confidence_score': confidence,
                'verification_method': verification_result.get('verification_method'),
                'structural_safe': structural_safe,
                'logical_safe': logical_safe,
                'summary': verification_result.get('summary', {}),
                'failure_reasons': verification_result.get('summary', {}).get('failure_reasons', [])
            })
            
        except Exception as e:
            logger.error(f"파일 {file_id} 검증 중 오류: {e}")
            results['statistics']['error_files'] += 1
            results['file_results'].append({
                'file_id': file_id,
                'is_safe': False,
                'error': str(e)
            })
    
    # 최종 통계 계산
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    results['statistics']['elapsed_time'] = elapsed_time
    if results['statistics']['verified_files'] > 0:
        results['statistics']['safety_rate'] = results['statistics']['safe_files'] / results['statistics']['verified_files']
        results['verification_details']['average_confidence'] = total_confidence / results['statistics']['verified_files']
    
    # 결과 저장
    output_file = f"verification/results/integrated_verification_{repair_method}_{verification_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"=== 통합 검증 완료 ===")
    logger.info(f"처리된 파일: {results['statistics']['verified_files']}개")
    logger.info(f"안전한 파일: {results['statistics']['safe_files']}개")
    logger.info(f"안전율: {results['statistics']['safety_rate']:.1%}")
    logger.info(f"평균 신뢰도: {results['verification_details']['average_confidence']:.3f}")
    
    # 상세 통계 출력
    logger.info(f"=== 상세 검증 통계 ===")
    logger.info(f"구조적 검증 - 안전: {results['verification_details']['structural_safe_count']}개, "
               f"위험: {results['verification_details']['structural_unsafe_count']}개, "
               f"오류: {results['verification_details']['structural_error_count']}개")
    logger.info(f"논리적 검증 - 안전: {results['verification_details']['logical_safe_count']}개, "
               f"위험: {results['verification_details']['logical_unsafe_count']}개, "
               f"오류: {results['verification_details']['logical_error_count']}개")
    
    if verification_mode == "hybrid":
        logger.info(f"하이브리드 결과 - 둘 다 안전: {results['verification_details']['both_safe']}개, "
                   f"둘 다 위험: {results['verification_details']['both_unsafe']}개, "
                   f"혼재: {results['verification_details']['mixed_results']}개")
    
    logger.info(f"처리 시간: {elapsed_time:.2f}초")
    logger.info(f"결과 저장: {output_file}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="통합 검증기 배치 실행")
    parser.add_argument("--original-dir", required=True, help="원본 파일 디렉토리")
    parser.add_argument("--repaired-dir", required=True, help="복구된 파일 디렉토리")
    parser.add_argument("--repair-method", required=True, choices=["baseline", "two_phase", "gha_repair"], help="복구 방법")
    parser.add_argument("--verification-mode", default="hybrid", choices=["structural", "logical", "hybrid"], help="검증 모드")
    parser.add_argument("--max-files", type=int, default=100, help="최대 처리 파일 수")
    
    args = parser.parse_args()
    
    run_integrated_verification(
        args.original_dir,
        args.repaired_dir,
        args.repair_method,
        args.max_files,
        args.verification_mode
    )

if __name__ == "__main__":
    main()

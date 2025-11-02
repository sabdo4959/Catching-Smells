#!/usr/bin/env python3
"""
3가지 GitHub Actions 수정 방법의 구조적 안전성 비교 분석 도구

이 스크립트는 baseline, gha_repair, two_phase 방법의 키 구조 검증 결과를
종합적으로 비교 분석합니다.

Usage:
    python compare_methods.py [--results-dir RESULTS_DIR]
"""

import json
import os
import argparse
from typing import Dict, Set


def load_verification_results(results_dir: str) -> Dict[str, dict]:
    """검증 결과 파일들을 로드합니다."""
    methods = {
        'baseline': 'key_structure_verification_baseline.json',
        'gha_repair': 'key_structure_verification_gha_repair.json',
        'two_phase': 'key_structure_verification_two_phase.json'
    }
    
    results = {}
    for method, filename in methods.items():
        filepath = os.path.join(results_dir, filename)
        if os.path.exists(filepath):
            with open(filepath) as f:
                results[method] = json.load(f)
        else:
            print(f"⚠️  경고: {filepath} 파일을 찾을 수 없습니다.")
    
    return results


def extract_method_files(base_dir: str) -> Dict[str, Set[str]]:
    """각 방법에서 처리된 파일 목록을 추출합니다."""
    method_directories = {
        'baseline': 'data_repair_baseline',
        'gha_repair': 'data_gha_repair', 
        'two_phase': 'data_repair_two_phase'
    }
    
    method_files = {}
    for method, dirname in method_directories.items():
        files = set()
        full_path = os.path.join(base_dir, dirname)
        if os.path.exists(full_path):
            for f in os.listdir(full_path):
                if f.endswith('.yml'):
                    # 파일명에서 접미사 제거
                    clean_name = f.replace(f'_{method}_repaired.yml', '') \
                                  .replace('_gha_repaired.yml', '') \
                                  .replace('_two_phase_repaired.yml', '')
                    files.add(clean_name)
        method_files[method] = files
    
    return method_files


def extract_safe_files(results: Dict[str, dict], method_files: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """각 방법별 안전한 파일들을 추출합니다."""
    safe_files = {}
    for method in results.keys():
        if method in results:
            unsafe = set(results[method]['unsafe_details'])
            safe_files[method] = method_files[method] - unsafe
        else:
            safe_files[method] = set()
    
    return safe_files


def print_statistics(safe_files: Dict[str, Set[str]], method_files: Dict[str, Set[str]]):
    """전체 통계를 출력합니다."""
    print('📊 전체 통계:')
    for method in ['baseline', 'gha_repair', 'two_phase']:
        if method in safe_files:
            total = len(method_files[method])
            safe_count = len(safe_files[method])
            safe_rate = (safe_count / total * 100) if total > 0 else 0
            print(f'  {method:12}: {safe_count:2}/{total:3}개 ({safe_rate:4.1f}%) 안전')


def print_safe_files_by_method(safe_files: Dict[str, Set[str]]):
    """각 방법별 안전한 파일들을 출력합니다."""
    print('\n✅ 각 방법별 안전한 파일들:')
    for method in ['baseline', 'gha_repair', 'two_phase']:
        if method in safe_files:
            print(f'\n{method.upper()} ({len(safe_files[method])}개):')
            for f in sorted(safe_files[method]):
                display_name = f'{f[:50]}...' if len(f) > 50 else f
                print(f'  ✓ {display_name}')


def analyze_intersections(safe_files: Dict[str, Set[str]]):
    """교집합 분석을 수행합니다."""
    print('\n🔄 교집합 분석:')
    
    # 세 방법 모두 안전한 파일들
    common_all = safe_files['baseline'] & safe_files['gha_repair'] & safe_files['two_phase']
    print(f'  세 방법 모두 안전: {len(common_all)}개')
    for f in sorted(common_all):
        display_name = f'{f[:60]}...' if len(f) > 60 else f
        print(f'    🎯 {display_name}')
    
    # 두 방법씩의 교집합
    common_baseline_gha = safe_files['baseline'] & safe_files['gha_repair']
    common_baseline_two = safe_files['baseline'] & safe_files['two_phase']
    common_gha_two = safe_files['gha_repair'] & safe_files['two_phase']
    
    print(f'\n  baseline & gha_repair 공통: {len(common_baseline_gha)}개')
    print(f'  baseline & two_phase 공통: {len(common_baseline_two)}개')  
    print(f'  gha_repair & two_phase 공통: {len(common_gha_two)}개')


def analyze_unique_successes(safe_files: Dict[str, Set[str]]):
    """각 방법만의 고유 안전 파일들을 분석합니다."""
    print('\n🚀 각 방법만의 고유 안전 파일:')
    
    gha_only = safe_files['gha_repair'] - safe_files['baseline'] - safe_files['two_phase']
    two_only = safe_files['two_phase'] - safe_files['baseline'] - safe_files['gha_repair']
    baseline_only = safe_files['baseline'] - safe_files['gha_repair'] - safe_files['two_phase']
    
    print(f'  GHA-Repair만 안전: {len(gha_only)}개')
    for f in sorted(gha_only):
        display_name = f'{f[:60]}...' if len(f) > 60 else f
        print(f'    💎 {display_name}')
    
    print(f'\n  Two-Phase만 안전: {len(two_only)}개')
    for f in sorted(two_only):
        display_name = f'{f[:60]}...' if len(f) > 60 else f
        print(f'    🔹 {display_name}')
        
    print(f'\n  Baseline만 안전: {len(baseline_only)}개')
    for f in sorted(baseline_only):
        display_name = f'{f[:60]}...' if len(f) > 60 else f
        print(f'    📍 {display_name}')


def print_performance_ranking(safe_files: Dict[str, Set[str]], method_files: Dict[str, Set[str]]):
    """성능 순위를 출력합니다."""
    print('\n📈 성능 순위:')
    methods_sorted = sorted(safe_files.keys(), key=lambda x: len(safe_files[x]), reverse=True)
    
    for i, method in enumerate(methods_sorted, 1):
        safe_count = len(safe_files[method])
        total_count = len(method_files[method])
        rate = (safe_count / total_count * 100) if total_count > 0 else 0
        
        # 순위별 이모지
        rank_emoji = ['🥇', '🥈', '🥉'][i-1] if i <= 3 else f'{i}위'
        print(f'  {rank_emoji} {method:12}: {safe_count}개 ({rate:4.1f}%)')


def save_comparison_result(safe_files: Dict[str, Set[str]], method_files: Dict[str, Set[str]], 
                          output_file: str):
    """비교 결과를 JSON 파일로 저장합니다."""
    comparison_result = {
        'summary': {
            'total_methods': len(safe_files),
            'comparison_date': '2025-11-02'
        },
        'statistics': {},
        'intersections': {},
        'unique_successes': {}
    }
    
    # 통계 정보
    for method in safe_files.keys():
        safe_count = len(safe_files[method])
        total_count = len(method_files[method])
        rate = (safe_count / total_count * 100) if total_count > 0 else 0
        
        comparison_result['statistics'][method] = {
            'safe_files': safe_count,
            'total_files': total_count,
            'safety_rate': round(rate, 1)
        }
    
    # 교집합 정보
    if all(method in safe_files for method in ['baseline', 'gha_repair', 'two_phase']):
        common_all = safe_files['baseline'] & safe_files['gha_repair'] & safe_files['two_phase']
        comparison_result['intersections'] = {
            'all_methods_safe': list(sorted(common_all)),
            'baseline_gha_repair': list(sorted(safe_files['baseline'] & safe_files['gha_repair'])),
            'baseline_two_phase': list(sorted(safe_files['baseline'] & safe_files['two_phase'])),
            'gha_repair_two_phase': list(sorted(safe_files['gha_repair'] & safe_files['two_phase']))
        }
    
    # 고유 성공 정보
    if all(method in safe_files for method in ['baseline', 'gha_repair', 'two_phase']):
        comparison_result['unique_successes'] = {
            'gha_repair_only': list(sorted(safe_files['gha_repair'] - safe_files['baseline'] - safe_files['two_phase'])),
            'two_phase_only': list(sorted(safe_files['two_phase'] - safe_files['baseline'] - safe_files['gha_repair'])),
            'baseline_only': list(sorted(safe_files['baseline'] - safe_files['gha_repair'] - safe_files['two_phase']))
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_result, f, indent=2, ensure_ascii=False)
    
    print(f'\n💾 비교 결과가 저장되었습니다: {output_file}')


def main():
    parser = argparse.ArgumentParser(description='3가지 GitHub Actions 수정 방법의 구조적 안전성 비교')
    parser.add_argument('--results-dir', default='results', 
                       help='검증 결과 파일들이 있는 디렉토리 (기본값: results)')
    parser.add_argument('--base-dir', default='..', 
                       help='데이터 디렉토리들의 기본 경로 (기본값: ..)')
    parser.add_argument('--output', default='results/methods_comparison.json',
                       help='비교 결과 저장 파일 (기본값: results/methods_comparison.json)')
    
    args = parser.parse_args()
    
    print('=' * 80)
    print('🎯 3가지 방법의 키 구조 검증 결과 종합 비교')
    print('=' * 80)
    
    # 검증 결과 로드
    results = load_verification_results(args.results_dir)
    if not results:
        print("❌ 검증 결과 파일을 찾을 수 없습니다.")
        return
    
    # 파일 목록 추출
    method_files = extract_method_files(args.base_dir)
    
    # 안전한 파일들 추출
    safe_files = extract_safe_files(results, method_files)
    
    # 분석 결과 출력
    print_statistics(safe_files, method_files)
    print_safe_files_by_method(safe_files)
    analyze_intersections(safe_files)
    analyze_unique_successes(safe_files)
    print_performance_ranking(safe_files, method_files)
    
    # 결과 저장
    save_comparison_result(safe_files, method_files, args.output)


if __name__ == '__main__':
    main()

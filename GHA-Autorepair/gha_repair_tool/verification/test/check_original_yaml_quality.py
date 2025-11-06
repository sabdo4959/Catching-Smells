#!/usr/bin/env python3
"""
원본 YAML 파일들의 구조적 품질을 분석하는 스크립트
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

def analyze_yaml_quality(file_path: str) -> Dict[str, Any]:
    """단일 YAML 파일의 품질을 분석"""
    result = {
        'file': os.path.basename(file_path),
        'size_bytes': 0,
        'line_count': 0,
        'parseable': False,
        'error_message': None
    }
    
    try:
        # 파일 크기와 라인 수 확인
        result['size_bytes'] = os.path.getsize(file_path)
        
        # 라인 수 계산
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                result['line_count'] = content.count('\n') + 1
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    result['line_count'] = content.count('\n') + 1
            except Exception as e:
                result['error_message'] = f"Encoding error: {str(e)}"
                return result
        
        # YAML 파싱 테스트
        yaml_parser = YAML()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml_parser.load(f)
            result['parseable'] = True
        except Exception as e:
            result['error_message'] = str(e)
            
    except Exception as e:
        result['error_message'] = f"File access error: {str(e)}"
        
    return result

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_original_yaml_quality.py <data_original_dir>")
        sys.exit(1)
        
    data_dir = sys.argv[1]
    
    if not os.path.exists(data_dir):
        print(f"Directory not found: {data_dir}")
        sys.exit(1)
        
    print("🔍 원본 YAML 파일 품질 분석 시작...")
    print("=" * 80)
    
    # 모든 YAML 파일 찾기
    yaml_files = []
    for file_name in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file_name)
        if os.path.isfile(file_path):
            yaml_files.append(file_path)
    
    if not yaml_files:
        print("No files found in directory")
        sys.exit(1)
        
    print(f"📁 총 {len(yaml_files)}개 파일 발견")
    print()
    
    # 분석 결과 저장
    results = []
    stats = {
        'total_files': len(yaml_files),
        'parseable_files': 0,
        'files_with_errors': 0,
        'zero_byte_files': 0,
        'small_files_under_100b': 0,
        'large_files_over_10kb': 0,
        'avg_file_size': 0,
        'avg_line_count': 0
    }
    
    # 각 파일 분석
    total_size = 0
    total_lines = 0
    
    for i, file_path in enumerate(yaml_files, 1):
        print(f"🔍 [{i}/{len(yaml_files)}] 분석 중: {os.path.basename(file_path)}")
        
        result = analyze_yaml_quality(file_path)
        results.append(result)
        
        # 통계 업데이트
        if result['parseable']:
            stats['parseable_files'] += 1
        if result['error_message']:
            stats['files_with_errors'] += 1
        if result['size_bytes'] == 0:
            stats['zero_byte_files'] += 1
        elif result['size_bytes'] < 100:
            stats['small_files_under_100b'] += 1
        elif result['size_bytes'] > 10240:  # 10KB
            stats['large_files_over_10kb'] += 1
            
        total_size += result['size_bytes']
        total_lines += result['line_count']
    
    # 평균 계산
    stats['avg_file_size'] = total_size // len(yaml_files) if yaml_files else 0
    stats['avg_line_count'] = total_lines // len(yaml_files) if yaml_files else 0
    
    print()
    print("=" * 80)
    print("📊 원본 YAML 파일 품질 분석 결과")
    print("=" * 80)
    
    # 기본 통계
    print(f"\n[1] 기본 통계:")
    print(f"전체 파일:          {stats['total_files']:3d}개")
    print(f"파싱 가능:          {stats['parseable_files']:3d}개 ({stats['parseable_files']/stats['total_files']*100:.1f}%)")
    print(f"파싱 오류:          {stats['files_with_errors']:3d}개 ({stats['files_with_errors']/stats['total_files']*100:.1f}%)")
    
    # 파일 크기 분포
    print(f"\n[2] 파일 크기 분포:")
    print(f"평균 파일 크기:     {stats['avg_file_size']:,} bytes")
    print(f"평균 라인 수:       {stats['avg_line_count']:,} lines")
    print(f"0 바이트:           {stats['zero_byte_files']:3d}개")
    print(f"100바이트 미만:     {stats['small_files_under_100b']:3d}개")
    print(f"10KB 초과:          {stats['large_files_over_10kb']:3d}개")
    
    # 오류가 있는 파일들 상세 출력
    problematic_files = [r for r in results if r['error_message']]
    
    if problematic_files:
        print(f"\n[3] 파싱 오류가 있는 파일들 ({len(problematic_files)}개):")
        print("-" * 80)
        
        for result in problematic_files[:10]:  # 최대 10개만 출력
            error_msg = result['error_message']
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            print(f"📄 {result['file']} ({result['size_bytes']} bytes, {result['line_count']} lines)")
            print(f"   ❌ {error_msg}")
            print()
                
        if len(problematic_files) > 10:
            print(f"... 및 {len(problematic_files) - 10}개 파일 더")
    
    # 성공적으로 파싱된 파일들
    successful_files = [r for r in results if r['parseable']]
    print(f"\n[4] 파싱 성공한 파일들:")
    print(f"성공적으로 파싱:     {len(successful_files):3d}개 ({len(successful_files)/stats['total_files']*100:.1f}%)")
    
    # 결과 JSON 파일로 저장
    output_file = "results/original_yaml_quality_analysis.json"
    os.makedirs("results", exist_ok=True)
    
    analysis_summary = {
        'statistics': stats,
        'detailed_results': results,
        'analysis_date': '2025-11-06',
        'directory_analyzed': data_dir
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 상세 분석 결과 저장: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()

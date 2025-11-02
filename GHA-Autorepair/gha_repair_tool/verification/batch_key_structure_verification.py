#!/usr/bin/env python3
"""
배치 키 구조 검증 스크립트
baseline과 gha_repair 결과의 구조적 안전성을 검증합니다.
"""

import os
import sys
from pathlib import Path
import json
from collections import defaultdict

# 이미 verification 폴더 안에 있으므로 직접 import
from key_structure_verifier import verify_structural_equivalence


def batch_key_structure_verification(original_dir, repair_dir, repair_type="unknown"):
    """
    배치 키 구조 검증을 수행합니다.
    
    Args:
        original_dir: 원본 파일 디렉토리
        repair_dir: 수정된 파일 디렉토리  
        repair_type: 수정 유형 (baseline, gha_repair 등)
    
    Returns:
        dict: 검증 결과 통계
    """
    print(f"\n{'='*80}")
    print(f"🔍 배치 키 구조 검증 시작: {repair_type}")
    print(f"   원본 디렉토리: {original_dir}")
    print(f"   수정 디렉토리: {repair_dir}")
    print(f"{'='*80}")
    
    original_path = Path(original_dir)
    repair_path = Path(repair_dir)
    
    if not original_path.exists():
        print(f"ERROR: 원본 디렉토리를 찾을 수 없습니다: {original_dir}")
        return None
    
    if not repair_path.exists():
        print(f"ERROR: 수정 디렉토리를 찾을 수 없습니다: {repair_dir}")
        return None
    
    # 수정된 파일 목록 가져오기
    repair_files = list(repair_path.glob("*"))
    repair_files = [f for f in repair_files if f.is_file() and f.suffix in ['.yml', '.yaml']]
    
    print(f"\n📊 검증 대상: {len(repair_files)}개 파일")
    
    results = {
        "total_files": 0,
        "safe_files": 0,
        "unsafe_files": 0,
        "error_files": 0,
        "safe_rate": 0.0,
        "unsafe_details": [],
        "error_details": []
    }
    
    safe_files = []
    unsafe_files = []
    error_files = []
    
    for i, repair_file in enumerate(repair_files, 1):
        # 원본 파일 찾기
        if repair_type == "baseline":
            # baseline: filename_baseline_repaired.yml -> filename
            original_name = repair_file.name.replace("_baseline_repaired.yml", "")
        elif repair_type == "gha_repair":
            # gha_repair: filename_gha_repaired.yml -> filename  
            original_name = repair_file.name.replace("_gha_repaired.yml", "")
        elif repair_type == "two_phase":
            # two_phase: filename_two_phase_repaired.yml -> filename
            original_name = repair_file.name.replace("_two_phase_repaired.yml", "")
        else:
            print(f"⚠️  알 수 없는 repair_type: {repair_type}")
            continue
        
        original_file = original_path / original_name
        
        if not original_file.exists():
            print(f"⚠️  [{i}/{len(repair_files)}] 원본 파일 없음: {original_name}")
            error_files.append(f"원본 파일 없음: {original_name}")
            continue
        
        print(f"🔍 [{i}/{len(repair_files)}] 검증 중: {original_name}")
        
        try:
            # 키 구조 검증 수행 (출력 억제)
            import io
            import contextlib
            
            # 출력을 캡처하여 화면에 표시하지 않음
            captured_output = io.StringIO()
            with contextlib.redirect_stdout(captured_output):
                is_safe = verify_structural_equivalence(original_file, repair_file)
            
            results["total_files"] += 1
            
            if is_safe:
                results["safe_files"] += 1
                safe_files.append(original_name)
                print(f"   ✅ 안전")
            else:
                results["unsafe_files"] += 1
                unsafe_files.append(original_name)
                results["unsafe_details"].append(original_name)
                print(f"   ❌ 안전하지 않음")
                
        except Exception as e:
            results["error_files"] += 1
            error_files.append(f"{original_name}: {str(e)}")
            results["error_details"].append(f"{original_name}: {str(e)}")
            print(f"   💥 오류: {str(e)}")
    
    # 결과 계산
    if results["total_files"] > 0:
        results["safe_rate"] = (results["safe_files"] / results["total_files"]) * 100
    
    # 결과 출력
    print(f"\n{'='*80}")
    print(f"📈 {repair_type} 키 구조 검증 결과")
    print(f"{'='*80}")
    print(f"전체 파일:     {results['total_files']:3d}개")
    print(f"구조적 안전:   {results['safe_files']:3d}개 ({results['safe_rate']:.1f}%)")
    print(f"구조적 위험:   {results['unsafe_files']:3d}개")
    print(f"검증 오류:     {results['error_files']:3d}개")
    
    if results["unsafe_files"] > 0:
        print(f"\n❌ 구조적으로 안전하지 않은 파일들:")
        for unsafe_file in results["unsafe_details"][:10]:  # 처음 10개만 표시
            print(f"   - {unsafe_file}")
        if len(results["unsafe_details"]) > 10:
            print(f"   ... 외 {len(results['unsafe_details']) - 10}개")
    
    if results["error_files"] > 0:
        print(f"\n💥 검증 오류 파일들:")
        for error_file in results["error_details"][:5]:  # 처음 5개만 표시
            print(f"   - {error_file}")
        if len(results["error_details"]) > 5:
            print(f"   ... 외 {len(results['error_details']) - 5}개")
    
    return results


def main():
    """메인 함수"""
    if len(sys.argv) != 4:
        print("사용법: python batch_key_structure_verification.py <original_dir> <repair_dir> <repair_type>")
        print("예시: python batch_key_structure_verification.py data_original data_repair_baseline baseline")
        sys.exit(1)
    
    original_dir = sys.argv[1]
    repair_dir = sys.argv[2]
    repair_type = sys.argv[3]
    
    results = batch_key_structure_verification(original_dir, repair_dir, repair_type)
    
    if results:
        # 결과를 JSON 파일로 저장
        output_file = f"key_structure_verification_{repair_type}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 결과가 저장되었습니다: {output_file}")


if __name__ == "__main__":
    main()

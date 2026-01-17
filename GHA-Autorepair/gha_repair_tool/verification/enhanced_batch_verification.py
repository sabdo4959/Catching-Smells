#!/usr/bin/env python3
"""
향상된 배치 키 구조 검증 도구

기존 키 구조 검증 + 구조적 값(needs, matrix 등) 검증을 모두 수행합니다.

Usage:
    python enhanced_batch_verification.py <original_dir> <repaired_dir> <method_name> [--mapping-csv CSV_PATH]
"""

import os
import sys
import json
import argparse
import csv
from pathlib import Path

try:
    from key_structure_verifier import KeyStructureVerifier
    from enhanced_key_structure_verifier import verify_enhanced_structural_equivalence
except ImportError as e:
    print(f"ERROR: 검증 모듈을 찾을 수 없습니다: {e}", file=sys.stderr)
    sys.exit(1)


def load_step_mapping(csv_path: str, source_step: str = "step1", target_step: str = "step2"):
    """
    all_steps.csv에서 스텝 간 파일명 매핑을 로드합니다.
    
    Args:
        csv_path: all_steps.csv 파일 경로
        source_step: 수정된 파일의 기준 스텝 (예: step1)
        target_step: 비교할 원본 파일의 스텝 (예: step2)
    
    Returns:
        dict: {source_hash: target_hash} 매핑
    """
    mapping = {}
    source_col = f"file_hash_{source_step}"
    target_col = f"file_hash_{target_step}"
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_hash = row.get(source_col, "").strip()
                target_hash = row.get(target_col, "").strip()
                if source_hash and target_hash:
                    mapping[source_hash] = target_hash
        
        print(f"✅ 매핑 정보 로드: {len(mapping)}개 ({source_step} → {target_step})")
        return mapping
    except Exception as e:
        print(f"⚠️ 매핑 파일 로드 실패: {e}")
        return {}


def run_enhanced_batch_verification(original_dir: str, repaired_dir: str, method_name: str, 
                                   step_mapping: dict = None):
    """향상된 배치 검증을 실행합니다."""
    
    print("=" * 80)
    print(f"🔍 향상된 배치 키 구조 검증 시작: {method_name}")
    print(f"   원본 디렉토리: {original_dir}")
    print(f"   수정 디렉토리: {repaired_dir}")
    if step_mapping:
        print(f"   스텝 매핑 적용: {len(step_mapping)}개")
    print("=" * 80)
    
    # 수정된 파일들 목록 가져오기
    repaired_files = []
    if os.path.exists(repaired_dir):
        for file in os.listdir(repaired_dir):
            if file.endswith('.yml'):
                repaired_files.append(file)
    
    if not repaired_files:
        print(f"❌ {repaired_dir}에서 수정된 파일을 찾을 수 없습니다.")
        return
    
    print(f"📊 검증 대상: {len(repaired_files)}개 파일")
    
    # 결과 저장용
    basic_verification_results = {
        "total_files": len(repaired_files),
        "basic_safe_files": 0,
        "basic_unsafe_files": 0,
        "basic_error_files": 0,
        "basic_safe_details": [],
        "basic_unsafe_details": [],
        "basic_error_details": []
    }
    
    enhanced_verification_results = {
        "total_files": len(repaired_files),
        "enhanced_safe_files": 0,
        "enhanced_unsafe_files": 0,
        "enhanced_error_files": 0,
        "enhanced_safe_details": [],
        "enhanced_unsafe_details": [],
        "enhanced_error_details": [],
        "structural_value_issues": []
    }
    
    basic_verifier = KeyStructureVerifier()
    
    # 각 파일 검증
    for i, repaired_file in enumerate(repaired_files, 1):
        # 원본 파일명 추출
        if method_name == "baseline":
            original_filename = repaired_file.replace("_baseline_repaired.yml", "")
        elif method_name == "gha_repair":
            original_filename = repaired_file.replace("_gha_repaired.yml", "")
        elif method_name == "two_phase":
            original_filename = repaired_file.replace("_two_phase_repaired.yml", "")
        else:
            print(f"❌ 알 수 없는 방법: {method_name}")
            return
        
        # 스텝 매핑이 있으면 매핑된 파일명 사용
        if step_mapping and original_filename in step_mapping:
            mapped_filename = step_mapping[original_filename]
            original_path = os.path.join(original_dir, mapped_filename)
            print(f"\n🔍 [{i}/{len(repaired_files)}] 검증 중: {original_filename} → {mapped_filename}")
        else:
            original_path = os.path.join(original_dir, original_filename)
            print(f"\n🔍 [{i}/{len(repaired_files)}] 검증 중: {original_filename}")
        repaired_path = os.path.join(repaired_dir, repaired_file)
        
        # 1. 기본 키 구조 검증
        try:
            is_basic_safe = basic_verifier.verify_key_structure(original_path, repaired_path)
            if is_basic_safe:
                basic_verification_results["basic_safe_files"] += 1
                basic_verification_results["basic_safe_details"].append(original_filename)
                print("   ✅ 기본 키 구조 안전")
            else:
                basic_verification_results["basic_unsafe_files"] += 1
                basic_verification_results["basic_unsafe_details"].append(original_filename)
                print("   ❌ 기본 키 구조 안전하지 않음")
        except Exception as e:
            basic_verification_results["basic_error_files"] += 1
            basic_verification_results["basic_error_details"].append(original_filename)
            print(f"   ERROR: 기본 검증 실패 - {str(e)}")
            is_basic_safe = False
        
        # 2. 향상된 구조 검증 (needs, matrix 등 포함)
        try:
            enhanced_result = verify_enhanced_structural_equivalence(
                Path(original_path), Path(repaired_path)
            )
            
            if enhanced_result["safe"]:
                enhanced_verification_results["enhanced_safe_files"] += 1
                enhanced_verification_results["enhanced_safe_details"].append(original_filename)
                print("   ✅ 향상된 구조 안전")
            else:
                enhanced_verification_results["enhanced_unsafe_files"] += 1
                enhanced_verification_results["enhanced_unsafe_details"].append(original_filename)
                
                # 구조적 값 문제가 있는 경우 별도 기록
                if enhanced_result["structural_value_issues"]:
                    enhanced_verification_results["structural_value_issues"].append({
                        "file": original_filename,
                        "issues": enhanced_result["structural_value_issues"]
                    })
                
                print(f"   ❌ 향상된 구조 안전하지 않음 ({enhanced_result['total_issues']}개 문제)")
                
        except Exception as e:
            enhanced_verification_results["enhanced_error_files"] += 1
            enhanced_verification_results["enhanced_error_details"].append(original_filename)
            print(f"   ERROR: 향상된 검증 실패 - {str(e)}")
        
        print()  # 빈 줄로 구분
    
    # 결과 출력
    print("=" * 80)
    print(f"📈 {method_name} 향상된 키 구조 검증 결과")
    print("=" * 80)
    
    print("\\n[1] 기본 키 구조 검증:")
    print(f"전체 파일:     {basic_verification_results['total_files']}개")
    print(f"구조적 안전:   {basic_verification_results['basic_safe_files']}개 ({basic_verification_results['basic_safe_files']/basic_verification_results['total_files']*100:.1f}%)")
    print(f"구조적 위험:   {basic_verification_results['basic_unsafe_files']}개")
    print(f"검증 오류:     {basic_verification_results['basic_error_files']}개")
    
    print("\\n[2] 향상된 구조 검증 (needs, matrix 포함):")
    print(f"전체 파일:     {enhanced_verification_results['total_files']}개")
    print(f"구조적 안전:   {enhanced_verification_results['enhanced_safe_files']}개 ({enhanced_verification_results['enhanced_safe_files']/enhanced_verification_results['total_files']*100:.1f}%)")
    print(f"구조적 위험:   {enhanced_verification_results['enhanced_unsafe_files']}개")
    print(f"검증 오류:     {enhanced_verification_results['enhanced_error_files']}개")
    
    # 구조적 값 문제 상세 출력
    if enhanced_verification_results["structural_value_issues"]:
        print("\\n[3] 구조적 값 문제 상세:")
        for item in enhanced_verification_results["structural_value_issues"]:
            print(f"📄 {item['file']}:")
            for issue in item['issues']:
                print(f"   - {issue}")
    
    # 결과 비교
    basic_safe = basic_verification_results['basic_safe_files']
    enhanced_safe = enhanced_verification_results['enhanced_safe_files']
    
    print("\\n[4] 검증 방법 비교:")
    print(f"기본 검증 안전:     {basic_safe}개")
    print(f"향상된 검증 안전:   {enhanced_safe}개")
    
    if enhanced_safe < basic_safe:
        print(f"🔍 향상된 검증이 {basic_safe - enhanced_safe}개 추가 문제 발견!")
        print("   (needs, matrix 등의 구조적 값 변경 감지)")
    elif enhanced_safe == basic_safe:
        print("✅ 두 검증 방법의 결과가 일치함")
    else:
        print("⚠️  예상치 못한 결과: 향상된 검증이 더 관대함")
    
    # JSON 결과 저장
    basic_output_file = f"results/key_structure_verification_{method_name}.json"
    enhanced_output_file = f"results/enhanced_key_structure_verification_{method_name}.json"
    
    # 기존 형식 유지 (호환성)
    basic_results_compatible = {
        "total_files": basic_verification_results["total_files"],
        "safe_files": basic_verification_results["basic_safe_files"],
        "unsafe_files": basic_verification_results["basic_unsafe_files"],
        "error_files": basic_verification_results["basic_error_files"],
        "safe_rate": basic_verification_results["basic_safe_files"] / basic_verification_results["total_files"] * 100,
        "safe_details": basic_verification_results["basic_safe_details"],
        "unsafe_details": basic_verification_results["basic_unsafe_details"]
    }
    
    with open(basic_output_file, 'w', encoding='utf-8') as f:
        json.dump(basic_results_compatible, f, indent=2, ensure_ascii=False)
    
    # 향상된 결과 저장
    enhanced_results_compatible = {
        "total_files": enhanced_verification_results["total_files"],
        "safe_files": enhanced_verification_results["enhanced_safe_files"],
        "unsafe_files": enhanced_verification_results["enhanced_unsafe_files"],
        "error_files": enhanced_verification_results["enhanced_error_files"],
        "safe_rate": enhanced_verification_results["enhanced_safe_files"] / enhanced_verification_results["total_files"] * 100,
        "safe_details": enhanced_verification_results["enhanced_safe_details"],
        "unsafe_details": enhanced_verification_results["enhanced_unsafe_details"],
        "structural_value_issues": enhanced_verification_results["structural_value_issues"]
    }
    
    with open(enhanced_output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_results_compatible, f, indent=2, ensure_ascii=False)
    
    print(f"\\n💾 기본 검증 결과 저장: {basic_output_file}")
    print(f"💾 향상된 검증 결과 저장: {enhanced_output_file}")


def main():
    parser = argparse.ArgumentParser(description='향상된 배치 키 구조 검증')
    parser.add_argument('original_dir', help='원본 파일 디렉토리')
    parser.add_argument('repaired_dir', help='수정된 파일 디렉토리')
    parser.add_argument('method_name', choices=['baseline', 'gha_repair', 'two_phase'],
                       help='수정 방법명')
    parser.add_argument('--mapping-csv', 
                       help='스텝 매핑 CSV 파일 경로 (예: all_steps.csv)',
                       default=None)
    parser.add_argument('--source-step',
                       help='수정된 파일의 기준 스텝 (기본값: step1)',
                       default='step1')
    parser.add_argument('--target-step',
                       help='비교할 원본 파일의 스텝 (기본값: step2)',
                       default='step2')
    
    args = parser.parse_args()
    
    # 스텝 매핑 로드
    step_mapping = None
    if args.mapping_csv:
        step_mapping = load_step_mapping(args.mapping_csv, args.source_step, args.target_step)
    
    run_enhanced_batch_verification(args.original_dir, args.repaired_dir, args.method_name, step_mapping)


if __name__ == "__main__":
    main()

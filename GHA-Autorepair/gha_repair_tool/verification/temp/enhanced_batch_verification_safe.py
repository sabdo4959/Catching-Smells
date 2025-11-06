#!/usr/bin/env python3
"""
향상된 일괄 검증 도구 (YAML 파싱 에러 무시 버전)
YAML 파싱이 실패하는 파일은 건너뛰고 검증 가능한 파일만 처리
"""

import os
import sys
from pathlib import Path
import yaml

# 현재 스크립트 위치를 기준으로 enhanced_key_structure_verifier 모듈 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from enhanced_key_structure_verifier import EnhancedKeyStructureVerifier, verify_enhanced_structural_equivalence

def can_parse_yaml(file_path):
    """YAML 파일이 파싱 가능한지 확인"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True
    except Exception:
        return False

def main():
    if len(sys.argv) != 4:
        print("사용법: python enhanced_batch_verification_safe.py <원본_디렉토리> <수정된_디렉토리> <모드>")
        print("모드: baseline, two-phase, gha-repair")
        sys.exit(1)
    
    original_dir = sys.argv[1]
    repaired_dir = sys.argv[2]
    repair_mode = sys.argv[3]
    
    if not os.path.exists(original_dir):
        print(f"❌ 원본 디렉토리가 존재하지 않습니다: {original_dir}")
        sys.exit(1)
    
    if not os.path.exists(repaired_dir):
        print(f"❌ 수정된 디렉토리가 존재하지 않습니다: {repaired_dir}")
        sys.exit(1)
    
    # 수정된 파일 목록 가져오기
    repaired_files = []
    for filename in os.listdir(repaired_dir):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            if repair_mode == "baseline" and "_baseline_repaired.yml" in filename:
                original_name = filename.replace("_baseline_repaired.yml", "")
                repaired_files.append((original_name, filename))
            elif repair_mode == "two-phase" and "_two_phase_repaired.yml" in filename:
                original_name = filename.replace("_two_phase_repaired.yml", "")
                repaired_files.append((original_name, filename))
            elif repair_mode == "gha-repair" and "_repaired.yml" in filename:
                original_name = filename.replace("_repaired.yml", "")
                repaired_files.append((original_name, filename))
    
    if not repaired_files:
        print(f"❌ {repaired_dir}에서 수정된 파일을 찾을 수 없습니다.")
        return
    
    print(f"📊 검증 대상: {len(repaired_files)}개 파일")
    
    # 결과 저장용
    basic_verification_results = {
        "total_files": len(repaired_files),
        "basic_safe_files": 0,
        "basic_unsafe_files": 0,
        "yaml_error_files": 0,
        "basic_safe_details": [],
        "basic_unsafe_details": [],
        "yaml_error_details": []
    }
    
    enhanced_verification_results = {
        "total_files": len(repaired_files),
        "enhanced_safe_files": 0,
        "enhanced_unsafe_files": 0,
        "yaml_error_files": 0,
        "enhanced_safe_details": [],
        "enhanced_unsafe_details": [],
        "yaml_error_details": []
    }
    
    # 검증 진행
    for i, (original_filename, repaired_filename) in enumerate(repaired_files, 1):
        original_path = os.path.join(original_dir, original_filename)
        repaired_path = os.path.join(repaired_dir, repaired_filename)
        
        print(f"\n[{i}/{len(repaired_files)}] 🔍 {original_filename}")
        
        # YAML 파싱 가능 여부 확인
        if not can_parse_yaml(original_path):
            print("   ❌ 원본 파일 YAML 파싱 실패 - 건너뜀")
            basic_verification_results["yaml_error_files"] += 1
            basic_verification_results["yaml_error_details"].append(original_filename)
            enhanced_verification_results["yaml_error_files"] += 1
            enhanced_verification_results["yaml_error_details"].append(original_filename)
            continue
            
        if not can_parse_yaml(repaired_path):
            print("   ❌ 수정된 파일 YAML 파싱 실패 - 건너뜀")
            basic_verification_results["yaml_error_files"] += 1
            basic_verification_results["yaml_error_details"].append(original_filename)
            enhanced_verification_results["yaml_error_files"] += 1
            enhanced_verification_results["yaml_error_details"].append(original_filename)
            continue
        
        # 1. 기본 구조 검증
        try:
            verification_tool = EnhancedKeyStructureVerifier()
            basic_result = verification_tool.verify_key_structure(original_path, repaired_path)
            
            if basic_result["safe"]:
                basic_verification_results["basic_safe_files"] += 1
                basic_verification_results["basic_safe_details"].append(original_filename)
                print("   ✅ 기본 구조 안전")
            else:
                basic_verification_results["basic_unsafe_files"] += 1
                basic_verification_results["basic_unsafe_details"].append(original_filename)
                print("   ❌ 기본 구조 위험")
                if basic_result.get("details"):
                    for detail in basic_result["details"][:3]:  # 최대 3개만 출력
                        print(f"      - {detail}")
        except Exception as e:
            print(f"   ❌ 기본 검증 실패 - {str(e)}")
            basic_verification_results["yaml_error_files"] += 1
            basic_verification_results["yaml_error_details"].append(original_filename)
        
        # 2. 향상된 구조 검증
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
                print("   ❌ 향상된 구조 위험")
                if enhanced_result.get("details"):
                    for detail in enhanced_result["details"][:3]:  # 최대 3개만 출력
                        print(f"      - {detail}")
        except Exception as e:
            print(f"   ❌ 향상된 검증 실패 - {str(e)}")
            enhanced_verification_results["yaml_error_files"] += 1
            enhanced_verification_results["yaml_error_details"].append(original_filename)
    
    # 결과 요약 출력
    print(f"\n{'='*60}")
    print(f"🎯 {repair_mode.upper()} 모드 검증 결과 요약")
    print(f"{'='*60}")
    
    total_processed = (basic_verification_results["basic_safe_files"] + 
                      basic_verification_results["basic_unsafe_files"])
    yaml_errors = basic_verification_results["yaml_error_files"]
    
    print(f"📊 전체 파일: {basic_verification_results['total_files']}개")
    print(f"📊 처리된 파일: {total_processed}개")
    print(f"❌ YAML 에러: {yaml_errors}개")
    
    print(f"\n🔍 기본 검증 결과:")
    print(f"   ✅ 안전: {basic_verification_results['basic_safe_files']}개")
    print(f"   ❌ 위험: {basic_verification_results['basic_unsafe_files']}개")
    if total_processed > 0:
        basic_safety_rate = (basic_verification_results['basic_safe_files'] / total_processed) * 100
        print(f"   📈 안전률: {basic_safety_rate:.1f}%")
    
    total_enhanced = (enhanced_verification_results["enhanced_safe_files"] + 
                     enhanced_verification_results["enhanced_unsafe_files"])
    
    print(f"\n🔍 향상된 검증 결과:")
    print(f"   ✅ 안전: {enhanced_verification_results['enhanced_safe_files']}개")
    print(f"   ❌ 위험: {enhanced_verification_results['enhanced_unsafe_files']}개")
    if total_enhanced > 0:
        enhanced_safety_rate = (enhanced_verification_results['enhanced_safe_files'] / total_enhanced) * 100
        print(f"   📈 안전률: {enhanced_safety_rate:.1f}%")
    
    if basic_verification_results['basic_unsafe_files'] > 0:
        print(f"\n❌ 기본 검증 위험 파일들:")
        for filename in basic_verification_results['basic_unsafe_details'][:10]:  # 최대 10개만 표시
            print(f"   - {filename}")
    
    if enhanced_verification_results['enhanced_unsafe_files'] > 0:
        print(f"\n❌ 향상된 검증 위험 파일들:")
        for filename in enhanced_verification_results['enhanced_unsafe_details'][:10]:  # 최대 10개만 표시
            print(f"   - {filename}")

if __name__ == "__main__":
    main()

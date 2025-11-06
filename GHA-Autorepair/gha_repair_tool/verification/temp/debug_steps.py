#!/usr/bin/env python3
"""
Debug script for step order verification
"""

import yaml
import json

def _extract_step_identities(steps):
    identities = []
    
    for step in steps:
        # Step 타입 결정: uses vs run vs name 기반 식별
        if 'uses' in step:
            # uses step은 action 이름의 prefix만 사용 (버전 제외)
            uses_value = step['uses']
            action_name = uses_value.split('@')[0] if '@' in uses_value else uses_value
            identity = f"uses:{action_name}"
        elif 'run' in step:
            # run step은 name이 있으면 name만 사용 (run 값은 무시)
            if 'name' in step:
                identity = f"run:{step['name']}"
            else:
                # name이 없으면 step의 키 구조로 식별 (run 값은 제외)
                keys_without_run = [k for k in step.keys() if k not in ['run', 'timeout-minutes']]
                identity = f"run:keys:{'-'.join(sorted(keys_without_run))}"
        else:
            # 기타 step은 키 조합 사용
            identity = f"other:{'-'.join(sorted(step.keys()))}"
        
        identities.append(identity)
    
    return identities

def debug_steps_reordered(orig_steps, repaired_steps):
    """Steps가 순서 변경되었는지 확인 (값 변경과 구별) - 디버그 버전"""
    print(f"DEBUG: 원본 steps 수: {len(orig_steps)}, 수정된 steps 수: {len(repaired_steps)}")
    
    if len(orig_steps) != len(repaired_steps):
        print("DEBUG: 길이가 다름 - False 반환")
        return False
    
    # 1. 위치별 비교
    for i, (orig_step, repaired_step) in enumerate(zip(orig_steps, repaired_steps)):
        print(f"\nDEBUG: Step {i} 비교")
        
        # permissions 필드와 timeout-minutes는 예외 처리
        orig_keys_filtered = tuple(sorted([k for k in orig_step.keys() if k not in ['permissions', 'timeout-minutes']]))
        repaired_keys_filtered = tuple(sorted([k for k in repaired_step.keys() if k not in ['permissions', 'timeout-minutes']]))
        
        print(f"  원본 키: {orig_keys_filtered}")
        print(f"  수정된 키: {repaired_keys_filtered}")
        
        # 예외 필드를 제외한 키 구조가 다르면 순서가 바뀐 것
        if orig_keys_filtered != repaired_keys_filtered:
            print("  키 구조가 다름 - True 반환")
            return True
        
        # 키 구조가 같은 경우, 주요 식별자 비교
        orig_step_for_comparison = {}
        repaired_step_for_comparison = {}
        
        # 값 변경을 허용할 키들
        value_change_allowed_keys = ['run', 'uses', 'permissions', 'timeout-minutes']
        
        for key, value in orig_step.items():
            if key not in value_change_allowed_keys:
                orig_step_for_comparison[key] = value
                
        for key, value in repaired_step.items():
            if key not in value_change_allowed_keys:
                repaired_step_for_comparison[key] = value
        
        # JSON 비교
        orig_json = json.dumps(orig_step_for_comparison, sort_keys=True, default=str)
        repaired_json = json.dumps(repaired_step_for_comparison, sort_keys=True, default=str)
        
        print(f"  원본 JSON: {orig_json}")
        print(f"  수정된 JSON: {repaired_json}")
        print(f"  JSON 같은가: {orig_json == repaired_json}")
        
        if orig_json != repaired_json:
            print("  JSON이 다름 - True 반환")
            return True
    
    print("\nDEBUG: 모든 위치별 비교 통과")
    
    # 3. Step 정체성 기반 검사
    orig_identities = _extract_step_identities(orig_steps)
    repaired_identities = _extract_step_identities(repaired_steps)
    
    print(f"원본 identities: {orig_identities}")
    print(f"수정된 identities: {repaired_identities}")
    print(f"Set 같은가: {set(orig_identities) == set(repaired_identities)}")
    print(f"순서 같은가: {orig_identities == repaired_identities}")
    
    # 같은 step들이 다른 순서로 나타나면 순서 변경
    if set(orig_identities) == set(repaired_identities) and orig_identities != repaired_identities:
        print("DEBUG: Identity set은 같지만 순서가 다름 - True 반환")
        return True
    
    print("DEBUG: 모든 검사 통과 - False 반환")
    return False

if __name__ == "__main__":
    # 원본 파일 로드
    with open('../data_original/eda4becd286010436a22854c03c251fe68585622868a4c32b2674bbe2fb3f520', 'r', encoding='utf-8') as f:
        orig = yaml.safe_load(f)

    # 수정된 파일 로드  
    with open('../data_repair_baseline/eda4becd286010436a22854c03c251fe68585622868a4c32b2674bbe2fb3f520_baseline_repaired.yml', 'r', encoding='utf-8') as f:
        repaired = yaml.safe_load(f)

    orig_steps = orig['jobs']['test_linux']['steps']
    repaired_steps = repaired['jobs']['test_linux']['steps']

    result = debug_steps_reordered(orig_steps, repaired_steps)
    print(f"\n최종 결과: {result}")

#!/usr/bin/env python3
"""
YAML 구조 차이점 분석 도구

두 개의 GitHub Actions YAML 파일을 비교하여 구조적 차이점을 상세히 분석합니다.
"""

import sys
import yaml
from pathlib import Path
from deepdiff import DeepDiff
from pprint import pprint
import argparse

try:
    from parser import GHAWorkflowParser
except ImportError:
    print("WARNING: parser.py를 찾을 수 없습니다. 기본 yaml.safe_load를 사용합니다.", file=sys.stderr)
    GHAWorkflowParser = None


class YAMLDiffAnalyzer:
    """YAML 구조 차이점 분석기"""
    
    def __init__(self):
        self.parser = GHAWorkflowParser() if GHAWorkflowParser else None
    
    def load_yaml(self, file_path):
        """YAML 파일을 로드합니다."""
        try:
            if self.parser:
                return self.parser.parse(Path(file_path))
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"ERROR: {file_path} 로드 실패: {e}", file=sys.stderr)
            return None
    
    def analyze_timeout_changes(self, original, repaired):
        """timeout-minutes 변경사항을 분석합니다."""
        print("\n🔍 === timeout-minutes 변경사항 분석 ===")
        
        print("\n[원본 파일에서 timeout-minutes 위치]")
        original_timeouts = self._find_timeouts(original, "원본")
        
        print("\n[수리된 파일에서 timeout-minutes 위치]")
        repaired_timeouts = self._find_timeouts(repaired, "수리됨")
        
        # 변경사항 요약
        if original_timeouts != repaired_timeouts:
            print("\n⚠️ timeout-minutes 위치/값 변경 감지!")
            print("변경 유형:")
            
            # 제거된 timeout
            removed = set(original_timeouts.keys()) - set(repaired_timeouts.keys())
            if removed:
                print(f"  ❌ 제거됨: {list(removed)}")
            
            # 추가된 timeout
            added = set(repaired_timeouts.keys()) - set(original_timeouts.keys())
            if added:
                print(f"  ✅ 추가됨: {list(added)}")
            
            # 값이 변경된 timeout
            for key in set(original_timeouts.keys()) & set(repaired_timeouts.keys()):
                if original_timeouts[key] != repaired_timeouts[key]:
                    print(f"  🔄 값 변경: {key} ({original_timeouts[key]} → {repaired_timeouts[key]})")
        else:
            print("\n✅ timeout-minutes 변경사항 없음")
    
    def _find_timeouts(self, data, label):
        """YAML 데이터에서 모든 timeout-minutes를 찾습니다."""
        timeouts = {}
        
        if not data or 'jobs' not in data:
            return timeouts
        
        for job_name, job_data in data['jobs'].items():
            if isinstance(job_data, dict):
                # Job 레벨 timeout
                if 'timeout-minutes' in job_data:
                    key = f"jobs.{job_name}.timeout-minutes"
                    value = job_data['timeout-minutes']
                    timeouts[key] = value
                    print(f"  - {key}: {value}")
                
                # Step 레벨 timeout
                if 'steps' in job_data and isinstance(job_data['steps'], list):
                    for i, step in enumerate(job_data['steps']):
                        if isinstance(step, dict) and 'timeout-minutes' in step:
                            key = f"jobs.{job_name}.steps[{i}].timeout-minutes"
                            value = step['timeout-minutes']
                            timeouts[key] = value
                            print(f"  - {key}: {value}")
        
        if not timeouts:
            print("  (timeout-minutes 없음)")
        
        return timeouts
    
    def analyze_key_structure_changes(self, original, repaired):
        """키 구조 변경사항을 분석합니다."""
        print("\n🔍 === 키 구조 변경사항 분석 ===")
        
        diff = DeepDiff(original, repaired, ignore_order=False)
        
        if not diff:
            print("✅ 구조적 차이점 없음")
            return
        
        for change_type, changes in diff.items():
            print(f"\n📍 {change_type}:")
            
            if change_type == 'dictionary_item_added':
                for path in changes:
                    print(f"  ✅ 추가된 키: {path}")
            
            elif change_type == 'dictionary_item_removed':
                for path in changes:
                    print(f"  ❌ 제거된 키: {path}")
            
            elif change_type == 'values_changed':
                for path, details in changes.items():
                    old_val = str(details['old_value'])[:100]
                    new_val = str(details['new_value'])[:100]
                    print(f"  🔄 값 변경: {path}")
                    print(f"      이전: {old_val}{'...' if len(str(details['old_value'])) > 100 else ''}")
                    print(f"      이후: {new_val}{'...' if len(str(details['new_value'])) > 100 else ''}")
            
            elif change_type == 'type_changes':
                for path, details in changes.items():
                    print(f"  🔄 타입 변경: {path}")
                    print(f"      이전 타입: {details['old_type']}")
                    print(f"      이후 타입: {details['new_type']}")
            
            elif change_type == 'iterable_item_added':
                for path, items in changes.items():
                    print(f"  ✅ 리스트 항목 추가: {path}")
                    for item in items:
                        print(f"      {item}")
            
            elif change_type == 'iterable_item_removed':
                for path, items in changes.items():
                    print(f"  ❌ 리스트 항목 제거: {path}")
                    for item in items:
                        print(f"      {item}")
            
            else:
                print(f"  기타 변경: {changes}")
    
    def analyze_step_order_changes(self, original, repaired):
        """Step 순서 변경사항을 분석합니다."""
        print("\n🔍 === Step 순서 변경사항 분석 ===")
        
        if not original or not repaired or 'jobs' not in original or 'jobs' not in repaired:
            print("❌ Jobs 정보가 없어 분석할 수 없습니다.")
            return
        
        for job_name in set(original.get('jobs', {}).keys()) | set(repaired.get('jobs', {}).keys()):
            orig_job = original.get('jobs', {}).get(job_name, {})
            repr_job = repaired.get('jobs', {}).get(job_name, {})
            
            orig_steps = orig_job.get('steps', [])
            repr_steps = repr_job.get('steps', [])
            
            if len(orig_steps) != len(repr_steps):
                print(f"⚠️ {job_name}: Step 개수 변경 ({len(orig_steps)} → {len(repr_steps)})")
            
            # Step 이름 기준으로 순서 확인
            orig_names = [step.get('name', f'step_{i}') for i, step in enumerate(orig_steps) if isinstance(step, dict)]
            repr_names = [step.get('name', f'step_{i}') for i, step in enumerate(repr_steps) if isinstance(step, dict)]
            
            if orig_names != repr_names:
                print(f"⚠️ {job_name}: Step 순서 또는 내용 변경")
                print(f"    원본 steps: {orig_names}")
                print(f"    수리 steps: {repr_names}")
            else:
                print(f"✅ {job_name}: Step 순서 유지")
    
    def analyze_structural_safety(self, original_file, repaired_file):
        """두 파일의 구조적 안전성을 종합 분석합니다."""
        print("=" * 80)
        print(f"🔬 YAML 구조 차이점 분석")
        print(f"🔬 원본: {Path(original_file).name}")
        print(f"🔬 수리됨: {Path(repaired_file).name}")
        print("=" * 80)
        
        # 파일 로드
        original = self.load_yaml(original_file)
        repaired = self.load_yaml(repaired_file)
        
        if original is None or repaired is None:
            print("❌ 파일 로드 실패로 분석을 중단합니다.")
            return False
        
        # 각종 분석 실행
        self.analyze_timeout_changes(original, repaired)
        self.analyze_key_structure_changes(original, repaired)
        self.analyze_step_order_changes(original, repaired)
        
        print("\n" + "=" * 80)
        print("📋 분석 완료")
        print("=" * 80)
        
        return True


def main():
    parser = argparse.ArgumentParser(description='YAML 파일 구조 차이점 분석')
    parser.add_argument('original', help='원본 YAML 파일 경로')
    parser.add_argument('repaired', help='수리된 YAML 파일 경로')
    
    args = parser.parse_args()
    
    analyzer = YAMLDiffAnalyzer()
    analyzer.analyze_structural_safety(args.original, args.repaired)


if __name__ == "__main__":
    main()

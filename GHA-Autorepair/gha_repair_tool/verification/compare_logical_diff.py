#!/usr/bin/env python3
"""
GitHub Actions 워크플로우 논리적 차이점 비교 도구

이 도구는 원본과 수정된 워크플로우 파일 간의 논리적 차이점을 상세히 분석합니다.
기존 LogicalVerifier가 놓치고 있는 run 명령어, 변수 참조 등도 포함해서 검증합니다.
"""

import yaml
import argparse
import sys
import re
from typing import Dict, Any, List, Tuple, Set
from pathlib import Path
import difflib


class ComprehensiveLogicalDiffer:
    """포괄적인 논리적 차이점 분석기"""
    
    def __init__(self):
        self.differences = []
        self.warnings = []
        self.github_vars_pattern = re.compile(r'\$\{\{\s*([^}]+)\s*\}\}')
    
    def compare_files(self, original_path: str, repaired_path: str) -> Dict[str, Any]:
        """두 워크플로우 파일을 비교하여 논리적 차이점을 분석"""
        
        print(f"🔍 논리적 차이점 분석")
        print(f"원본: {original_path}")
        print(f"수정: {repaired_path}")
        print("=" * 70)
        
        # 파일 내용 읽기
        try:
            with open(original_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            with open(repaired_path, 'r', encoding='utf-8') as f:
                repaired_content = f.read()
        except Exception as e:
            return {"error": f"파일 읽기 실패: {e}"}
        
        # YAML 파싱 시도
        try:
            original_yaml = yaml.safe_load(original_content)
            repaired_yaml = yaml.safe_load(repaired_content)
        except yaml.YAMLError as e:
            print(f"⚠️  YAML 파싱 오류: {e}")
            print("원본 텍스트로 비교를 계속합니다...")
            return self._compare_as_text(original_content, repaired_content)
        
        # 포괄적 비교 수행
        result = {
            "trigger_changes": self._compare_triggers(original_yaml, repaired_yaml),
            "job_changes": self._compare_jobs(original_yaml, repaired_yaml),
            "step_changes": self._compare_steps(original_yaml, repaired_yaml),
            "variable_changes": self._compare_variables(original_content, repaired_content),
            "env_changes": self._compare_env_vars(original_yaml, repaired_yaml),
            "is_logically_equivalent": False,  # 기본값
            "summary": [],
            "critical_differences": [],
            "minor_differences": []
        }
        
        # 전체 분석 결과 종합
        self._analyze_overall_equivalence(result)
        
        return result
    
    def _compare_triggers(self, original: Dict, repaired: Dict) -> Dict[str, Any]:
        """트리거 조건 (on) 비교"""
        print("\n📋 1. 트리거 조건 (on) 분석")
        
        orig_on = original.get('on', {})
        rep_on = repaired.get('on', {})
        
        changes = {
            "identical": False,
            "changes": [],
            "critical": False
        }
        
        if orig_on == rep_on:
            print("   ✅ 트리거 조건 동일")
            changes["identical"] = True
            return changes
        
        # 세부 트리거 비교
        for trigger_type in set(list(orig_on.keys()) + list(rep_on.keys())):
            orig_trigger = orig_on.get(trigger_type, {})
            rep_trigger = rep_on.get(trigger_type, {})
            
            if orig_trigger != rep_trigger:
                change_desc = f"'{trigger_type}' 트리거 변경"
                
                # if 조건 추가/변경 감지
                if isinstance(rep_trigger, dict) and 'if' in rep_trigger:
                    if not isinstance(orig_trigger, dict) or 'if' not in orig_trigger:
                        change_desc += f" (if 조건 추가: {rep_trigger['if']})"
                        changes["critical"] = True
                    elif orig_trigger['if'] != rep_trigger['if']:
                        change_desc += f" (if 조건 변경: {orig_trigger['if']} → {rep_trigger['if']})"
                        changes["critical"] = True
                
                changes["changes"].append(change_desc)
                print(f"   ⚠️  {change_desc}")
        
        return changes
    
    def _compare_jobs(self, original: Dict, repaired: Dict) -> Dict[str, Any]:
        """Job 레벨 비교"""
        print("\n🏗️  2. Job 구조 분석")
        
        orig_jobs = original.get('jobs', {})
        rep_jobs = repaired.get('jobs', {})
        
        changes = {
            "job_count_change": len(orig_jobs) != len(rep_jobs),
            "added_jobs": list(set(rep_jobs.keys()) - set(orig_jobs.keys())),
            "removed_jobs": list(set(orig_jobs.keys()) - set(rep_jobs.keys())),
            "modified_jobs": [],
            "critical": False
        }
        
        print(f"   원본 Job 수: {len(orig_jobs)}")
        print(f"   수정 Job 수: {len(rep_jobs)}")
        
        if changes["added_jobs"]:
            print(f"   ➕ 추가된 Job: {changes['added_jobs']}")
            changes["critical"] = True
            
        if changes["removed_jobs"]:
            print(f"   ➖ 제거된 Job: {changes['removed_jobs']}")
            changes["critical"] = True
        
        # 공통 Job들의 변경사항 확인
        common_jobs = set(orig_jobs.keys()) & set(rep_jobs.keys())
        for job_id in common_jobs:
            job_changes = self._compare_single_job(orig_jobs[job_id], rep_jobs[job_id], job_id)
            if job_changes["has_changes"]:
                changes["modified_jobs"].append({
                    "job_id": job_id,
                    "changes": job_changes
                })
                if job_changes["critical"]:
                    changes["critical"] = True
        
        return changes
    
    def _compare_single_job(self, orig_job: Dict, rep_job: Dict, job_id: str) -> Dict[str, Any]:
        """단일 Job 비교"""
        changes = {
            "has_changes": False,
            "critical": False,
            "changes": []
        }
        
        # 주요 Job 속성 비교
        important_attrs = ['runs-on', 'if', 'needs', 'environment', 'timeout-minutes']
        
        for attr in important_attrs:
            orig_val = orig_job.get(attr)
            rep_val = rep_job.get(attr)
            
            if orig_val != rep_val:
                changes["has_changes"] = True
                change_desc = f"{attr}: {orig_val} → {rep_val}"
                changes["changes"].append(change_desc)
                print(f"   🔄 Job '{job_id}' {change_desc}")
                
                # if 조건이나 needs 변경은 critical
                if attr in ['if', 'needs']:
                    changes["critical"] = True
        
        return changes
    
    def _compare_steps(self, original: Dict, repaired: Dict) -> Dict[str, Any]:
        """Steps 비교 (run 명령어 포함)"""
        print("\n🔧 3. Steps 및 run 명령어 분석")
        
        orig_jobs = original.get('jobs', {})
        rep_jobs = repaired.get('jobs', {})
        
        changes = {
            "step_structure_changes": [],
            "run_command_changes": [],
            "critical": False
        }
        
        # 공통 Job들의 Steps 비교
        common_jobs = set(orig_jobs.keys()) & set(rep_jobs.keys())
        
        for job_id in common_jobs:
            orig_steps = orig_jobs[job_id].get('steps', [])
            rep_steps = rep_jobs[job_id].get('steps', [])
            
            print(f"\n   Job '{job_id}':")
            print(f"   - 원본 Steps 수: {len(orig_steps)}")
            print(f"   - 수정 Steps 수: {len(rep_steps)}")
            
            # Steps 수 변경
            if len(orig_steps) != len(rep_steps):
                change_desc = f"Job '{job_id}': Steps 수 변경 ({len(orig_steps)} → {len(rep_steps)})"
                changes["step_structure_changes"].append(change_desc)
                changes["critical"] = True
                print(f"   ⚠️  {change_desc}")
            
            # 개별 Step 비교
            min_steps = min(len(orig_steps), len(rep_steps))
            for i in range(min_steps):
                step_changes = self._compare_single_step(orig_steps[i], rep_steps[i], job_id, i)
                
                if step_changes["run_changed"]:
                    changes["run_command_changes"].append(step_changes)
                    
                if step_changes["critical"]:
                    changes["critical"] = True
        
        return changes
    
    def _compare_single_step(self, orig_step: Dict, rep_step: Dict, job_id: str, step_idx: int) -> Dict[str, Any]:
        """단일 Step 비교"""
        changes = {
            "job_id": job_id,
            "step_index": step_idx,
            "run_changed": False,
            "critical": False,
            "changes": []
        }
        
        # run 명령어 비교
        orig_run = orig_step.get('run', '')
        rep_run = rep_step.get('run', '')
        
        if orig_run != rep_run:
            changes["run_changed"] = True
            changes["changes"].append(f"run 명령어 변경")
            print(f"   🔄 Step {step_idx}: run 명령어 변경")
            print(f"      원본: {orig_run[:50]}{'...' if len(orig_run) > 50 else ''}")
            print(f"      수정: {rep_run[:50]}{'...' if len(rep_run) > 50 else ''}")
            
            # 변수 참조 변경 감지
            orig_vars = self._extract_github_variables(orig_run)
            rep_vars = self._extract_github_variables(rep_run)
            
            if orig_vars != rep_vars:
                changes["critical"] = True
                var_changes = {
                    "added": rep_vars - orig_vars,
                    "removed": orig_vars - rep_vars
                }
                changes["variable_changes"] = var_changes
                print(f"      📊 변수 참조 변경: 제거={var_changes['removed']}, 추가={var_changes['added']}")
        
        # 기타 중요 속성 비교
        important_attrs = ['if', 'uses', 'with', 'env']
        for attr in important_attrs:
            if orig_step.get(attr) != rep_step.get(attr):
                changes["changes"].append(f"{attr} 변경")
                if attr == 'if':
                    changes["critical"] = True
        
        return changes
    
    def _compare_variables(self, original_content: str, repaired_content: str) -> Dict[str, Any]:
        """GitHub 변수 참조 비교"""
        print("\n📊 4. GitHub 변수 참조 분석")
        
        orig_vars = self._extract_github_variables(original_content)
        rep_vars = self._extract_github_variables(repaired_content)
        
        changes = {
            "added_variables": list(rep_vars - orig_vars),
            "removed_variables": list(orig_vars - rep_vars),
            "critical": False
        }
        
        if changes["added_variables"]:
            print(f"   ➕ 추가된 변수: {changes['added_variables']}")
            
        if changes["removed_variables"]:
            print(f"   ➖ 제거된 변수: {changes['removed_variables']}")
            changes["critical"] = True
            
        if not changes["added_variables"] and not changes["removed_variables"]:
            print("   ✅ 변수 참조 동일")
        
        return changes
    
    def _compare_env_vars(self, original: Dict, repaired: Dict) -> Dict[str, Any]:
        """환경변수 비교"""
        print("\n🌍 5. 환경변수 분석")
        
        changes = {
            "global_env_changed": False,
            "job_env_changes": [],
            "step_env_changes": [],
            "critical": False
        }
        
        # 전역 환경변수
        orig_env = original.get('env', {})
        rep_env = repaired.get('env', {})
        
        if orig_env != rep_env:
            changes["global_env_changed"] = True
            print(f"   🔄 전역 환경변수 변경")
            
        # Job별 환경변수는 여기서는 생략 (필요시 추가)
        
        if not changes["global_env_changed"]:
            print("   ✅ 환경변수 동일")
            
        return changes
    
    def _extract_github_variables(self, content: str) -> Set[str]:
        """GitHub 표현식에서 변수 추출 (${{ ... }})"""
        matches = self.github_vars_pattern.findall(content)
        # 공백 제거 및 정규화
        variables = {match.strip() for match in matches}
        return variables
    
    def _compare_as_text(self, original_content: str, repaired_content: str) -> Dict[str, Any]:
        """YAML 파싱 실패시 텍스트로 비교"""
        print("\n📝 텍스트 기반 비교 (YAML 파싱 실패)")
        
        # 간단한 텍스트 차이점 표시
        diff = list(difflib.unified_diff(
            original_content.splitlines(keepends=True),
            repaired_content.splitlines(keepends=True),
            fromfile='원본',
            tofile='수정본',
            n=3
        ))
        
        # GitHub 변수 비교
        orig_vars = self._extract_github_variables(original_content)
        rep_vars = self._extract_github_variables(repaired_content)
        
        return {
            "parsing_failed": True,
            "text_diff": diff,
            "variable_changes": {
                "added_variables": list(rep_vars - orig_vars),
                "removed_variables": list(orig_vars - rep_vars)
            },
            "is_logically_equivalent": False
        }
    
    def _analyze_overall_equivalence(self, result: Dict[str, Any]) -> None:
        """전체 논리적 동치성 판단"""
        print("\n" + "=" * 70)
        print("📋 전체 분석 결과")
        
        critical_issues = []
        minor_issues = []
        
        # 각 영역별 critical 여부 확인
        if result["trigger_changes"]["critical"]:
            critical_issues.append("트리거 조건 변경")
            
        if result["job_changes"]["critical"]:
            critical_issues.append("Job 구조 변경")
            
        if result["step_changes"]["critical"]:
            critical_issues.append("Steps/run 명령어 변경")
            
        if result["variable_changes"]["critical"]:
            critical_issues.append("변수 참조 변경")
        
        # 결론 도출
        if critical_issues:
            print("❌ 논리적으로 동치가 아님")
            print(f"🚨 Critical 이슈: {', '.join(critical_issues)}")
            result["is_logically_equivalent"] = False
            result["critical_differences"] = critical_issues
        else:
            print("✅ 논리적으로 동치함 (또는 허용 가능한 수정)")
            result["is_logically_equivalent"] = True
        
        result["summary"] = critical_issues + minor_issues
        print("=" * 70)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='GitHub Actions 워크플로우 논리적 차이 분석')
    parser.add_argument('original', help='원본 워크플로우 파일 경로')
    parser.add_argument('repaired', help='수정된 워크플로우 파일 경로')
    parser.add_argument('--output', '-o', help='결과를 JSON으로 저장할 파일 경로')
    
    args = parser.parse_args()
    
    # 파일 존재 확인
    if not Path(args.original).exists():
        print(f"❌ 원본 파일을 찾을 수 없습니다: {args.original}")
        sys.exit(1)
        
    if not Path(args.repaired).exists():
        print(f"❌ 수정 파일을 찾을 수 없습니다: {args.repaired}")
        sys.exit(1)
    
    # 비교 실행
    differ = ComprehensiveLogicalDiffer()
    result = differ.compare_files(args.original, args.repaired)
    
    # 결과 저장
    if args.output:
        import json
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 결과가 저장되었습니다: {args.output}")


if __name__ == "__main__":
    main()

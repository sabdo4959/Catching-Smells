#!/usr/bin/env python3
"""
향상된 키 구조 검증 결과 요약 분석기
"""

import re
import sys
from pathlib import Path

def parse_enhanced_verification_log(log_file_path):
    """향상된 검증 로그에서 결과 추출"""
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 최종 결과 섹션 찾기
    summary_match = re.search(r'📈 gha_repair 향상된 키 구조 검증 결과.*?(?=Traceback|$)', content, re.DOTALL)
    
    if not summary_match:
        print("❌ 결과 요약을 찾을 수 없습니다")
        return None
        
    summary_text = summary_match.group(0)
    
    # 기본 검증 결과 추출
    basic_results = {}
    basic_match = re.search(r'전체 파일:\s+(\d+)개.*?구조적 안전:\s+(\d+)개.*?구조적 위험:\s+(\d+)개.*?검증 오류:\s+(\d+)개', summary_text, re.DOTALL)
    if basic_match:
        basic_results = {
            'total': int(basic_match.group(1)),
            'safe': int(basic_match.group(2)),
            'unsafe': int(basic_match.group(3)),
            'errors': int(basic_match.group(4))
        }
    
    # 향상된 검증 결과 추출
    enhanced_results = {}
    enhanced_match = re.search(r'향상된 구조 검증.*?전체 파일:\s+(\d+)개.*?구조적 안전:\s+(\d+)개.*?구조적 위험:\s+(\d+)개.*?검증 오류:\s+(\d+)개', summary_text, re.DOTALL)
    if enhanced_match:
        enhanced_results = {
            'total': int(enhanced_match.group(1)),
            'safe': int(enhanced_match.group(2)),
            'unsafe': int(enhanced_match.group(3)),
            'errors': int(enhanced_match.group(4))
        }
    
    # 구조적 값 문제 세부사항 추출
    structural_issues = []
    
    # needs 의존성 변경 추출
    needs_pattern = r'📄 ([a-f0-9]{64}).*?needs 의존성 변경: (.*?)\n'
    for match in re.finditer(needs_pattern, summary_text, re.DOTALL):
        file_hash = match.group(1)
        change_desc = match.group(2).strip()
        structural_issues.append({
            'file': file_hash[:8] + '...',
            'type': 'needs_dependency_change',
            'description': change_desc
        })
    
    # matrix 전략 변경 추출
    matrix_pattern = r'📄 ([a-f0-9]{64}).*?matrix 전략 변경: (.*?)\n'
    for match in re.finditer(matrix_pattern, summary_text, re.DOTALL):
        file_hash = match.group(1)
        change_desc = match.group(2).strip()
        structural_issues.append({
            'file': file_hash[:8] + '...',
            'type': 'matrix_strategy_change',
            'description': change_desc
        })
    
    # 구조적 값 제거/추가 추출
    structural_value_pattern = r'- (구조적 값 제거|예상치 못한 구조적 값 추가): (.*?) \(타입: (needs|matrix)\)'
    for match in re.finditer(structural_value_pattern, summary_text):
        action = match.group(1)
        path = match.group(2)
        value_type = match.group(3)
        structural_issues.append({
            'type': f'{value_type}_{action}',
            'path': path
        })
    
    return {
        'basic': basic_results,
        'enhanced': enhanced_results,
        'structural_issues': structural_issues
    }

def main():
    log_file = Path('enhanced_verification_output.log')
    
    if not log_file.exists():
        print("❌ 향상된 검증 로그 파일을 찾을 수 없습니다")
        return
    
    print("🔍 향상된 키 구조 검증 결과 분석")
    print("=" * 60)
    
    results = parse_enhanced_verification_log(log_file)
    
    if not results:
        return
    
    basic = results['basic']
    enhanced = results['enhanced']
    
    print(f"\n📊 기본 키 구조 검증:")
    print(f"   전체 파일: {basic['total']}개")
    print(f"   구조적 안전: {basic['safe']}개 ({basic['safe']/basic['total']*100:.1f}%)")
    print(f"   구조적 위험: {basic['unsafe']}개 ({basic['unsafe']/basic['total']*100:.1f}%)")
    print(f"   검증 오류: {basic['errors']}개")
    
    print(f"\n🔬 향상된 구조 검증 (needs/matrix 포함):")
    print(f"   전체 파일: {enhanced['total']}개")
    print(f"   구조적 안전: {enhanced['safe']}개 ({enhanced['safe']/enhanced['total']*100:.1f}%)")
    print(f"   구조적 위험: {enhanced['unsafe']}개 ({enhanced['unsafe']/enhanced['total']*100:.1f}%)")
    print(f"   검증 오류: {enhanced['errors']}개")
    
    print(f"\n📈 비교 분석:")
    print(f"   기본 vs 향상된 안전률: {basic['safe']/basic['total']*100:.1f}% → {enhanced['safe']/enhanced['total']*100:.1f}%")
    
    if basic['safe'] == enhanced['safe']:
        print("   ✅ 두 검증 방법의 안전 파일 수가 동일함")
    else:
        diff = enhanced['safe'] - basic['safe']
        print(f"   {'📈' if diff > 0 else '📉'} 향상된 검증에서 {abs(diff)}개 파일의 평가가 변경됨")
    
    # 구조적 이슈 분석
    structural_issues = results['structural_issues']
    if structural_issues:
        print(f"\n🔍 발견된 구조적 값 문제:")
        
        needs_issues = [i for i in structural_issues if 'needs' in i.get('type', '')]
        matrix_issues = [i for i in structural_issues if 'matrix' in i.get('type', '')]
        
        if needs_issues:
            print(f"   🔗 needs 의존성 문제: {len(needs_issues)}건")
            for issue in needs_issues[:3]:  # 상위 3개만 표시
                if 'description' in issue:
                    print(f"      - {issue['file']}: {issue['description']}")
                elif 'path' in issue:
                    print(f"      - {issue['type']}: {issue['path']}")
        
        if matrix_issues:
            print(f"   🔀 matrix 전략 문제: {len(matrix_issues)}건")
            for issue in matrix_issues[:3]:  # 상위 3개만 표시
                if 'description' in issue:
                    print(f"      - {issue['file']}: {issue['description']}")
                elif 'path' in issue:
                    print(f"      - {issue['type']}: {issue['path']}")
    
    print(f"\n🎯 핵심 발견사항:")
    print(f"   • 향상된 검증이 {enhanced['errors']}개 파일에서 구조적 값 문제를 감지")
    print(f"   • needs 의존성과 matrix 전략 변경이 주요 구조적 이슈")
    print(f"   • if 조건문은 의도적으로 검증에서 제외됨 (의미적 동치)")
    print(f"   • 전체적으로 gha_repair 방법의 안전성: {enhanced['safe']/enhanced['total']*100:.1f}%")

if __name__ == "__main__":
    main()

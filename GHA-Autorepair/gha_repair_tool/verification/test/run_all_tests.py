#!/usr/bin/env python3
"""
전체 테스트 실행 스크립트
Enhanced Key Structure Verifier의 모든 테스트를 실행하고 리포트 생성
"""

import os
import sys
from pathlib import Path
import time
from datetime import datetime

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

def run_all_tests():
    """모든 테스트 실행"""
    print("🧪 Enhanced Key Structure Verifier 전체 테스트 실행")
    print("=" * 80)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = {}
    
    # Test 1: Gray Area 테스트
    print("\n🎯 Test Suite 1: Gray Area 테스트 (좋은 변경 vs 나쁜 변경)")
    print("-" * 60)
    try:
        from test_gray_area import run_gray_area_tests
        start_time = time.time()
        gray_area_success = run_gray_area_tests()
        gray_area_time = time.time() - start_time
        results['gray_area'] = {
            'success': gray_area_success,
            'time': gray_area_time
        }
    except Exception as e:
        print(f"❌ Gray Area 테스트 실행 실패: {e}")
        results['gray_area'] = {
            'success': False,
            'time': 0,
            'error': str(e)
        }
    
    # Test 2: 종합적인 테스트
    print("\n🎯 Test Suite 2: 종합적인 검증 테스트")
    print("-" * 60)
    try:
        from test_comprehensive import run_comprehensive_tests
        start_time = time.time()
        comprehensive_success = run_comprehensive_tests()
        comprehensive_time = time.time() - start_time
        results['comprehensive'] = {
            'success': comprehensive_success,
            'time': comprehensive_time
        }
    except Exception as e:
        print(f"❌ 종합 테스트 실행 실패: {e}")
        results['comprehensive'] = {
            'success': False,
            'time': 0,
            'error': str(e)
        }
    
    # 전체 결과 요약
    print("\n" + "=" * 80)
    print("📊 전체 테스트 결과 요약")
    print("=" * 80)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r['success'])
    total_time = sum(r['time'] for r in results.values())
    
    print(f"🔍 실행된 테스트 스위트: {total_tests}")
    print(f"✅ 성공한 테스트 스위트: {successful_tests}")
    print(f"❌ 실패한 테스트 스위트: {total_tests - successful_tests}")
    print(f"⏱️  총 실행 시간: {total_time:.2f}초")
    
    print("\n📋 상세 결과:")
    for test_name, result in results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        time_str = f"{result['time']:.2f}s"
        print(f"   {test_name:20} {status:10} {time_str:>8}")
        if 'error' in result:
            print(f"      오류: {result['error']}")
    
    # 전체 성공률
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"\n🎯 전체 성공률: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 모든 테스트 통과!")
        print("   Enhanced Key Structure Verifier가 올바르게 동작합니다.")
        print("   스멜 수정과 환각을 정확히 구별할 수 있습니다.")
    else:
        print("\n⚠️  일부 테스트 실패")
        print("   Enhanced Key Structure Verifier 로직을 점검해주세요.")
    
    # 테스트 리포트 파일 생성
    report_path = create_test_report(results, success_rate, total_time)
    print(f"\n📄 상세 리포트: {report_path}")
    
    return success_rate == 100

def create_test_report(results, success_rate, total_time):
    """테스트 리포트 파일 생성"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f"test_report_{timestamp}.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Enhanced Key Structure Verifier 테스트 리포트\n\n")
        f.write(f"**실행 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**전체 성공률:** {success_rate:.1f}%\n")
        f.write(f"**총 실행 시간:** {total_time:.2f}초\n\n")
        
        f.write("## 테스트 결과 요약\n\n")
        f.write("| 테스트 스위트 | 결과 | 실행 시간 | 비고 |\n")
        f.write("|--------------|------|-----------|------|\n")
        
        for test_name, result in results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            time_str = f"{result['time']:.2f}s"
            error_str = result.get('error', '-')
            f.write(f"| {test_name} | {status} | {time_str} | {error_str} |\n")
        
        f.write("\n## 테스트 상세 내용\n\n")
        
        f.write("### 1. Gray Area 테스트\n")
        f.write("**목적:** 스멜 수정 vs 환각 구별 능력 검증\n")
        f.write("**케이스:**\n")
        f.write("- ✅ 스멜 수정 (timeout, permissions, concurrency, if 조건 추가)\n")
        f.write("- ❌ 사이드 이펙트 (needs, matrix 파괴)\n")
        f.write("- ❌ 구조 변경 (steps 순서, job 제거)\n")
        f.write("- ✅ 값 변경 (actions 버전, 환경변수)\n\n")
        
        f.write("### 2. 종합적인 테스트\n")
        f.write("**목적:** 복잡한 시나리오에서의 정확도 검증\n")
        f.write("**케이스:**\n")
        f.write("- 복잡한 needs 의존성 체인\n")
        f.write("- 복잡한 matrix 전략\n")
        f.write("- 여러 스멜 동시 수정\n")
        f.write("- 실제 수리 도구 시뮬레이션\n\n")
        
        if success_rate == 100:
            f.write("## ✅ 결론\n\n")
            f.write("모든 테스트를 통과했습니다. Enhanced Key Structure Verifier가 ")
            f.write("스멜 수정과 환각을 정확히 구별할 수 있음을 확인했습니다.\n\n")
            f.write("**주요 성과:**\n")
            f.write("- needs/matrix를 구조적 요소로 정확히 인식\n")
            f.write("- if 조건을 의미적 동치로 올바르게 처리\n")
            f.write("- 복잡한 시나리오에서도 정확한 판단\n")
            f.write("- 실제 수리 도구들의 패턴을 올바르게 검증\n")
        else:
            f.write("## ⚠️ 결론\n\n")
            f.write("일부 테스트에서 실패가 발생했습니다. ")
            f.write("Enhanced Key Structure Verifier의 로직을 점검해야 합니다.\n\n")
            f.write("**개선 필요 사항:**\n")
            for test_name, result in results.items():
                if not result['success']:
                    f.write(f"- {test_name}: {result.get('error', '알 수 없는 오류')}\n")
    
    return report_path

def main():
    """메인 함수"""
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n🚨 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

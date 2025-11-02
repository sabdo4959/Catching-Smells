#!/usr/bin/env python3
"""
향상된 키 구조 검증기 테스트 스위트
Gray Area 테스트: 좋은 변경 vs 나쁜 변경 구별 능력 검증
"""

import os
import sys
import tempfile
from pathlib import Path
import unittest
from typing import Tuple, Dict, Any

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from enhanced_key_structure_verifier import EnhancedKeyStructureVerifier

class GrayAreaTestSuite(unittest.TestCase):
    """Gray Area 테스트: 스멜 수정 vs 환각 구별"""
    
    def setUp(self):
        """테스트 준비"""
        self.verifier = EnhancedKeyStructureVerifier()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """테스트 정리"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_files(self, original_yaml: str, modified_yaml: str) -> Tuple[str, str]:
        """테스트용 YAML 파일 생성"""
        original_path = os.path.join(self.temp_dir, "original.yml")
        modified_path = os.path.join(self.temp_dir, "modified.yml")
        
        with open(original_path, 'w') as f:
            f.write(original_yaml)
        with open(modified_path, 'w') as f:
            f.write(modified_yaml)
            
        return original_path, modified_path
    
    def verify_files(self, original_yaml: str, modified_yaml: str) -> Dict[str, Any]:
        """파일 검증 실행"""
        original_path, modified_path = self.create_test_files(original_yaml, modified_yaml)
        return self.verifier.verify_structural_safety(original_path, modified_path)

    # =====================================================
    # Test Case 1: Positive Test - "좋은 변경"은 통과시키는가?
    # =====================================================
    
    def test_smell_fix_timeout_addition(self):
        """Smell 5 수정: timeout-minutes 키 추가는 SAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       f"timeout-minutes 추가는 SAFE여야 함. 결과: {result}")
        print("✅ Test 1.1: timeout-minutes 추가 - SAFE 통과")
    
    def test_smell_fix_permissions_addition(self):
        """Smell 3 수정: permissions 키 추가는 SAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       f"permissions 추가는 SAFE여야 함. 결과: {result}")
        print("✅ Test 1.2: permissions 추가 - SAFE 통과")
    
    def test_smell_fix_concurrency_addition(self):
        """Smell 6/7 수정: concurrency 블록 추가는 SAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       f"concurrency 추가는 SAFE여야 함. 결과: {result}")
        print("✅ Test 1.3: concurrency 추가 - SAFE 통과")
    
    def test_smell_fix_if_condition_addition(self):
        """Smell 9/10 수정: if 조건 추가는 SAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       f"if 조건 추가는 SAFE여야 함. 결과: {result}")
        print("✅ Test 1.4: if 조건 추가 - SAFE 통과")

    # =====================================================
    # Test Case 2: Negative Test - "나쁜 변경"은 걸러내는가?
    # =====================================================
    
    def test_side_effect_needs_modification(self):
        """나쁜 변경: 스멜 수정 + needs 의존성 파괴는 UNSAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
  test:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: []
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertFalse(result['is_safe'], 
                        f"timeout 추가 + needs 파괴는 UNSAFE여야 함. 결과: {result}")
        print("✅ Test 2.1: 스멜수정 + needs 파괴 - UNSAFE 차단")
    
    def test_side_effect_matrix_modification(self):
        """나쁜 변경: 스멜 수정 + matrix 전략 파괴는 UNSAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [14, 16, 18]
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    strategy:
      matrix:
        node: [18]
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertFalse(result['is_safe'], 
                        f"timeout 추가 + matrix 변경은 UNSAFE여야 함. 결과: {result}")
        print("✅ Test 2.2: 스멜수정 + matrix 변경 - UNSAFE 차단")

    # =====================================================
    # Test Case 3: Negative Test - "겉보기엔 사소한" 위험한 변경
    # =====================================================
    
    def test_steps_order_change_unsafe(self):
        """위험한 변경: steps 순서 변경은 UNSAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: npm install
      - name: Run tests
        run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test
      - name: Install dependencies
        run: npm install
"""
        
        result = self.verify_files(original, modified)
        self.assertFalse(result['is_safe'], 
                        f"steps 순서 변경은 UNSAFE여야 함. 결과: {result}")
        print("✅ Test 3.1: steps 순서 변경 - UNSAFE 차단")
    
    def test_job_removal_unsafe(self):
        """위험한 변경: job 제거는 UNSAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
  test:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertFalse(result['is_safe'], 
                        f"job 제거는 UNSAFE여야 함. 결과: {result}")
        print("✅ Test 3.2: job 제거 - UNSAFE 차단")

    # =====================================================
    # Test Case 4: Positive Test - "값(Value) 변경"은 무시하는가?
    # =====================================================
    
    def test_action_version_update_safe(self):
        """Smell 24 수정: actions 버전 업데이트는 SAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       f"actions 버전 업데이트는 SAFE여야 함. 결과: {result}")
        print("✅ Test 4.1: actions 버전 업데이트 - SAFE 통과")
    
    def test_run_script_update_safe(self):
        """Smell 25 수정: run 스크립트 값 변경은 SAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set output
        run: echo "::set-output name=result::success"
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set output
        run: echo "result=success" >> $GITHUB_OUTPUT
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       f"run 스크립트 값 변경은 SAFE여야 함. 결과: {result}")
        print("✅ Test 4.2: run 스크립트 업데이트 - SAFE 통과")
    
    def test_env_value_change_safe(self):
        """값 변경: 환경변수 값 변경은 SAFE여야 함"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      NODE_ENV: development
      API_URL: http://localhost:3000
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      NODE_ENV: production
      API_URL: https://api.production.com
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       f"환경변수 값 변경은 SAFE여야 함. 결과: {result}")
        print("✅ Test 4.3: 환경변수 값 변경 - SAFE 통과")

def run_gray_area_tests():
    """Gray Area 테스트 실행"""
    print("🔬 Gray Area 테스트 시작: 좋은 변경 vs 나쁜 변경 구별 능력 검증")
    print("=" * 80)
    
    # 테스트 스위트 생성
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(GrayAreaTestSuite)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 80)
    print(f"🎯 테스트 결과 요약:")
    print(f"   실행된 테스트: {result.testsRun}")
    print(f"   성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   실패: {len(result.failures)}")
    print(f"   오류: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ 실패한 테스트:")
        for test, trace in result.failures:
            print(f"   - {test}: {trace.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\n🚨 오류가 발생한 테스트:")
        for test, trace in result.errors:
            print(f"   - {test}: {trace.split('\\n')[-2]}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n📊 성공률: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 모든 Gray Area 테스트 통과! 검증기가 스마트하게 동작합니다.")
    else:
        print("⚠️  일부 테스트 실패. 검증기 로직 개선이 필요합니다.")
    
    return result.testsRun == (result.testsRun - len(result.failures) - len(result.errors))

if __name__ == "__main__":
    run_gray_area_tests()

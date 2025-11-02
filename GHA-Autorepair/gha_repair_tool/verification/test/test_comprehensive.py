#!/usr/bin/env python3
"""
종합적인 검증 테스트 러너
Enhanced Key Structure Verifier의 전반적인 정확도 검증
"""

import os
import sys
from pathlib import Path
import unittest
import tempfile
from typing import Dict, Any, List, Tuple

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from enhanced_key_structure_verifier import EnhancedKeyStructureVerifier

class ComprehensiveTestSuite(unittest.TestCase):
    """종합적인 검증 테스트"""
    
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
    # Edge Cases: 복잡한 시나리오들
    # =====================================================
    
    def test_complex_needs_dependency_chain(self):
        """복잡한 needs 의존성 체인 변경은 UNSAFE"""
        original = """
name: Complex CI
on: [push]
jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
  
  build:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - run: npm run build
  
  test-unit:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit
  
  test-integration:
    needs: [build, test-unit]
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:integration
  
  deploy:
    needs: [test-unit, test-integration]
    runs-on: ubuntu-latest
    steps:
      - run: npm run deploy
"""
        
        modified = """
name: Complex CI
on: [push]
jobs:
  setup:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
  
  build:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - run: npm run build
  
  test-unit:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit
  
  test-integration:
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:integration
  
  deploy:
    needs: [test-integration]
    runs-on: ubuntu-latest
    steps:
      - run: npm run deploy
"""
        
        result = self.verify_files(original, modified)
        self.assertFalse(result['is_safe'], 
                        "needs 의존성 체인 변경은 UNSAFE여야 함")
        print("✅ 복잡한 needs 체인 변경 감지")
    
    def test_matrix_strategy_complex(self):
        """복잡한 matrix 전략 변경은 UNSAFE"""
        original = """
name: Matrix Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        node: [14, 16, 18, 20]
        os: [ubuntu-latest, windows-latest, macos-latest]
        include:
          - node: 20
            os: ubuntu-latest
            experimental: true
        exclude:
          - node: 14
            os: windows-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        modified = """
name: Matrix Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        node: [16, 18]
        os: [ubuntu-latest]
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertFalse(result['is_safe'], 
                        "복잡한 matrix 전략 변경은 UNSAFE여야 함")
        print("✅ 복잡한 matrix 전략 변경 감지")
    
    def test_multiple_smell_fixes_safe(self):
        """여러 스멜 동시 수정은 SAFE"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm test
      - run: echo "::set-output name=result::success"
"""
        
        modified = """
name: CI
on: [push]
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: npm test
      - run: echo "result=success" >> $GITHUB_OUTPUT
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       "여러 스멜 동시 수정은 SAFE여야 함")
        print("✅ 여러 스멜 동시 수정 통과")
    
    def test_good_change_with_side_effect_unsafe(self):
        """좋은 변경 + 사이드 이펙트 = UNSAFE"""
        original = """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [14, 16, 18]
    steps:
      - uses: actions/checkout@v2
      - run: npm run build
  
  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm test
"""
        
        modified = """
name: CI
on: [push]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    strategy:
      matrix:
        node: [18]
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
  
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        result = self.verify_files(original, modified)
        self.assertFalse(result['is_safe'], 
                        "좋은 변경 + 사이드 이펙트는 UNSAFE여야 함")
        print("✅ 좋은 변경 + 사이드 이펙트 차단")

    # =====================================================
    # 실제 수리 결과 시뮬레이션
    # =====================================================
    
    def test_baseline_repair_simulation(self):
        """Baseline 수리 시뮬레이션: 매우 보수적"""
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
        
        # Baseline: 매우 안전한 변경만
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
                       "Baseline 스타일 수리는 SAFE여야 함")
        print("✅ Baseline 수리 스타일 검증")
    
    def test_gha_repair_simulation(self):
        """GHA-Repair 수리 시뮬레이션: 적극적이지만 안전"""
        original = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm test
      - run: echo "::set-output name=result::success"
"""
        
        # GHA-Repair: 여러 스멜 동시 수정
        modified = """
name: CI
on: [push]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - run: npm test
      - run: echo "result=success" >> $GITHUB_OUTPUT
"""
        
        result = self.verify_files(original, modified)
        self.assertTrue(result['is_safe'], 
                       "GHA-Repair 스타일 수리는 SAFE여야 함")
        print("✅ GHA-Repair 수리 스타일 검증")
    
    def test_hallucination_simulation(self):
        """환각 시뮬레이션: 위험한 변경들"""
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
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [14, 16, 18]
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        
        # 환각: 스멜 수정하면서 구조 파괴
        modified = """
name: CI
on: [push]
permissions:
  contents: read
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
                        "환각 스타일 변경은 UNSAFE여야 함")
        print("✅ 환각 패턴 차단")

def run_comprehensive_tests():
    """종합적인 테스트 실행"""
    print("🔬 종합적인 검증 테스트 시작")
    print("=" * 80)
    
    # 테스트 스위트 생성
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(ComprehensiveTestSuite)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 80)
    print(f"🎯 종합 테스트 결과:")
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
    
    return result.testsRun == (result.testsRun - len(result.failures) - len(result.errors))

if __name__ == "__main__":
    run_comprehensive_tests()

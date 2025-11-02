#!/usr/bin/env python3
"""
Steps 순서 변경 디버깅 스크립트
"""

import tempfile
import os
import sys
from pathlib import Path

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from enhanced_key_structure_verifier import verify_enhanced_structural_equivalence, _extract_key_structure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from parser import GHAWorkflowParser

def debug_steps_order():
    """Steps 순서 변경 테스트 디버깅"""
    
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
    
    # 임시 파일 생성
    temp_dir = tempfile.mkdtemp()
    try:
        original_path = os.path.join(temp_dir, "original.yml")
        modified_path = os.path.join(temp_dir, "modified.yml")
        
        with open(original_path, 'w') as f:
            f.write(original)
        with open(modified_path, 'w') as f:
            f.write(modified)
        
        # 파싱 및 키 구조 분석
        parser = GHAWorkflowParser()
        ast_orig = parser.parse(Path(original_path))
        ast_repaired = parser.parse(Path(modified_path))
        
        print("원본 AST steps:")
        orig_steps = ast_orig.get('jobs', {}).get('test', {}).get('steps', [])
        for i, step in enumerate(orig_steps):
            print(f"  step[{i}]: {step}")
        
        print("\\n수정된 AST steps:")
        repaired_steps = ast_repaired.get('jobs', {}).get('test', {}).get('steps', [])
        for i, step in enumerate(repaired_steps):
            print(f"  step[{i}]: {step}")
        
        orig_key_structure = _extract_key_structure(ast_orig)
        repaired_key_structure = _extract_key_structure(ast_repaired)
        
        print("\\n원본 키 구조:")
        for key, info in orig_key_structure.items():
            if "steps" in key:
                print(f"  {key}: {info}")
        
        print("\\n수정된 키 구조:")
        for key, info in repaired_key_structure.items():
            if "steps" in key:
                print(f"  {key}: {info}")
        
        # 전체 검증 실행
        result = verify_enhanced_structural_equivalence(Path(original_path), Path(modified_path))
        print(f"\\n검증 결과: {result['safe']}")
        print(f"키 구조 문제: {result['key_structure_issues']}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    debug_steps_order()

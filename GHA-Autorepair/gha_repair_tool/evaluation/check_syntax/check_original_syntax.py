#!/usr/bin/env python3
"""
원본 YAML 파일들의 구문 검증 스크립트

지정된 디렉토리의 YAML 파일에 대해:
1. YAML 파싱 검증
2. actionlint 구문 검증
을 수행하고 결과를 출력합니다.
"""

import os
import sys
import logging
import yaml
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

# 상위 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
# check_syntax -> evaluation -> gha_repair_tool
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from utils import process_runner
from utils import yaml_parser


def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def check_yaml_syntax(file_path: str) -> Dict[str, Any]:
    """
    YAML 파일의 구문을 검증합니다.
    
    Args:
        file_path: 검증할 YAML 파일 경로
        
    Returns:
        Dict: 검증 결과
    """
    result = {
        'file': os.path.basename(file_path),
        'yaml_valid': False,
        'yaml_error': None,
        'actionlint_valid': False,
        'actionlint_errors': [],
        'actionlint_syntax_errors': [],
        'actionlint_expression_errors': []
    }
    
    # 1. YAML 파싱 검증
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        yaml_data = yaml.safe_load(content)
        
        if yaml_data is not None:
            result['yaml_valid'] = True
        else:
            result['yaml_error'] = "Empty YAML file"
    except yaml.YAMLError as e:
        result['yaml_error'] = str(e)
    except Exception as e:
        result['yaml_error'] = f"Unknown error: {str(e)}"
    
    # 2. actionlint 검증 (evaluator.py와 동일한 로직)
    try:
        actionlint_result = process_runner.run_actionlint(file_path)
        
        if actionlint_result.get('success', True):
            # 성공: 오류 없음
            result['actionlint_valid'] = True
        else:
            # 실패: 오류 있음
            errors = actionlint_result.get('errors', [])
            result['actionlint_errors'] = errors
            
            # syntax-check와 expression 타입의 에러만 필터링 (evaluator.py와 동일)
            syntax_errors = [
                error for error in errors 
                if isinstance(error, dict) and error.get('kind') in ['syntax-check', 'expression']
            ]
            
            for error in syntax_errors:
                kind = error.get('kind', '')
                if kind == 'syntax-check':
                    result['actionlint_syntax_errors'].append(error)
                elif kind == 'expression':
                    result['actionlint_expression_errors'].append(error)
            
            # evaluator.py와 동일: syntax-check, expression 오류만 있으면 실패
            # 다른 타입의 오류(permissions, deprecated-commands 등)는 무시
            result['actionlint_valid'] = len(syntax_errors) == 0
            
    except Exception as e:
        result['actionlint_errors'] = [f"actionlint execution error: {str(e)}"]
    
    return result


def print_summary(results: List[Dict[str, Any]]):
    """
    검증 결과 요약을 출력합니다.
    
    Args:
        results: 검증 결과 리스트
    """
    total_files = len(results)
    
    yaml_valid_count = sum(1 for r in results if r['yaml_valid'])
    yaml_invalid_count = total_files - yaml_valid_count
    
    actionlint_valid_count = sum(1 for r in results if r['actionlint_valid'])
    actionlint_invalid_count = total_files - actionlint_valid_count
    
    syntax_error_count = sum(1 for r in results if len(r['actionlint_syntax_errors']) > 0)
    expression_error_count = sum(1 for r in results if len(r['actionlint_expression_errors']) > 0)
    
    print("\n" + "="*80)
    print("구문 검증 결과 요약")
    print("="*80)
    print(f"총 파일 수: {total_files}")
    print()
    print("YAML 파싱 결과:")
    print(f"  ✅ 유효: {yaml_valid_count} ({yaml_valid_count/total_files*100:.1f}%)")
    print(f"  ❌ 무효: {yaml_invalid_count} ({yaml_invalid_count/total_files*100:.1f}%)")
    print()
    print("actionlint 검증 결과:")
    print(f"  ✅ 통과: {actionlint_valid_count} ({actionlint_valid_count/total_files*100:.1f}%)")
    print(f"  ❌ 실패: {actionlint_invalid_count} ({actionlint_invalid_count/total_files*100:.1f}%)")
    print(f"     - syntax-check 오류: {syntax_error_count}개 파일")
    print(f"     - expression 오류: {expression_error_count}개 파일")
    print("="*80)
    
    # YAML 무효 파일 목록
    if yaml_invalid_count > 0:
        print("\nYAML 파싱 실패 파일:")
        print("-"*80)
        for result in results:
            if not result['yaml_valid']:
                print(f"  - {result['file']}")
                print(f"    오류: {result['yaml_error'][:100]}")
    
    # actionlint 실패 파일 목록 (상위 10개만)
    if actionlint_invalid_count > 0:
        print("\nactionlint 검증 실패 파일 (상위 10개):")
        print("-"*80)
        invalid_files = [r for r in results if not r['actionlint_valid']]
        for result in invalid_files[:10]:
            print(f"  - {result['file']}")
            
            # syntax-check 오류
            if result['actionlint_syntax_errors']:
                print(f"    syntax-check 오류 ({len(result['actionlint_syntax_errors'])}개):")
                for err in result['actionlint_syntax_errors'][:3]:
                    msg = err.get('message', 'Unknown error')
                    print(f"      • {msg[:80]}")
            
            # expression 오류
            if result['actionlint_expression_errors']:
                print(f"    expression 오류 ({len(result['actionlint_expression_errors'])}개):")
                for err in result['actionlint_expression_errors'][:3]:
                    msg = err.get('message', 'Unknown error')
                    print(f"      • {msg[:80]}")
    
    print()


def main():
    """메인 함수"""
    # 커맨드 라인 인자 파싱
    parser = argparse.ArgumentParser(
        description="YAML 파일들의 구문 검증 (YAML 파싱 + actionlint)"
    )
    
    parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="검증할 YAML 파일들이 있는 디렉토리 경로 (기본값: data_original)"
    )
    
    parser.add_argument(
        "--max-files",
        type=int,
        default=100,
        help="최대 검증할 파일 수 (기본값: 100)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="결과 파일을 저장할 디렉토리 (기본값: evaluation)"
    )
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 입력 디렉토리 경로 설정
    script_dir = Path(__file__).parent
    
    if args.input_dir:
        # 절대 경로 또는 상대 경로 처리
        input_dir = Path(args.input_dir)
        if not input_dir.is_absolute():
            # 상대 경로면 현재 작업 디렉토리 기준
            input_dir = Path.cwd() / input_dir
    else:
        # 기본값: data_original (gha_repair_tool 디렉토리 기준)
        # check_syntax -> evaluation -> gha_repair_tool -> data_original
        gha_repair_tool_dir = script_dir.parent.parent
        input_dir = gha_repair_tool_dir / "data_original"
    
    if not input_dir.exists():
        logger.error(f"입력 디렉토리를 찾을 수 없습니다: {input_dir}")
        sys.exit(1)
    
    logger.info(f"입력 디렉토리: {input_dir}")
    
    # 출력 디렉토리 설정
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
    else:
        output_dir = script_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"출력 디렉토리: {output_dir}")
    
    # YAML 파일 목록 가져오기
    yaml_files = sorted(list(input_dir.glob("*")))
    
    # 디렉토리 제외
    yaml_files = [f for f in yaml_files if f.is_file()]
    
    logger.info(f"총 {len(yaml_files)}개 파일 발견")
    
    if len(yaml_files) == 0:
        logger.error("검증할 파일이 없습니다")
        sys.exit(1)
    
    # 최대 파일 수 제한
    if len(yaml_files) > args.max_files:
        logger.info(f"처음 {args.max_files}개 파일만 처리합니다")
        yaml_files = yaml_files[:args.max_files]
    
    # 각 파일 검증
    results = []
    
    print(f"\n파일 검증 중... (총 {len(yaml_files)}개)")
    print("-"*80)
    
    for i, yaml_file in enumerate(yaml_files, 1):
        logger.info(f"[{i}/{len(yaml_files)}] {yaml_file.name} 검증 중...")
        
        result = check_yaml_syntax(str(yaml_file))
        results.append(result)
        
        # 간단한 진행 상황 출력
        status = "✅" if result['yaml_valid'] and result['actionlint_valid'] else "❌"
        print(f"  [{i:3d}] {status} {yaml_file.name}")
    
    # 결과 요약 출력
    print_summary(results)
    
    # 디렉토리 이름을 결과 파일명에 포함
    dir_name = input_dir.name
    
    # 결과를 JSON 파일로 저장
    output_file = output_dir / f"syntax_check_{dir_name}_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n상세 결과가 저장되었습니다: {output_file}")
    
    # CSV 형태로도 저장
    csv_output_file = output_dir / f"syntax_check_{dir_name}_results.csv"
    with open(csv_output_file, 'w', encoding='utf-8') as f:
        f.write("file,yaml_valid,actionlint_valid,syntax_errors,expression_errors\n")
        for result in results:
            f.write(f"{result['file']},"
                   f"{result['yaml_valid']},"
                   f"{result['actionlint_valid']},"
                   f"{len(result['actionlint_syntax_errors'])},"
                   f"{len(result['actionlint_expression_errors'])}\n")
    
    logger.info(f"CSV 결과가 저장되었습니다: {csv_output_file}")


if __name__ == "__main__":
    main()

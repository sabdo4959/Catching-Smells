#!/usr/bin/env python3
"""
/Users/nam/workflows/ 전체 파일 비교 평가 스크립트

step1과 step2 파일들을 모두 비교하여:
1. 전체 파일 통계
2. actionlint 통과 파일만의 통계
3. actionlint 통과 + BLEU >= 0.85 파일 통계
"""

import logging
import argparse
import sys
import os
import json
import csv
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import pandas as pd
import difflib
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

# 로컬 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import process_runner


class AllWorkflowsComparator:
    """전체 워크플로우 파일 비교 평가 클래스"""
    
    def __init__(self, output_dir: str = "./evaluation/all_workflows_comparison"):
        """
        Args:
            output_dir: 결과를 저장할 디렉토리
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def check_yaml_syntax(self, file_path: str) -> Tuple[bool, str]:
        """YAML 파싱 검증"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            yaml_data = yaml.safe_load(content)
            if yaml_data is not None:
                return True, None
            else:
                return False, "Empty YAML file"
        except yaml.YAMLError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unknown error: {str(e)}"
    
    def check_with_actionlint(self, file_path: str) -> Tuple[bool, List, List, List]:
        """
        actionlint 검증
        
        Returns:
            Tuple[valid, all_errors, syntax_errors, expression_errors]
        """
        try:
            result = process_runner.run_actionlint(file_path)
            
            if result.get('success', True):
                return True, [], [], []
            else:
                all_errors = result.get('errors', [])
                
                # syntax-check와 expression 오류만 필터링
                syntax_errors = [
                    error for error in all_errors 
                    if isinstance(error, dict) and error.get('kind') == 'syntax-check'
                ]
                expression_errors = [
                    error for error in all_errors 
                    if isinstance(error, dict) and error.get('kind') == 'expression'
                ]
                
                # syntax-check, expression 오류만 있으면 실패
                is_valid = len(syntax_errors) == 0 and len(expression_errors) == 0
                
                return is_valid, all_errors, syntax_errors, expression_errors
                
        except Exception as e:
            self.logger.error(f"actionlint 실행 오류: {e}")
            error_obj = {'message': str(e), 'kind': 'runtime-error'}
            return False, [error_obj], [], []
    
    def calculate_edit_distance(self, file1: str, file2: str) -> int:
        """두 파일 간의 Edit Distance 계산 (Line-level)"""
        try:
            with open(file1, 'r', encoding='utf-8') as f:
                content1_lines = f.readlines()
            with open(file2, 'r', encoding='utf-8') as f:
                content2_lines = f.readlines()
            
            matcher = difflib.SequenceMatcher(None, content1_lines, content2_lines)
            opcodes = matcher.get_opcodes()
            edit_distance = 0
            
            for op, i1, i2, j1, j2 in opcodes:
                if op == 'replace':
                    edit_distance += max(i2 - i1, j2 - j1)
                elif op == 'delete':
                    edit_distance += i2 - i1
                elif op == 'insert':
                    edit_distance += j2 - j1
            
            return edit_distance
            
        except Exception as e:
            self.logger.error(f"Edit distance 계산 오류: {e}")
            return -1
    
    def calculate_bleu_score(self, file1: str, file2: str) -> float:
        """두 파일 간의 BLEU Score 계산"""
        try:
            with open(file1, 'r', encoding='utf-8') as f:
                reference = f.read()
            with open(file2, 'r', encoding='utf-8') as f:
                hypothesis = f.read()
            
            # 토큰화: 줄 단위로 분리
            reference_tokens = [reference.split('\n')]
            candidate_tokens = hypothesis.split('\n')
            
            # Smoothing function 사용
            smoothing = SmoothingFunction().method1
            
            # BLEU score 계산
            bleu = sentence_bleu(reference_tokens, candidate_tokens, smoothing_function=smoothing)
            return bleu
            
        except Exception as e:
            self.logger.error(f"BLEU score 계산 오류: {e}")
            return -1.0
    
    def find_step_pairs_all(self, workflows_dir: str, max_files: int = None) -> Dict[str, List[Tuple[str, str]]]:
        """
        workflows 디렉토리에서 step1과 step2, 3, 4, 5의 모든 파일 쌍을 찾습니다.
        os.scandir()를 사용하여 빠르게 탐색합니다.
        
        Args:
            workflows_dir: 워크플로우 파일 디렉토리
            max_files: 각 step별 최대 파일 수
            
        Returns:
            Dict[str, List[Tuple[step1_path, stepN_path]]]: 
                키: 'step2', 'step3', 'step4', 'step5'
                값: 파일 쌍 리스트
        """
        import os
        
        if not os.path.exists(workflows_dir):
            raise FileNotFoundError(f"디렉토리가 없습니다: {workflows_dir}")
        
        self.logger.info(f"파일 쌍 탐색 시작: {workflows_dir}")
        
        # step1 파일들을 먼저 수집 (딕셔너리로 빠른 조회)
        step1_files = {}
        step1_count = 0
        
        self.logger.info("Step1 파일 탐색 중...")
        
        try:
            with os.scandir(workflows_dir) as entries:
                for entry in entries:
                    # 파일명만 체크 (is_file() 호출 안 함 - 느림)
                    if entry.name.endswith('_step1.yaml') or entry.name.endswith('_step1.yml'):
                        base_name = entry.name.replace('_step1.yaml', '').replace('_step1.yml', '')
                        step1_files[base_name] = entry.path
                        step1_count += 1
                        
                        if step1_count % 1000 == 0:
                            self.logger.info(f"  Step1: {step1_count}개 파일 발견...")
                        
                        # max_files 제한 (step1도 제한)
                        if max_files and step1_count >= max_files * 2:  # 여유있게 2배
                            self.logger.info(f"  Step1: {max_files * 2}개 제한 도달, 탐색 중단")
                            break
                            
        except Exception as e:
            self.logger.error(f"Step1 파일 탐색 중 오류: {e}")
            raise
        
        if not step1_files:
            raise ValueError("step1 파일이 하나도 없습니다!")
        
        self.logger.info(f"✅ Step1: 총 {len(step1_files)}개 파일 발견")
        
        # 각 step별로 파일 쌍 생성
        all_pairs = {}
        
        for step_num in [2, 3, 4, 5]:
            step_key = f'step{step_num}'
            file_pairs = []
            stepN_count = 0
            matched_count = 0
            
            self.logger.info(f"\n{step_key.upper()} 파일 탐색 중...")
            
            try:
                with os.scandir(workflows_dir) as entries:
                    for entry in entries:
                        # stepN 파일 체크 (파일명만)
                        if entry.name.endswith(f'_step{step_num}.yaml') or entry.name.endswith(f'_step{step_num}.yml'):
                            stepN_count += 1
                            
                            if stepN_count % 1000 == 0:
                                self.logger.info(f"  {step_key}: {stepN_count}개 파일 스캔 중...")
                            
                            base_name = entry.name.replace(f'_step{step_num}.yaml', '').replace(f'_step{step_num}.yml', '')
                            
                            if base_name in step1_files:
                                step1_path = step1_files[base_name]
                                file_pairs.append((step1_path, entry.path))
                                matched_count += 1
                                
                                # max_files 제한 확인
                                if max_files and matched_count >= max_files:
                                    self.logger.info(f"  {step_key}: {max_files}개 제한 도달, 탐색 중단")
                                    break
                                    
            except Exception as e:
                self.logger.error(f"{step_key} 파일 탐색 중 오류: {e}")
            
            all_pairs[step_key] = file_pairs
            self.logger.info(f"✅ {step_key.upper()}: {stepN_count}개 중 {matched_count}개 매칭됨")
        
        # 결과 요약
        print("\n" + "=" * 80)
        print("📁 Step별 파일 매칭 결과")
        print("=" * 80)
        print(f"Step1: {len(step1_files)}개 파일 (기준)")
        for step_num in [2, 3, 4, 5]:
            step_key = f'step{step_num}'
            count = len(all_pairs[step_key])
            print(f"Step{step_num}: {count}개 파일 쌍 매칭됨")
        print("=" * 80 + "\n")
        
        return all_pairs
    
    def compare_all_workflows_by_dirs(self, 
                                      step_dirs: Dict[str, str],
                                      csv_file: str = None,
                                      max_files: int = None) -> Dict:
        """
        별도 디렉토리에 있는 step 파일들을 비교 평가합니다.
        step1과 step2, 3, 4, 5를 각각 비교합니다.
        
        Args:
            step_dirs: {'step1': path, 'step2': path, ...} 디렉토리 정보
            csv_file: step 매핑 정보를 담은 CSV 파일 경로
            max_files: 평가할 최대 파일 수 (각 step별로 적용)
            
        Returns:
            Dict: 비교 평가 결과 (step별로 구분)
        """
        import csv as csv_module
        
        start_time = datetime.now()
        
        # CSV에서 step 매핑 정보 읽기
        if csv_file is None:
            csv_file = "/Users/nam/Desktop/repository/Catching-Smells/data/all_steps.csv"
        
        self.logger.info(f"CSV 파일 로딩 중: {csv_file}")
        step_mappings = {}  # {step1_hash: {'step2': step2_hash, 'step3': step3_hash, ...}}
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv_module.DictReader(f)
            for row in reader:
                step1_hash = row['file_hash_step1']
                if not step1_hash or step1_hash.strip() == '':
                    continue
                
                step_mappings[step1_hash] = {
                    'step2': row.get('file_hash_step2', ''),
                    'step3': row.get('file_hash_step3', ''),
                    'step4': row.get('file_hash_step4', ''),
                    'step5': row.get('file_hash_step5', '')
                }
        
        self.logger.info(f"✅ CSV에서 {len(step_mappings)}개 매핑 로드됨")
        
        # step1 파일 목록 수집 (파일명 → 경로)
        step1_dir = Path(step_dirs['step1'])
        if not step1_dir.exists():
            raise FileNotFoundError(f"Step1 디렉토리가 없습니다: {step1_dir}")
        
        self.logger.info(f"Step1 파일 수집 중: {step1_dir}")
        step1_files = {}
        
        # 확장자 없는 파일 수집 (해시값만 있는 파일명)
        for file_path in step1_dir.iterdir():
            if file_path.is_file():
                file_hash = file_path.name  # 파일명 전체가 해시
                # CSV에 매핑 정보가 있는 파일만 수집
                if file_hash in step_mappings:
                    step1_files[file_hash] = str(file_path)
        
        total_step1 = len(step1_files)
        self.logger.info(f"✅ Step1: {total_step1}개 파일 발견 (CSV 매핑 있음)")
        
        # max_files 제한 적용
        if max_files and total_step1 > max_files:
            step1_files = dict(list(step1_files.items())[:max_files])
            self.logger.info(f"  Step1: {max_files}개로 제한")
        
        # 각 step별로 파일 쌍 생성 및 평가
        all_step_results = {}
        
        for step_num in [2, 3, 4, 5]:
            step_key = f'step{step_num}'
            step_dir = Path(step_dirs[step_key])
            
            if not step_dir.exists():
                self.logger.warning(f"{step_key} 디렉토리가 없습니다: {step_dir}")
                all_step_results[step_key] = {
                    'file_pairs_count': 0,
                    'results': [],
                    'stats': None
                }
                continue
            
            self.logger.info(f"\n{step_key.upper()} 파일 매칭 중...")
            
            # CSV 매핑을 사용해서 파일 쌍 생성
            file_pairs = []
            
            for step1_hash, step1_path in step1_files.items():
                # CSV에서 해당 stepN의 해시값 찾기
                stepN_hash = step_mappings[step1_hash].get(step_key, '')
                
                if not stepN_hash or stepN_hash.strip() == '':
                    continue
                
                # stepN 파일 경로 생성
                stepN_path = step_dir / stepN_hash
                
                if stepN_path.exists():
                    file_pairs.append((step1_path, str(stepN_path)))
            
            total_pairs = len(file_pairs)
            self.logger.info(f"✅ {step_key}: {total_pairs}개 파일 쌍 매칭됨")
            
            if total_pairs == 0:
                all_step_results[step_key] = {
                    'file_pairs_count': 0,
                    'results': [],
                    'stats': None
                }
                continue
            
            # 평가 수행
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"🔍 {step_key.upper()} 비교 평가 시작: {total_pairs}개 파일 쌍")
            self.logger.info(f"{'='*60}")
            
            step_results = []
            
            for i, (step1_file, stepN_file) in enumerate(file_pairs, 1):
                if i % 100 == 0 or i == 1:
                    self.logger.info(f"[{step_key}] [{i}/{total_pairs}] 평가 중... ({i/total_pairs*100:.1f}%)")
                
                # step1 검증
                step1_yaml_valid, step1_yaml_error = self.check_yaml_syntax(step1_file)
                step1_actionlint_valid, step1_all_errors, step1_syntax_errors, step1_expression_errors = \
                    self.check_with_actionlint(step1_file)
                
                # stepN 검증
                stepN_yaml_valid, stepN_yaml_error = self.check_yaml_syntax(stepN_file)
                stepN_actionlint_valid, stepN_all_errors, stepN_syntax_errors, stepN_expression_errors = \
                    self.check_with_actionlint(stepN_file)
                
                # 유사도 계산
                edit_distance = self.calculate_edit_distance(step1_file, stepN_file)
                bleu_score = self.calculate_bleu_score(step1_file, stepN_file)
                
                result = {
                    'base_name': Path(step1_file).stem,
                    'step1_file': Path(step1_file).name,
                    f'{step_key}_file': Path(stepN_file).name,
                    
                    # step1 결과
                    'step1_yaml_valid': step1_yaml_valid,
                    'step1_yaml_error': step1_yaml_error,
                    'step1_actionlint_valid': step1_actionlint_valid,
                    'step1_syntax_error_count': len(step1_syntax_errors),
                    'step1_expression_error_count': len(step1_expression_errors),
                    
                    # stepN 결과
                    f'{step_key}_yaml_valid': stepN_yaml_valid,
                    f'{step_key}_yaml_error': stepN_yaml_error,
                    f'{step_key}_actionlint_valid': stepN_actionlint_valid,
                    f'{step_key}_syntax_error_count': len(stepN_syntax_errors),
                    f'{step_key}_expression_error_count': len(stepN_expression_errors),
                    
                    # 유사도
                    'edit_distance': edit_distance,
                    'bleu_score': bleu_score,
                    
                    # 개선 여부
                    'yaml_improved': stepN_yaml_valid and not step1_yaml_valid,
                    'actionlint_improved': stepN_actionlint_valid and not step1_actionlint_valid,
                }
                
                step_results.append(result)
            
            # step별 통계 계산
            step_stats = self._calculate_step_statistics(step_results, total_pairs, step_key)
            
            all_step_results[step_key] = {
                'file_pairs_count': total_pairs,
                'results': step_results,
                'stats': step_stats
            }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 전체 요약
        summary = {
            'metadata': {
                'step_dirs': step_dirs,
                'csv_file': csv_file,
                'processing_time': processing_time,
                'timestamp': datetime.now().isoformat()
            },
            'step_results': all_step_results
        }
        
        # 결과 저장 및 출력
        self.save_comparison_results(summary)
        self.print_comparison_summary(summary)
        
        return summary
    
    def compare_all_workflows(self, 
                              workflows_dir: str,
                              max_files: int = None) -> Dict:
        """
        전체 워크플로우 파일을 비교 평가합니다.
        step1과 step2, 3, 4, 5를 각각 비교합니다.
        
        Args:
            workflows_dir: 워크플로우 파일 디렉토리
            max_files: 평가할 최대 파일 수 (각 step별로 적용)
            
        Returns:
            Dict: 비교 평가 결과 (step별로 구분)
        """
        start_time = datetime.now()
        
        # 모든 step 파일 쌍 찾기 (max_files 제한 포함)
        all_step_pairs = self.find_step_pairs_all(workflows_dir, max_files)
        
        # 각 step별로 평가 수행
        all_step_results = {}
        
        for step_key in ['step2', 'step3', 'step4', 'step5']:
            file_pairs = all_step_pairs[step_key]
            
            if not file_pairs:
                self.logger.warning(f"{step_key}: 매칭되는 파일 쌍이 없습니다")
                all_step_results[step_key] = {
                    'file_pairs_count': 0,
                    'results': [],
                    'stats': None
                }
                continue
            
            total_pairs = len(file_pairs)
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"🔍 {step_key.upper()} 비교 평가 시작: {total_pairs}개 파일 쌍")
            self.logger.info(f"{'='*60}")
            
            # 파일 평가
            step_results = []
            
            for i, (step1_file, stepN_file) in enumerate(file_pairs, 1):
                if i % 10 == 0 or i == 1:
                    self.logger.info(f"[{step_key}] [{i}/{total_pairs}] 평가 중... ({i/total_pairs*100:.1f}%)")
                
                # step1 검증
                step1_yaml_valid, step1_yaml_error = self.check_yaml_syntax(step1_file)
                step1_actionlint_valid, step1_all_errors, step1_syntax_errors, step1_expression_errors = \
                    self.check_with_actionlint(step1_file)
                
                # stepN 검증
                stepN_yaml_valid, stepN_yaml_error = self.check_yaml_syntax(stepN_file)
                stepN_actionlint_valid, stepN_all_errors, stepN_syntax_errors, stepN_expression_errors = \
                    self.check_with_actionlint(stepN_file)
                
                # 유사도 계산
                edit_distance = self.calculate_edit_distance(step1_file, stepN_file)
                bleu_score = self.calculate_bleu_score(step1_file, stepN_file)
                
                result = {
                    'base_name': Path(step1_file).stem.replace('_step1', ''),
                    'step1_file': Path(step1_file).name,
                    f'{step_key}_file': Path(stepN_file).name,
                    
                    # step1 결과
                    'step1_yaml_valid': step1_yaml_valid,
                    'step1_yaml_error': step1_yaml_error,
                    'step1_actionlint_valid': step1_actionlint_valid,
                    'step1_syntax_error_count': len(step1_syntax_errors),
                    'step1_expression_error_count': len(step1_expression_errors),
                    
                    # stepN 결과
                    f'{step_key}_yaml_valid': stepN_yaml_valid,
                    f'{step_key}_yaml_error': stepN_yaml_error,
                    f'{step_key}_actionlint_valid': stepN_actionlint_valid,
                    f'{step_key}_syntax_error_count': len(stepN_syntax_errors),
                    f'{step_key}_expression_error_count': len(stepN_expression_errors),
                    
                    # 유사도
                    'edit_distance': edit_distance,
                    'bleu_score': bleu_score,
                    
                    # 개선 여부
                    'yaml_improved': stepN_yaml_valid and not step1_yaml_valid,
                    'actionlint_improved': stepN_actionlint_valid and not step1_actionlint_valid,
                }
                
                step_results.append(result)
            
            # step별 통계 계산
            step_stats = self._calculate_step_statistics(step_results, total_pairs, step_key)
            
            all_step_results[step_key] = {
                'file_pairs_count': total_pairs,
                'results': step_results,
                'stats': step_stats
            }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 전체 요약
        summary = {
            'metadata': {
                'workflows_dir': workflows_dir,
                'processing_time': processing_time,
                'timestamp': datetime.now().isoformat()
            },
            'step_results': all_step_results
        }
        
        # 결과 저장 및 출력
        self.save_comparison_results(summary)
        self.print_comparison_summary(summary)
        
        return summary
    
    def _calculate_step_statistics(self, results: List[Dict], total: int, step_key: str) -> Dict:
        """
        특정 step의 통계 계산
        
        Args:
            results: 평가 결과 리스트
            total: 전체 파일 수
            step_key: 'step2', 'step3', 'step4', 'step5'
        """
        if total == 0:
            return {
                'overall': {},
                'actionlint_passed': {},
                'high_quality': {}
            }
        
        # 1. 전체 파일 통계
        step1_yaml_success = sum(1 for r in results if r['step1_yaml_valid'])
        step1_actionlint_success = sum(1 for r in results if r['step1_actionlint_valid'])
        
        stepN_yaml_success = sum(1 for r in results if r.get(f'{step_key}_yaml_valid', False))
        stepN_actionlint_success = sum(1 for r in results if r.get(f'{step_key}_actionlint_valid', False))
        
        yaml_improved = sum(1 for r in results if r['yaml_improved'])
        actionlint_improved = sum(1 for r in results if r['actionlint_improved'])
        
        valid_bleu = [r['bleu_score'] for r in results if r['bleu_score'] >= 0]
        valid_edit = [r['edit_distance'] for r in results if r['edit_distance'] >= 0]
        
        overall_stats = {
            'total_files': total,
            'step1': {
                'yaml_success': step1_yaml_success,
                'yaml_success_rate': (step1_yaml_success / total * 100) if total > 0 else 0,
                'actionlint_success': step1_actionlint_success,
                'actionlint_success_rate': (step1_actionlint_success / total * 100) if total > 0 else 0,
            },
            f'{step_key}': {
                'yaml_success': stepN_yaml_success,
                'yaml_success_rate': (stepN_yaml_success / total * 100) if total > 0 else 0,
                'actionlint_success': stepN_actionlint_success,
                'actionlint_success_rate': (stepN_actionlint_success / total * 100) if total > 0 else 0,
            },
            'improvement': {
                'yaml_improved_count': yaml_improved,
                'yaml_improvement_rate': (yaml_improved / total * 100) if total > 0 else 0,
                'actionlint_improved_count': actionlint_improved,
                'actionlint_improvement_rate': (actionlint_improved / total * 100) if total > 0 else 0,
            },
            'similarity': {
                'avg_bleu': sum(valid_bleu) / len(valid_bleu) if valid_bleu else 0,
                'min_bleu': min(valid_bleu) if valid_bleu else 0,
                'max_bleu': max(valid_bleu) if valid_bleu else 0,
                'avg_edit_distance': sum(valid_edit) / len(valid_edit) if valid_edit else 0,
            }
        }
        
        # 2. actionlint 통과 파일 통계
        actionlint_passed = [r for r in results if r.get(f'{step_key}_actionlint_valid', False)]
        actionlint_count = len(actionlint_passed)
        
        if actionlint_count > 0:
            actionlint_bleu = [r['bleu_score'] for r in actionlint_passed if r['bleu_score'] >= 0]
            
            bleu_ranges = {
                '0.95-1.00': sum(1 for b in actionlint_bleu if 0.95 <= b <= 1.00),
                '0.90-0.95': sum(1 for b in actionlint_bleu if 0.90 <= b < 0.95),
                '0.85-0.90': sum(1 for b in actionlint_bleu if 0.85 <= b < 0.90),
                '0.80-0.85': sum(1 for b in actionlint_bleu if 0.80 <= b < 0.85),
                '0.70-0.80': sum(1 for b in actionlint_bleu if 0.70 <= b < 0.80),
                '< 0.70': sum(1 for b in actionlint_bleu if b < 0.70),
            }
            
            actionlint_stats = {
                'count': actionlint_count,
                'percentage_of_all': (actionlint_count / total * 100) if total > 0 else 0,
                'avg_bleu': sum(actionlint_bleu) / len(actionlint_bleu) if actionlint_bleu else 0,
                'min_bleu': min(actionlint_bleu) if actionlint_bleu else 0,
                'max_bleu': max(actionlint_bleu) if actionlint_bleu else 0,
                'bleu_distribution': bleu_ranges
            }
        else:
            actionlint_stats = {
                'count': 0,
                'percentage_of_all': 0,
                'avg_bleu': 0,
                'min_bleu': 0,
                'max_bleu': 0,
                'bleu_distribution': {}
            }
        
        # 3. 고품질 파일 통계 (actionlint + BLEU >= 0.85)
        high_quality = [r for r in actionlint_passed if r['bleu_score'] >= 0.85]
        hq_count = len(high_quality)
        
        if hq_count > 0:
            hq_bleu = [r['bleu_score'] for r in high_quality if r['bleu_score'] >= 0]
            hq_edit = [r['edit_distance'] for r in high_quality if r['edit_distance'] >= 0]
            
            high_quality_stats = {
                'count': hq_count,
                'percentage_of_all': (hq_count / total * 100) if total > 0 else 0,
                'percentage_of_actionlint_passed': (hq_count / actionlint_count * 100) if actionlint_count > 0 else 0,
                'avg_bleu': sum(hq_bleu) / len(hq_bleu) if hq_bleu else 0,
                'min_bleu': min(hq_bleu) if hq_bleu else 0,
                'max_bleu': max(hq_bleu) if hq_bleu else 0,
                'avg_edit_distance': sum(hq_edit) / len(hq_edit) if hq_edit else 0,
                'min_edit_distance': min(hq_edit) if hq_edit else 0,
                'max_edit_distance': max(hq_edit) if hq_edit else 0,
            }
        else:
            high_quality_stats = {
                'count': 0,
                'percentage_of_all': 0,
                'percentage_of_actionlint_passed': 0,
                'avg_bleu': 0,
                'min_bleu': 0,
                'max_bleu': 0,
                'avg_edit_distance': 0,
                'min_edit_distance': 0,
                'max_edit_distance': 0,
            }
        
        return {
            'overall': overall_stats,
            'actionlint_passed': actionlint_stats,
            'high_quality': high_quality_stats
        }
    
    def _calculate_overall_stats(self, results: List[Dict], total: int) -> Dict:
        """전체 파일 통계 계산"""
        step1_yaml_success = sum(1 for r in results if r['step1_yaml_valid'])
        step1_actionlint_success = sum(1 for r in results if r['step1_actionlint_valid'])
        
        step2_yaml_success = sum(1 for r in results if r['step2_yaml_valid'])
        step2_actionlint_success = sum(1 for r in results if r['step2_actionlint_valid'])
        
        yaml_improved = sum(1 for r in results if r['yaml_improved'])
        actionlint_improved = sum(1 for r in results if r['actionlint_improved'])
        
        valid_bleu = [r['bleu_score'] for r in results if r['bleu_score'] >= 0]
        valid_edit = [r['edit_distance'] for r in results if r['edit_distance'] >= 0]
        
        return {
            'total_files': total,
            'step1': {
                'yaml_success': step1_yaml_success,
                'yaml_success_rate': (step1_yaml_success / total * 100) if total > 0 else 0,
                'actionlint_success': step1_actionlint_success,
                'actionlint_success_rate': (step1_actionlint_success / total * 100) if total > 0 else 0,
            },
            'step2': {
                'yaml_success': step2_yaml_success,
                'yaml_success_rate': (step2_yaml_success / total * 100) if total > 0 else 0,
                'actionlint_success': step2_actionlint_success,
                'actionlint_success_rate': (step2_actionlint_success / total * 100) if total > 0 else 0,
            },
            'improvement': {
                'yaml_improved_count': yaml_improved,
                'yaml_improvement_rate': (yaml_improved / total * 100) if total > 0 else 0,
                'actionlint_improved_count': actionlint_improved,
                'actionlint_improvement_rate': (actionlint_improved / total * 100) if total > 0 else 0,
            },
            'similarity': {
                'avg_bleu': sum(valid_bleu) / len(valid_bleu) if valid_bleu else 0,
                'min_bleu': min(valid_bleu) if valid_bleu else 0,
                'max_bleu': max(valid_bleu) if valid_bleu else 0,
                'avg_edit_distance': sum(valid_edit) / len(valid_edit) if valid_edit else 0,
            }
        }
    
    def _calculate_actionlint_passed_stats(self, results: List[Dict], total: int) -> Dict:
        """actionlint 통과 파일만의 통계"""
        if total == 0:
            return {
                'count': 0,
                'percentage_of_all': 0,
                'avg_bleu': 0,
                'min_bleu': 0,
                'max_bleu': 0,
                'bleu_distribution': {}
            }
        
        valid_bleu = [r['bleu_score'] for r in results if r['bleu_score'] >= 0]
        
        # BLEU 분포 계산
        bleu_ranges = {
            '0.95-1.00': sum(1 for b in valid_bleu if 0.95 <= b <= 1.00),
            '0.90-0.95': sum(1 for b in valid_bleu if 0.90 <= b < 0.95),
            '0.85-0.90': sum(1 for b in valid_bleu if 0.85 <= b < 0.90),
            '0.80-0.85': sum(1 for b in valid_bleu if 0.80 <= b < 0.85),
            '0.70-0.80': sum(1 for b in valid_bleu if 0.70 <= b < 0.80),
            '< 0.70': sum(1 for b in valid_bleu if b < 0.70),
        }
        
        return {
            'count': total,
            'percentage_of_all': 0,  # 전체 대비 비율은 나중에 계산
            'avg_bleu': sum(valid_bleu) / len(valid_bleu) if valid_bleu else 0,
            'min_bleu': min(valid_bleu) if valid_bleu else 0,
            'max_bleu': max(valid_bleu) if valid_bleu else 0,
            'bleu_distribution': bleu_ranges
        }
    
    def _calculate_high_quality_stats(self, results: List[Dict], total: int) -> Dict:
        """actionlint 통과 + BLEU >= 0.85 파일 통계"""
        if total == 0:
            return {
                'count': 0,
                'percentage_of_all': 0,
                'percentage_of_actionlint_passed': 0,
                'avg_bleu': 0,
                'min_bleu': 0,
                'max_bleu': 0,
            }
        
        valid_bleu = [r['bleu_score'] for r in results if r['bleu_score'] >= 0]
        
        return {
            'count': total,
            'percentage_of_all': 0,  # 전체 대비 비율은 나중에 계산
            'percentage_of_actionlint_passed': 0,  # actionlint 통과 대비 비율은 나중에 계산
            'avg_bleu': sum(valid_bleu) / len(valid_bleu) if valid_bleu else 0,
            'min_bleu': min(valid_bleu) if valid_bleu else 0,
            'max_bleu': max(valid_bleu) if valid_bleu else 0,
        }
    
    def save_comparison_results(self, summary: Dict):
        """비교 결과를 JSON과 CSV로 저장 (step별로)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장 (전체)
        json_file = self.output_dir / f"all_workflows_comparison_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON 결과 저장: {json_file}")
        
        # 각 step별로 CSV 저장
        for step_key in ['step2', 'step3', 'step4', 'step5']:
            step_data = summary['step_results'].get(step_key, {})
            
            if not step_data or step_data.get('file_pairs_count', 0) == 0:
                self.logger.info(f"{step_key}: 데이터 없음, CSV 생성 건너뜀")
                continue
            
            results = step_data.get('results', [])
            stats = step_data.get('stats', {})
            
            # 상세 결과 CSV
            csv_file = self.output_dir / f"{step_key}_comparison_{timestamp}.csv"
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 헤더
                writer.writerow([
                    'base_name', 'step1_file', f'{step_key}_file',
                    'step1_yaml_valid', 'step1_actionlint_valid',
                    'step1_syntax_errors', 'step1_expression_errors',
                    f'{step_key}_yaml_valid', f'{step_key}_actionlint_valid',
                    f'{step_key}_syntax_errors', f'{step_key}_expression_errors',
                    'yaml_improved', 'actionlint_improved',
                    'edit_distance', 'bleu_score',
                    'is_actionlint_passed', 'is_high_quality'
                ])
                
                # 데이터
                for r in results:
                    is_actionlint_passed = r.get(f'{step_key}_actionlint_valid', False)
                    is_high_quality = is_actionlint_passed and r['bleu_score'] >= 0.85
                    
                    writer.writerow([
                        r['base_name'],
                        r['step1_file'],
                        r.get(f'{step_key}_file', ''),
                        r['step1_yaml_valid'],
                        r['step1_actionlint_valid'],
                        r['step1_syntax_error_count'],
                        r['step1_expression_error_count'],
                        r.get(f'{step_key}_yaml_valid', False),
                        r.get(f'{step_key}_actionlint_valid', False),
                        r.get(f'{step_key}_syntax_error_count', 0),
                        r.get(f'{step_key}_expression_error_count', 0),
                        r['yaml_improved'],
                        r['actionlint_improved'],
                        r['edit_distance'],
                        f"{r['bleu_score']:.4f}" if r['bleu_score'] >= 0 else "N/A",
                        is_actionlint_passed,
                        is_high_quality
                    ])
            
            self.logger.info(f"{step_key} CSV 상세 결과 저장: {csv_file}")
            
            # 통계 요약 CSV
            if stats:
                stats_csv = self.output_dir / f"{step_key}_stats_{timestamp}.csv"
                with open(stats_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Category', 'Metric', 'Value'])
                    
                    overall = stats.get('overall', {})
                    actionlint = stats.get('actionlint_passed', {})
                    hq = stats.get('high_quality', {})
                    
                    # 전체 통계
                    if overall:
                        writer.writerow(['Overall', 'Total Files', overall.get('total_files', 0)])
                        stepN_data = overall.get(step_key, {})
                        writer.writerow(['Overall', f'{step_key.upper()} YAML Success Rate', 
                                       f"{stepN_data.get('yaml_success_rate', 0):.2f}%"])
                        writer.writerow(['Overall', f'{step_key.upper()} actionlint Success Rate', 
                                       f"{stepN_data.get('actionlint_success_rate', 0):.2f}%"])
                        similarity = overall.get('similarity', {})
                        writer.writerow(['Overall', 'Average BLEU Score', 
                                       f"{similarity.get('avg_bleu', 0):.4f}"])
                    
                    # actionlint 통과 파일
                    if actionlint:
                        writer.writerow(['Actionlint Passed', 'Count', actionlint.get('count', 0)])
                        writer.writerow(['Actionlint Passed', 'Percentage of All', 
                                       f"{actionlint.get('percentage_of_all', 0):.2f}%"])
                        writer.writerow(['Actionlint Passed', 'Average BLEU', 
                                       f"{actionlint.get('avg_bleu', 0):.4f}"])
                    
                    # 고품질 파일
                    if hq:
                        writer.writerow(['High Quality (actionlint + BLEU>=0.85)', 'Count', hq.get('count', 0)])
                        writer.writerow(['High Quality', 'Percentage of All', 
                                       f"{hq.get('percentage_of_all', 0):.2f}%"])
                        writer.writerow(['High Quality', 'Percentage of Actionlint Passed', 
                                       f"{hq.get('percentage_of_actionlint_passed', 0):.2f}%"])
                        writer.writerow(['High Quality', 'Average BLEU', 
                                       f"{hq.get('avg_bleu', 0):.4f}"])
                        writer.writerow(['High Quality', 'Average Edit Distance', 
                                       f"{hq.get('avg_edit_distance', 0):.2f}"])
                        writer.writerow(['High Quality', 'Edit Distance Range', 
                                       f"{hq.get('min_edit_distance', 0):.0f} ~ {hq.get('max_edit_distance', 0):.0f}"])
                
                self.logger.info(f"{step_key} CSV 통계 요약 저장: {stats_csv}")
            
            # 고품질 파일 목록 CSV 저장
            high_quality_files = [r for r in results 
                                 if r.get(f'{step_key}_actionlint_valid', False) 
                                 and r['bleu_score'] >= 0.85]
            
            if high_quality_files:
                hq_csv = self.output_dir / f"{step_key}_high_quality_files_{timestamp}.csv"
                with open(hq_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # 헤더
                    writer.writerow([
                        'base_name', 'step1_file', f'{step_key}_file',
                        'bleu_score', 'edit_distance',
                        'step1_syntax_errors', 'step1_expression_errors',
                        f'{step_key}_syntax_errors', f'{step_key}_expression_errors',
                        'yaml_improved', 'actionlint_improved'
                    ])
                    
                    # 데이터 (BLEU 점수 높은 순으로 정렬)
                    sorted_files = sorted(high_quality_files, key=lambda x: x['bleu_score'], reverse=True)
                    
                    for r in sorted_files:
                        writer.writerow([
                            r['base_name'],
                            r['step1_file'],
                            r.get(f'{step_key}_file', ''),
                            f"{r['bleu_score']:.4f}",
                            r['edit_distance'],
                            r['step1_syntax_error_count'],
                            r['step1_expression_error_count'],
                            r.get(f'{step_key}_syntax_error_count', 0),
                            r.get(f'{step_key}_expression_error_count', 0),
                            r['yaml_improved'],
                            r['actionlint_improved']
                        ])
                
                self.logger.info(f"{step_key} 고품질 파일 목록 저장: {hq_csv} ({len(high_quality_files)}개)")
    
    def print_comparison_summary(self, summary: Dict):
        """비교 결과 요약 출력 (step별로)"""
        print("\n" + "=" * 80)
        print("전체 워크플로우 비교 평가 결과 (Step별)")
        print("=" * 80)
        
        metadata = summary['metadata']
        if 'workflows_dir' in metadata:
            print(f"\n📁 분석 위치: {metadata['workflows_dir']}")
        elif 'step_dirs' in metadata:
            print(f"\n📁 Step 디렉토리:")
            for step_name, step_path in metadata['step_dirs'].items():
                print(f"  {step_name}: {step_path}")
        
        print(f"⏱️  총 처리 시간: {metadata['processing_time']:.2f}초")
        
        # 각 step별로 출력
        for step_key in ['step2', 'step3', 'step4', 'step5']:
            step_data = summary['step_results'].get(step_key, {})
            
            if not step_data or step_data.get('file_pairs_count', 0) == 0:
                print(f"\n{'='*80}")
                print(f"{step_key.upper()}: 데이터 없음")
                print(f"{'='*80}")
                continue
            
            total = step_data['file_pairs_count']
            stats = step_data.get('stats', {})
            
            if not stats:
                continue
            
            overall = stats.get('overall', {})
            actionlint = stats.get('actionlint_passed', {})
            hq = stats.get('high_quality', {})
            
            print("\n" + "=" * 80)
            print(f"📊 {step_key.upper()} 비교 결과")
            print("=" * 80)
            print(f"총 파일 쌍: {total}")
            
            # 1. 전체 파일 통계
            if overall:
                print(f"\n1️⃣  전체 파일 통계")
                print("-" * 80)
                
                stepN_data = overall.get(step_key, {})
                print(f"\n{step_key.upper()} 성공률:")
                print(f"  YAML 파싱: {stepN_data.get('yaml_success', 0)}/{total} "
                      f"({stepN_data.get('yaml_success_rate', 0):.2f}%)")
                print(f"  actionlint: {stepN_data.get('actionlint_success', 0)}/{total} "
                      f"({stepN_data.get('actionlint_success_rate', 0):.2f}%)")
                
                improvement = overall.get('improvement', {})
                print(f"\n개선율:")
                print(f"  YAML 개선: {improvement.get('yaml_improved_count', 0)}개 파일 "
                      f"({improvement.get('yaml_improvement_rate', 0):.2f}%)")
                print(f"  actionlint 개선: {improvement.get('actionlint_improved_count', 0)}개 파일 "
                      f"({improvement.get('actionlint_improvement_rate', 0):.2f}%)")
                
                similarity = overall.get('similarity', {})
                print(f"\n유사도:")
                print(f"  평균 BLEU: {similarity.get('avg_bleu', 0):.4f}")
                print(f"  BLEU 범위: {similarity.get('min_bleu', 0):.4f} ~ "
                      f"{similarity.get('max_bleu', 0):.4f}")
                print(f"  평균 Edit Distance: {similarity.get('avg_edit_distance', 0):.1f}")
            
            # 2. actionlint 통과 파일 통계
            if actionlint and actionlint.get('count', 0) > 0:
                print(f"\n2️⃣  actionlint 통과 파일 통계")
                print("-" * 80)
                
                print(f"\n통과한 파일 수: {actionlint['count']}/{total} "
                      f"({actionlint.get('percentage_of_all', 0):.2f}%)")
                print(f"평균 BLEU: {actionlint.get('avg_bleu', 0):.4f}")
                print(f"BLEU 범위: {actionlint.get('min_bleu', 0):.4f} ~ "
                      f"{actionlint.get('max_bleu', 0):.4f}")
                
                bleu_dist = actionlint.get('bleu_distribution', {})
                if bleu_dist:
                    print(f"\nBLEU 분포:")
                    for range_name, count in bleu_dist.items():
                        percentage = (count / actionlint['count'] * 100) if actionlint['count'] > 0 else 0
                        print(f"  {range_name}: {count}개 ({percentage:.1f}%)")
            
            # 3. 고품질 파일 통계
            if hq and hq.get('count', 0) > 0:
                print(f"\n3️⃣  고품질 파일 통계 (actionlint 통과 + BLEU >= 0.85)")
                print("-" * 80)
                
                print(f"\n고품질 파일 수: {hq['count']}/{total} "
                      f"({hq.get('percentage_of_all', 0):.2f}%)")
                if actionlint.get('count', 0) > 0:
                    print(f"actionlint 통과 파일 중: {hq['count']}/{actionlint['count']} "
                          f"({hq.get('percentage_of_actionlint_passed', 0):.2f}%)")
                print(f"평균 BLEU: {hq.get('avg_bleu', 0):.4f}")
                print(f"BLEU 범위: {hq.get('min_bleu', 0):.4f} ~ {hq.get('max_bleu', 0):.4f}")
                print(f"평균 Edit Distance: {hq.get('avg_edit_distance', 0):.2f}")
                print(f"Edit Distance 범위: {hq.get('min_edit_distance', 0):.0f} ~ {hq.get('max_edit_distance', 0):.0f}")
        
        print("\n" + "=" * 80)
        print("🎉 비교 평가 완료!")
        print("=" * 80)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="전체 워크플로우 파일 비교 평가 도구")
    
    parser.add_argument("--step1-dir", default="/Users/nam/step1", 
                       help="Step1 파일 디렉토리 (기본: /Users/nam/step1)")
    parser.add_argument("--step2-dir", default="/Users/nam/step2", 
                       help="Step2 파일 디렉토리 (기본: /Users/nam/step2)")
    parser.add_argument("--step3-dir", default="/Users/nam/step3", 
                       help="Step3 파일 디렉토리 (기본: /Users/nam/step3)")
    parser.add_argument("--step4-dir", default="/Users/nam/step4", 
                       help="Step4 파일 디렉토리 (기본: /Users/nam/step4)")
    parser.add_argument("--step5-dir", default="/Users/nam/step5", 
                       help="Step5 파일 디렉토리 (기본: /Users/nam/step5)")
    parser.add_argument("--max-files", type=int, 
                       help="평가할 최대 파일 수")
    parser.add_argument("--csv-file", default="/Users/nam/Desktop/repository/Catching-Smells/data/all_steps.csv",
                       help="Step 매핑 CSV 파일 (기본: all_steps.csv)")
    parser.add_argument("--output-dir", default="./evaluation/all_workflows_comparison",
                       help="출력 디렉토리 (기본: ./evaluation/all_workflows_comparison)")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        comparator = AllWorkflowsComparator(args.output_dir)
        
        step_dirs = {
            'step1': args.step1_dir,
            'step2': args.step2_dir,
            'step3': args.step3_dir,
            'step4': args.step4_dir,
            'step5': args.step5_dir,
        }
        
        summary = comparator.compare_all_workflows_by_dirs(
            step_dirs,
            csv_file=args.csv_file,
            max_files=args.max_files
        )
        
        print(f"\n📁 결과 저장 위치: {args.output_dir}")
        
    except Exception as e:
        logging.error(f"비교 평가 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
베이스라인 평가 시스템

3가지 평가 지표를 측정합니다:
1. 구문 성공률 (Syntax Success Rate %)
2. 타겟 스멜 제거율 (Target Smell Removal Rate %)
3. 수정 범위 적절성 (Edit Scope Appropriateness)
"""

import logging
import json
import csv
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import difflib

# 로컬 모듈 임포트
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import process_runner, yaml_parser


@dataclass
class EvaluationResult:
    """단일 파일에 대한 평가 결과"""
    file_path: str
    original_file: str
    repaired_file: str
    
    # 1. 구문 성공률
    syntax_success: bool
    actionlint_errors: List[Dict]
    
    # 2. 타겟 스멜 제거율
    initial_smells_count: int
    final_smells_count: int
    smell_removal_rate: float
    
    # 3. 수정 범위 적절성
    edit_distance: int
    
    # 메타데이터
    evaluation_time: str
    processing_time: float
    error_message: Optional[str] = None


@dataclass
class GroupEvaluationSummary:
    """그룹 전체 평가 요약"""
    group_name: str
    total_files: int
    
    # 1. 구문 성공률
    syntax_success_count: int
    syntax_success_rate: float
    
    # 2. 타겟 스멜 제거율
    avg_smell_removal_rate: float
    
    # 3. 수정 범위 적절성
    avg_edit_distance: float
    
    # 상세 통계
    detailed_results: List[EvaluationResult]
    evaluation_time: str


class BaselineEvaluator:
    """베이스라인 평가 클래스"""
    
    def __init__(self, output_dir: str = "./evaluation_results"):
        """
        Args:
            output_dir: 평가 결과를 저장할 디렉토리
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 타겟 스멜 번호 (baseline과 동일)
        self.TARGET_SMELLS = {'1', '4', '5', '10', '11', '15', '16'}
        
    def evaluate_file(self, original_file: str, repaired_file: str) -> EvaluationResult:
        """
        단일 파일 쌍을 평가합니다.
        
        Args:
            original_file: 원본 YAML 파일 경로
            repaired_file: 수정된 YAML 파일 경로
            
        Returns:
            EvaluationResult: 평가 결과
        """
        start_time = datetime.now()
        self.logger.info(f"파일 평가 시작: {original_file} -> {repaired_file}")
        
        try:
            # 1. 구문 성공률 평가
            syntax_success, actionlint_errors = self._evaluate_syntax_success(repaired_file)
            
            # 2. 타겟 스멜 제거율 평가
            initial_smells, final_smells, removal_rate = self._evaluate_smell_removal(
                original_file, repaired_file, syntax_success
            )
            
            # 3. 수정 범위 적절성 평가
            edit_distance = self._calculate_edit_distance(original_file, repaired_file)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = EvaluationResult(
                file_path=original_file,
                original_file=original_file,
                repaired_file=repaired_file,
                syntax_success=syntax_success,
                actionlint_errors=actionlint_errors,
                initial_smells_count=initial_smells,
                final_smells_count=final_smells,
                smell_removal_rate=removal_rate,
                edit_distance=edit_distance,
                evaluation_time=start_time.isoformat(),
                processing_time=processing_time
            )
            
            self.logger.info(f"파일 평가 완료: {processing_time:.2f}초")
            return result
            
        except Exception as e:
            self.logger.error(f"파일 평가 중 오류: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return EvaluationResult(
                file_path=original_file,
                original_file=original_file,
                repaired_file=repaired_file,
                syntax_success=False,
                actionlint_errors=[],
                initial_smells_count=0,
                final_smells_count=0,
                smell_removal_rate=0.0,
                edit_distance=0,
                evaluation_time=start_time.isoformat(),
                processing_time=processing_time,
                error_message=str(e)
            )
    
    def _evaluate_syntax_success(self, repaired_file: str) -> Tuple[bool, List[Dict]]:
        """구문 성공률 평가"""
        self.logger.debug(f"구문 검사 시작: {repaired_file}")
        
        # actionlint 실행
        result = process_runner.run_actionlint(repaired_file)
        
        if result.get("success", True):
            # 성공: 오류 없음
            self.logger.debug("구문 검사 통과")
            return True, []
        else:
            # 실패: 오류 있음
            errors = result.get("errors", [])
            
            # syntax-check와 expression 타입의 오류만 구문 오류로 간주
            syntax_errors = [
                error for error in errors 
                if isinstance(error, dict) and error.get('kind') in ['syntax-check', 'expression']
            ]
            
            self.logger.debug(f"구문 오류 {len(syntax_errors)}개 발견 (syntax-check, expression만)")
            if syntax_errors:
                self.logger.debug(f"구문 오류 종류: {[e.get('kind', 'unknown') for e in syntax_errors[:3]]}")
            
            return len(syntax_errors) == 0, syntax_errors
    
    def _evaluate_smell_removal(self, original_file: str, repaired_file: str, 
                               syntax_success: bool) -> Tuple[int, int, float]:
        """타겟 스멜 제거율 평가"""
        self.logger.debug(f"스멜 제거율 평가 시작: {original_file} -> {repaired_file}")
        
        if not syntax_success:
            # 구문 실패한 파일은 0% 처리
            self.logger.debug("구문 실패로 인한 스멜 제거율 0%")
            return 0, 0, 0.0
        
        try:
            # 원본 파일의 타겟 스멜 개수
            original_result = process_runner.run_smell_detector(original_file)
            original_smells = self._count_target_smells(original_result.get("smells", []))
            
            # 수정된 파일의 타겟 스멜 개수
            repaired_result = process_runner.run_smell_detector(repaired_file)
            final_smells = self._count_target_smells(repaired_result.get("smells", []))
            
            # 제거율 계산
            if original_smells == 0:
                # 원본에 스멜이 없었던 경우
                if final_smells == 0:
                    removal_rate = 100.0  # 완벽 상태 유지
                else:
                    removal_rate = 0.0    # 새로운 스멜 생성 (실패)
                    self.logger.debug(f"스멜 추가됨: 0 -> {final_smells}")
            else:
                # 원본에 스멜이 있었던 경우
                if final_smells <= original_smells:
                    removal_rate = ((original_smells - final_smells) / original_smells) * 100.0
                else:
                    # 스멜이 늘어난 경우: 0%로 처리 (실패)
                    removal_rate = 0.0
                    self.logger.debug(f"스멜 증가: {original_smells} -> {final_smells}")
            
            self.logger.debug(f"스멜 변화: {original_smells} -> {final_smells} (제거율: {removal_rate:.1f}%)")
            return original_smells, final_smells, removal_rate
            
        except Exception as e:
            self.logger.error(f"스멜 제거율 평가 중 오류: {e}")
            return 0, 0, 0.0
    
    def _count_target_smells(self, smells: List[Dict]) -> int:
        """타겟 스멜만 카운트"""
        target_count = 0
        for smell in smells:
            if isinstance(smell, dict):
                message = smell.get('message', '')
                # 스멜 번호 추출 (예: "- 10. Avoid jobs without timeouts")
                for target_num in self.TARGET_SMELLS:
                    if f"- {target_num}." in message or f"#{target_num}" in message:
                        target_count += 1
                        break
        return target_count
    
    def _calculate_edit_distance(self, original_file: str, repaired_file: str) -> int:
        """수정 범위 적절성 (Edit Distance) 계산"""
        self.logger.debug(f"Edit Distance 계산: {original_file} -> {repaired_file}")
        
        try:
            # 파일 내용 읽기
            with open(original_file, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
            
            with open(repaired_file, 'r', encoding='utf-8') as f:
                repaired_lines = f.readlines()
            
            # SequenceMatcher를 사용한 유사도 기반 거리 계산
            matcher = difflib.SequenceMatcher(None, original_lines, repaired_lines)
            
            # 편집 거리 근사 계산 (삽입 + 삭제 + 교체)
            opcodes = matcher.get_opcodes()
            edit_distance = 0
            
            for op, i1, i2, j1, j2 in opcodes:
                if op == 'replace':
                    edit_distance += max(i2 - i1, j2 - j1)
                elif op == 'delete':
                    edit_distance += i2 - i1
                elif op == 'insert':
                    edit_distance += j2 - j1
                # 'equal'인 경우는 거리에 추가하지 않음
            
            self.logger.debug(f"Edit Distance: {edit_distance}")
            return edit_distance
            
        except Exception as e:
            self.logger.error(f"Edit Distance 계산 중 오류: {e}")
            return 0
    
    def evaluate_group(self, file_pairs: List[Tuple[str, str]], 
                      group_name: str = "baseline") -> GroupEvaluationSummary:
        """
        파일 그룹 전체를 평가합니다.
        
        Args:
            file_pairs: (원본파일, 수정파일) 쌍의 리스트
            group_name: 그룹 이름
            
        Returns:
            GroupEvaluationSummary: 그룹 평가 요약
        """
        self.logger.info(f"그룹 평가 시작: {group_name} ({len(file_pairs)}개 파일)")
        
        detailed_results = []
        syntax_success_count = 0
        total_smell_removal_rate = 0.0
        total_edit_distance = 0.0
        successful_files_for_edit = 0
        
        for original_file, repaired_file in file_pairs:
            result = self.evaluate_file(original_file, repaired_file)
            detailed_results.append(result)
            
            # 통계 누적
            if result.syntax_success:
                syntax_success_count += 1
                total_edit_distance += result.edit_distance
                successful_files_for_edit += 1
            
            total_smell_removal_rate += result.smell_removal_rate
        
        # 평균 계산
        total_files = len(file_pairs)
        syntax_success_rate = (syntax_success_count / total_files) * 100.0 if total_files > 0 else 0.0
        avg_smell_removal_rate = total_smell_removal_rate / total_files if total_files > 0 else 0.0
        avg_edit_distance = total_edit_distance / successful_files_for_edit if successful_files_for_edit > 0 else 0.0
        
        summary = GroupEvaluationSummary(
            group_name=group_name,
            total_files=total_files,
            syntax_success_count=syntax_success_count,
            syntax_success_rate=syntax_success_rate,
            avg_smell_removal_rate=avg_smell_removal_rate,
            avg_edit_distance=avg_edit_distance,
            detailed_results=detailed_results,
            evaluation_time=datetime.now().isoformat()
        )
        
        self.logger.info(f"그룹 평가 완료: {group_name}")
        self.logger.info(f"  구문 성공률: {syntax_success_rate:.1f}% ({syntax_success_count}/{total_files})")
        self.logger.info(f"  평균 스멜 제거율: {avg_smell_removal_rate:.1f}%")
        self.logger.info(f"  평균 Edit Distance: {avg_edit_distance:.1f}")
        
        return summary
    
    def save_results(self, summary: GroupEvaluationSummary) -> Tuple[str, str]:
        """
        평가 결과를 베이스라인 형식과 일치하게 JSON 파일 2개로 저장합니다.
        
        Args:
            summary: 그룹 평가 요약
            
        Returns:
            Tuple[str, str]: (요약 JSON 파일 경로, 상세 JSON 파일 경로)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 통계 계산
        smell_removal_rates = [result.smell_removal_rate for result in summary.detailed_results]
        edit_distances = [result.edit_distance for result in summary.detailed_results 
                         if result.syntax_success]  # 구문 성공한 경우만
        
        import statistics
        
        # 1. 요약 JSON 파일 저장 (베이스라인 형식과 동일)
        summary_data = {
            "evaluation_date": summary.evaluation_time,
            "total_files": summary.total_files,
            "original_directory": "data_original",
            "repaired_directory": "data_repair_two_phase",
            "syntax_success_rate": round(summary.syntax_success_rate, 2),
            "average_smell_removal_rate": round(summary.avg_smell_removal_rate, 2),
            "average_edit_distance": round(summary.avg_edit_distance, 2),
            "syntax_successes": summary.syntax_success_count,
            "syntax_failures": summary.total_files - summary.syntax_success_count,
            "smell_removal_stats": {
                "min": min(smell_removal_rates) if smell_removal_rates else 0.0,
                "max": max(smell_removal_rates) if smell_removal_rates else 0.0,
                "median": statistics.median(smell_removal_rates) if smell_removal_rates else 0.0,
                "stdev": statistics.stdev(smell_removal_rates) if len(smell_removal_rates) > 1 else 0.0
            },
            "edit_distance_stats": {
                "min": min(edit_distances) if edit_distances else 0,
                "max": max(edit_distances) if edit_distances else 0,
                "median": statistics.median(edit_distances) if edit_distances else 0,
                "stdev": statistics.stdev(edit_distances) if len(edit_distances) > 1 else 0.0
            }
        }
        
        summary_file = self.output_dir / f"{summary.group_name}_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        # 2. 상세 JSON 파일 저장 (베이스라인 형식과 동일 - 배열 형태)
        detailed_data = [asdict(result) for result in summary.detailed_results]
        
        detailed_file = self.output_dir / f"{summary.group_name}_detailed_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"결과 저장 완료:")
        self.logger.info(f"  요약 JSON: {summary_file}")
        self.logger.info(f"  상세 JSON: {detailed_file}")
        
        return str(summary_file), str(detailed_file)
    
    def print_summary(self, summary: GroupEvaluationSummary):
        """평가 요약을 콘솔에 출력합니다."""
        print(f"\n📊 {summary.group_name} 그룹 평가 결과")
        print("=" * 50)
        print(f"총 파일 수: {summary.total_files}")
        print()
        print(f"1. 구문 성공률: {summary.syntax_success_rate:.1f}% ({summary.syntax_success_count}/{summary.total_files})")
        print(f"2. 평균 타겟 스멜 제거율: {summary.avg_smell_removal_rate:.1f}%")
        print(f"3. 평균 수정 범위 (Edit Distance): {summary.avg_edit_distance:.1f}")
        print(f"\n평가 완료 시각: {summary.evaluation_time}")


def main():
    """테스트용 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="베이스라인 평가 도구")
    parser.add_argument("--original", required=True, help="원본 파일 경로")
    parser.add_argument("--repaired", required=True, help="수정된 파일 경로")
    parser.add_argument("--output-dir", default="./evaluation_results", help="출력 디렉토리")
    parser.add_argument("--group-name", default="test", help="그룹 이름")
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 평가 실행
    evaluator = BaselineEvaluator(args.output_dir)
    
    file_pairs = [(args.original, args.repaired)]
    summary = evaluator.evaluate_group(file_pairs, args.group_name)
    
    # 결과 출력 및 저장
    evaluator.print_summary(summary)
    evaluator.save_results(summary)


if __name__ == "__main__":
    main()

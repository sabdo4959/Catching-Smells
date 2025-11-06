"""
논리적 동치성 검증기 (Logical Equivalence Verifier)

GitHub Actions 워크플로우의 논리적 실행 조건(트리거, if문, concurrency)이 
원본과 수정본 간에 동치인지 SMT 솔버를 이용해 검증합니다.

Based on the semantic_verifier.md specification:
- 트리거 조건 (`on`) 검증
- 조건부 실행 (`if`) 검증  
- 동시성 제어 (`concurrency`) 검증
- 허용된 스멜 수정 예외 처리
"""

import logging
import yaml
from typing import Dict, Any, List, Tuple, Optional, Union
from pathlib import Path
import json

try:
    from z3 import Solver, Bool, String, sat, unsat, Not, And, Or, Implies
    from z3 import StringVal, BoolVal, IntVal, Contains, Length
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    logging.warning("Z3 not available. SMT verification will be disabled.")


class LogicalVerifier:
    """
    논리적 동치성 검증을 수행하는 클래스
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 허용된 스멜 수정 패턴 (semantic_verifier.md 기반)
        self.allowed_smell_fixes = {
            # Smell 8: 경로 필터 수정
            'path_filter_addition': [
                'paths:', 'paths-ignore:', 'branches:', 'branches-ignore:'
            ],
            # Smell 9, 10, 12: 포크 방지 수정  
            'fork_prevention': [
                'github.repository', 'github.repository_owner', 'github.event.pull_request.head.repo.full_name'
            ],
            # Smell 6, 7: 동시성 제어 수정
            'concurrency_fixes': [
                'concurrency:', 'cancel-in-progress:'
            ]
        }
        
        if not Z3_AVAILABLE:
            self.logger.warning("Z3 solver not available. Logical verification will be limited.")
    
    def verify_logical_equivalence(
        self, 
        original_yaml_path: str, 
        repaired_yaml_content: str,
        target_smells: List[str] = None,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        논리적 동치성 검증 메인 함수
        
        Args:
            original_yaml_path: 원본 YAML 파일 경로
            repaired_yaml_content: 수정된 YAML 내용
            target_smells: 허용된 스멜 수정 목록 (None이면 기본 안전 스멜들 허용)
            strict_mode: True면 target_smells 무시하고 모든 변경 거부
            
        Returns:
            Dict: 검증 결과
        """
        self.logger.info(f"논리적 동치성 검증 시작 (strict_mode: {strict_mode})")
        
        # strict_mode일 때는 target_smells 무시
        if strict_mode:
            effective_smells = []
            self.logger.info("엄격 모드: 모든 논리적 변경을 위험으로 판정")
        elif target_smells is None:
            # 기본적으로 안전한 스멜들은 허용
            effective_smells = ['smell_6', 'smell_7', 'smell_8', 'smell_9', 'smell_10', 'smell_12']
            self.logger.info("기본 모드: 일반적인 스멜 수정들을 허용")
        else:
            effective_smells = target_smells
            self.logger.info(f"사용자 지정 모드: {len(effective_smells)}개 스멜 허용")
        
        try:
            # YAML 파싱
            with open(original_yaml_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            original_yaml = yaml.safe_load(original_content)
            repaired_yaml = yaml.safe_load(repaired_yaml_content)
            
            if not original_yaml or not repaired_yaml:
                return self._create_result(False, "YAML 파싱 실패")
            
            # 3단계 검증 수행
            results = {
                'trigger_verification': self._verify_triggers(original_yaml, repaired_yaml, effective_smells),
                'if_verification': self._verify_if_conditions(original_yaml, repaired_yaml, effective_smells),
                'concurrency_verification': self._verify_concurrency(original_yaml, repaired_yaml, effective_smells)
            }
            
            # 전체 결과 종합
            all_safe = all(result['is_safe'] for result in results.values())
            
            return {
                'is_safe': all_safe,
                'verification_method': 'logical_smt',
                'results': results,
                'summary': self._create_summary(results),
                'z3_available': Z3_AVAILABLE,
                'mode_info': {
                    'strict_mode': strict_mode,
                    'effective_smells': effective_smells,
                    'total_allowed_smells': len(effective_smells)
                }
            }
            
        except Exception as e:
            self.logger.error(f"논리적 검증 중 오류: {e}")
            return self._create_result(False, f"검증 오류: {str(e)}")
    
    def _verify_triggers(
        self, 
        original_yaml: Dict, 
        repaired_yaml: Dict, 
        target_smells: List[str]
    ) -> Dict[str, Any]:
        """
        트리거 조건 (`on`) 검증
        """
        self.logger.info("트리거 조건 검증 중...")
        
        original_on = original_yaml.get('on', {})
        repaired_on = repaired_yaml.get('on', {})
        
        # 기본 구조 비교
        if self._deep_compare_structures(original_on, repaired_on):
            return self._create_result(True, "트리거 조건 동일")
        
        # 허용된 스멜 수정인지 확인
        if self._is_allowed_trigger_change(original_on, repaired_on, target_smells):
            return self._create_result(True, "허용된 트리거 스멜 수정")
        
        # SMT 기반 논리적 동치성 검증
        if Z3_AVAILABLE:
            smt_result = self._verify_trigger_equivalence_smt(original_on, repaired_on)
            return smt_result
        
        return self._create_result(False, "트리거 조건 불일치 (SMT 불가능)")
    
    def _verify_if_conditions(
        self, 
        original_yaml: Dict, 
        repaired_yaml: Dict, 
        target_smells: List[str]
    ) -> Dict[str, Any]:
        """
        조건부 실행 (`if`) 검증
        """
        self.logger.info("if 조건 검증 중...")
        
        # 모든 잡과 스텝의 if 조건을 1:1 매칭하여 검증
        original_jobs = original_yaml.get('jobs', {})
        repaired_jobs = repaired_yaml.get('jobs', {})
        
        unsafe_conditions = []
        
        # 잡 레벨 if 조건 검증
        for job_id in original_jobs.keys():
            if job_id not in repaired_jobs:
                continue
                
            orig_job_if = original_jobs[job_id].get('if', 'true')
            rep_job_if = repaired_jobs[job_id].get('if', 'true')
            
            if not self._verify_single_if_condition(orig_job_if, rep_job_if, target_smells):
                unsafe_conditions.append(f"Job {job_id} if condition mismatch")
        
        # 스텝 레벨 if 조건 검증
        for job_id in original_jobs.keys():
            if job_id not in repaired_jobs:
                continue
                
            orig_steps = original_jobs[job_id].get('steps', [])
            rep_steps = repaired_jobs[job_id].get('steps', [])
            
            min_steps = min(len(orig_steps), len(rep_steps))
            for i in range(min_steps):
                orig_step_if = orig_steps[i].get('if', 'true')
                rep_step_if = rep_steps[i].get('if', 'true')
                
                if not self._verify_single_if_condition(orig_step_if, rep_step_if, target_smells):
                    unsafe_conditions.append(f"Job {job_id} Step {i} if condition mismatch")
        
        if unsafe_conditions:
            return self._create_result(False, f"if 조건 불일치: {unsafe_conditions}")
        
        return self._create_result(True, "모든 if 조건 검증 통과")
    
    def _verify_concurrency(
        self, 
        original_yaml: Dict, 
        repaired_yaml: Dict, 
        target_smells: List[str]
    ) -> Dict[str, Any]:
        """
        동시성 제어 (`concurrency`) 검증
        """
        self.logger.info("동시성 제어 검증 중...")
        
        original_conc = original_yaml.get('concurrency', {})
        repaired_conc = repaired_yaml.get('concurrency', {})
        
        # 기본 구조 비교
        if self._deep_compare_structures(original_conc, repaired_conc):
            return self._create_result(True, "동시성 제어 동일")
        
        # 허용된 스멜 수정인지 확인
        if self._is_allowed_concurrency_change(original_conc, repaired_conc, target_smells):
            return self._create_result(True, "허용된 동시성 스멜 수정")
        
        # SMT 기반 검증
        if Z3_AVAILABLE:
            smt_result = self._verify_concurrency_equivalence_smt(original_conc, repaired_conc)
            return smt_result
        
        return self._create_result(False, "동시성 제어 불일치 (SMT 불가능)")
    
    def _verify_single_if_condition(
        self, 
        original_if: str, 
        repaired_if: str, 
        target_smells: List[str]
    ) -> bool:
        """
        단일 if 조건의 논리적 동치성 검증
        """
        # 문자열 동일성 체크
        if original_if == repaired_if:
            return True
        
        # 허용된 스멜 수정인지 확인
        if self._is_allowed_if_change(original_if, repaired_if, target_smells):
            return True
        
        # SMT 기반 검증
        if Z3_AVAILABLE:
            return self._verify_if_equivalence_smt(original_if, repaired_if)
        
        return False
    
    def _verify_trigger_equivalence_smt(self, original_on: Dict, repaired_on: Dict) -> Dict[str, Any]:
        """
        SMT 솔버를 이용한 트리거 조건 동치성 검증
        """
        try:
            self.logger.info("=== SMT 트리거 검증 시작 ===")
            self.logger.info(f"원본 트리거: {original_on}")
            self.logger.info(f"수정본 트리거: {repaired_on}")
            
            solver = Solver()
            
            # GitHub 컨텍스트 변수 정의
            github_event = String('github_event')
            github_ref = String('github_ref')
            github_ref_name = String('github_ref_name')
            
            self.logger.info("GitHub 컨텍스트 변수 정의 완료")
            
            # 원본과 수정본의 트리거 조건을 SMT 공식으로 변환
            original_formula = self._convert_trigger_to_smt(original_on, github_event, github_ref, github_ref_name)
            repaired_formula = self._convert_trigger_to_smt(repaired_on, github_event, github_ref, github_ref_name)
            
            self.logger.info(f"원본 SMT 공식: {original_formula}")
            self.logger.info(f"수정본 SMT 공식: {repaired_formula}")
            
            # 비동치 조건 추가: Not(original_formula == repaired_formula)
            non_equiv_condition = Not(original_formula == repaired_formula)
            solver.add(non_equiv_condition)
            
            self.logger.info(f"비동치 조건 추가: {non_equiv_condition}")
            self.logger.info("Z3 솔버 실행 중...")
            
            # 검증 실행
            result = solver.check()
            
            self.logger.info(f"Z3 솔버 결과: {result}")
            
            if result == unsat:
                self.logger.info("✅ UNSAT: 트리거 조건이 논리적으로 동치입니다")
                return self._create_result(True, "SMT 검증: 트리거 조건 논리적 동치")
            elif result == sat:
                model = solver.model()
                self.logger.warning(f"❌ SAT: 트리거 조건 불일치 발견")
                self.logger.warning(f"반례 모델: {model}")
                return self._create_result(False, f"SMT 검증: 트리거 조건 불일치, 반례: {model}")
            else:
                self.logger.error(f"⚠️ Z3 검증 결과 불명: {result}")
                return self._create_result(False, f"SMT 검증 실패: {result}")
                
        except Exception as e:
            self.logger.error(f"SMT 트리거 검증 오류: {e}")
            import traceback
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
            return self._create_result(False, f"SMT 검증 오류: {str(e)}")
    
    def _verify_if_equivalence_smt(self, original_if: str, repaired_if: str) -> bool:
        """
        SMT 솔버를 이용한 if 조건 동치성 검증
        """
        try:
            self.logger.debug(f"=== SMT if 조건 검증 ===")
            self.logger.debug(f"원본 if 조건: '{original_if}'")
            self.logger.debug(f"수정본 if 조건: '{repaired_if}'")
            
            solver = Solver()
            
            # GitHub 컨텍스트 변수들
            github_event_name = String('github_event_name')
            github_ref = String('github_ref')
            github_repository = String('github_repository')
            github_actor = String('github_actor')
            
            # if 조건을 SMT 공식으로 변환
            original_formula = self._convert_if_condition_to_smt(
                original_if, github_event_name, github_ref, github_repository, github_actor
            )
            repaired_formula = self._convert_if_condition_to_smt(
                repaired_if, github_event_name, github_ref, github_repository, github_actor
            )
            
            self.logger.debug(f"원본 if SMT 공식: {original_formula}")
            self.logger.debug(f"수정본 if SMT 공식: {repaired_formula}")
            
            # 비동치 조건 추가
            non_equiv_condition = Not(original_formula == repaired_formula)
            solver.add(non_equiv_condition)
            
            self.logger.debug(f"if 조건 비동치 검사: {non_equiv_condition}")
            
            # 검증 실행
            result = solver.check()
            
            self.logger.debug(f"if 조건 Z3 결과: {result}")
            
            if result == unsat:
                self.logger.debug("✅ if 조건 동치성 확인")
                return True
            else:
                if result == sat:
                    model = solver.model()
                    self.logger.debug(f"❌ if 조건 불일치, 반례: {model}")
                else:
                    self.logger.debug(f"⚠️ if 조건 검증 실패: {result}")
                return False
            
        except Exception as e:
            self.logger.error(f"SMT if 검증 오류: {e}")
            return False
    
    def _verify_concurrency_equivalence_smt(self, original_conc: Dict, repaired_conc: Dict) -> Dict[str, Any]:
        """
        SMT 솔버를 이용한 동시성 제어 동치성 검증
        """
        try:
            # 간단한 구조 비교로 대체 (concurrency는 대부분 정적 값)
            if self._deep_compare_structures(original_conc, repaired_conc):
                return self._create_result(True, "동시성 제어 구조 동일")
            else:
                return self._create_result(False, "동시성 제어 구조 불일치")
                
        except Exception as e:
            self.logger.error(f"SMT 동시성 검증 오류: {e}")
            return self._create_result(False, f"동시성 검증 오류: {str(e)}")
    
    def _convert_trigger_to_smt(self, trigger_on: Dict, github_event: Any, github_ref: Any, github_ref_name: Any):
        """
        트리거 조건을 SMT 공식으로 변환
        """
        if not Z3_AVAILABLE:
            self.logger.warning("Z3 사용 불가, BoolVal(True) 반환")
            return BoolVal(True)
        
        self.logger.debug(f"트리거 → SMT 변환 시작: {trigger_on}")
        
        conditions = []
        
        if isinstance(trigger_on, str):
            # 단일 이벤트: on: push
            condition = github_event == StringVal(trigger_on)
            conditions.append(condition)
            self.logger.debug(f"단일 이벤트 조건: {condition}")
            
        elif isinstance(trigger_on, list):
            # 다중 이벤트: on: [push, pull_request]
            event_conditions = [github_event == StringVal(event) for event in trigger_on]
            condition = Or(event_conditions)
            conditions.append(condition)
            self.logger.debug(f"다중 이벤트 조건: {condition}")
            
        elif isinstance(trigger_on, dict):
            # 복합 조건: on: push: branches: [main]
            for event_type, event_config in trigger_on.items():
                event_condition = github_event == StringVal(event_type)
                self.logger.debug(f"이벤트 타입 조건: {event_condition}")
                
                if isinstance(event_config, dict):
                    # 브랜치 필터 등
                    if 'branches' in event_config:
                        branches = event_config['branches']
                        if isinstance(branches, list):
                            branch_conditions = [Contains(github_ref, StringVal(branch)) for branch in branches]
                            branch_condition = Or(branch_conditions)
                            event_condition = And(event_condition, branch_condition)
                            self.logger.debug(f"브랜치 필터 추가: {branch_condition}")
                    
                    if 'paths' in event_config:
                        paths = event_config['paths']
                        self.logger.debug(f"경로 필터 감지: {paths}")
                        # 경로 필터는 현재 단순화하여 True로 처리
                        path_condition = BoolVal(True)  
                        event_condition = And(event_condition, path_condition)
                
                conditions.append(event_condition)
        
        if conditions:
            final_condition = Or(conditions) if len(conditions) > 1 else conditions[0]
            self.logger.debug(f"최종 트리거 SMT 공식: {final_condition}")
            return final_condition
        else:
            self.logger.debug("조건 없음, BoolVal(True) 반환")
            return BoolVal(True)
    
    def _convert_if_condition_to_smt(
        self, 
        if_condition: str, 
        github_event_name: Any,
        github_ref: Any, 
        github_repository: Any,
        github_actor: Any
    ):
        """
        if 조건 문자열을 SMT 공식으로 변환
        """
        if not Z3_AVAILABLE:
            self.logger.warning("Z3 사용 불가, BoolVal(True) 반환")
            return BoolVal(True)
        
        self.logger.debug(f"if 조건 → SMT 변환 시작: '{if_condition}'")
        
        # 기본값 처리
        if not if_condition or if_condition.lower() in ['true', '']:
            self.logger.debug("기본값 True 반환")
            return BoolVal(True)
        if if_condition.lower() == 'false':
            self.logger.debug("기본값 False 반환")
            return BoolVal(False)
        
        # 조건 정리
        if_condition = if_condition.strip()
        
        # && 연산자로 분할하여 복합 조건 처리
        if '&&' in if_condition:
            parts = [part.strip() for part in if_condition.split('&&')]
            conditions = []
            self.logger.debug(f"복합 조건 감지, 부분: {parts}")
            
            for part in parts:
                sub_condition = self._parse_single_condition(part, github_event_name, github_ref, github_repository, github_actor)
                conditions.append(sub_condition)
            
            final_condition = And(conditions)
            self.logger.debug(f"복합 조건 변환 결과: {final_condition}")
            return final_condition
        
        # 단일 조건 처리
        return self._parse_single_condition(if_condition, github_event_name, github_ref, github_repository, github_actor)
    
    def _parse_single_condition(self, condition: str, github_event_name: Any, github_ref: Any, github_repository: Any, github_actor: Any):
        """
        단일 조건을 SMT로 변환
        """
        condition = condition.strip()
        
        # github.event_name == 'push'
        if 'github.event_name' in condition and '==' in condition:
            parts = condition.split('==')
            if len(parts) == 2:
                value = parts[1].strip().strip("'\"")
                smt_condition = github_event_name == StringVal(value)
                self.logger.debug(f"github.event_name 조건 변환: {smt_condition}")
                return smt_condition
        
        # github.ref == 'refs/heads/main'
        if 'github.ref' in condition and '==' in condition:
            parts = condition.split('==')
            if len(parts) == 2:
                value = parts[1].strip().strip("'\"")
                smt_condition = github_ref == StringVal(value)
                self.logger.debug(f"github.ref 조건 변환: {smt_condition}")
                return smt_condition
        
        # contains(github.ref, 'main')
        if 'contains(' in condition and 'github.ref' in condition:
            import re
            match = re.search(r"contains\(\s*github\.ref\s*,\s*['\"]([^'\"]+)['\"]\s*\)", condition)
            if match:
                pattern = match.group(1)
                smt_condition = Contains(github_ref, StringVal(pattern))
                self.logger.debug(f"contains(github.ref) 조건 변환: {smt_condition}")
                return smt_condition
        
        # github.repository == 'owner/repo'
        if 'github.repository' in condition and '==' in condition:
            parts = condition.split('==')
            if len(parts) == 2:
                value = parts[1].strip().strip("'\"")
                smt_condition = github_repository == StringVal(value)
                self.logger.debug(f"github.repository 조건 변환: {smt_condition}")
                return smt_condition
        
        # 기본값: True (파싱 불가능한 경우)
        self.logger.debug(f"파싱 불가능한 조건, BoolVal(True) 반환: '{condition}'")
        return BoolVal(True)
    
    def _is_allowed_trigger_change(
        self, 
        original_on: Dict, 
        repaired_on: Dict, 
        target_smells: List[str]
    ) -> bool:
        """
        허용된 트리거 스멜 수정인지 확인 (Smell 8: 경로 필터)
        """
        if not target_smells or 'smell_8' not in [s.lower() for s in target_smells]:
            return False
        
        # paths, paths-ignore, branches, branches-ignore 추가는 허용
        allowed_additions = self.allowed_smell_fixes['path_filter_addition']
        
        for key in allowed_additions:
            if key in str(repaired_on) and key not in str(original_on):
                self.logger.info(f"허용된 경로 필터 추가 감지: {key}")
                return True
        
        return False
    
    def _is_allowed_if_change(
        self, 
        original_if: str, 
        repaired_if: str, 
        target_smells: List[str]
    ) -> bool:
        """
        허용된 if 조건 스멜 수정인지 확인 (Smell 9, 10, 12: 포크 방지)
        """
        if not target_smells:
            return False
        
        allowed_smells = ['smell_9', 'smell_10', 'smell_12']
        if not any(smell.lower() in [s.lower() for s in target_smells] for smell in allowed_smells):
            return False
        
        # 포크 방지 패턴 추가는 허용
        fork_prevention_patterns = self.allowed_smell_fixes['fork_prevention']
        
        for pattern in fork_prevention_patterns:
            if pattern in repaired_if and pattern not in original_if:
                self.logger.info(f"허용된 포크 방지 조건 추가 감지: {pattern}")
                return True
        
        return False
    
    def _is_allowed_concurrency_change(
        self, 
        original_conc: Dict, 
        repaired_conc: Dict, 
        target_smells: List[str]
    ) -> bool:
        """
        허용된 동시성 제어 스멜 수정인지 확인 (Smell 6, 7)
        """
        if not target_smells:
            return False
        
        allowed_smells = ['smell_6', 'smell_7']
        if not any(smell.lower() in [s.lower() for s in target_smells] for smell in allowed_smells):
            return False
        
        # 원본에 concurrency가 없고 수정본에 추가된 경우는 허용
        if not original_conc and repaired_conc:
            self.logger.info(f"허용된 동시성 제어 추가 감지: concurrency 블록 추가")
            return True
        
        # 동시성 제어 패턴 추가는 허용
        concurrency_patterns = self.allowed_smell_fixes['concurrency_fixes']
        
        repaired_str = str(repaired_conc)
        original_str = str(original_conc)
        
        for pattern in concurrency_patterns:
            if pattern in repaired_str and pattern not in original_str:
                self.logger.info(f"허용된 동시성 제어 추가 감지: {pattern}")
                return True
        
        return False
    
    def _deep_compare_structures(self, obj1: Any, obj2: Any) -> bool:
        """
        깊은 구조 비교
        """
        if type(obj1) != type(obj2):
            return False
        
        if isinstance(obj1, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(self._deep_compare_structures(obj1[k], obj2[k]) for k in obj1.keys())
        
        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            return all(self._deep_compare_structures(obj1[i], obj2[i]) for i in range(len(obj1)))
        
        else:
            return obj1 == obj2
    
    def _create_result(self, is_safe: bool, message: str) -> Dict[str, Any]:
        """
        검증 결과 생성
        """
        return {
            'is_safe': is_safe,
            'message': message,
            'timestamp': self._get_timestamp()
        }
    
    def _create_summary(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """
        검증 결과 요약 생성
        """
        total_checks = len(results)
        passed_checks = sum(1 for result in results.values() if result['is_safe'])
        
        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'pass_rate': passed_checks / total_checks if total_checks > 0 else 0,
            'failed_checks': [name for name, result in results.items() if not result['is_safe']]
        }
    
    def _get_timestamp(self) -> str:
        """
        현재 타임스탬프 반환
        """
        from datetime import datetime
        return datetime.now().isoformat()


def main():
    """
    테스트용 메인 함수
    """
    import sys
    
    if len(sys.argv) != 3:
        print("사용법: python logical_verifier.py <original_yaml> <repaired_yaml>")
        sys.exit(1)
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    verifier = LogicalVerifier()
    
    original_path = sys.argv[1]
    with open(sys.argv[2], 'r', encoding='utf-8') as f:
        repaired_content = f.read()
    
    result = verifier.verify_logical_equivalence(original_path, repaired_content)
    
    print("="*60)
    print("논리적 동치성 검증 결과")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

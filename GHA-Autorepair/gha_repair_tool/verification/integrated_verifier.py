"""
통합 검증기 (Integrated Verifier)

구조적 안전성 검증과 논리적 동치성 검증을 결합하여
완전한 GitHub Actions 워크플로우 수정 안전성을 검증합니다.

Based on semantic_verifier.md:
1. 구조적 동치성 검증 (Structural Equivalence) - 기존 enhanced_key_structure_verifier 활용
2. 논리적 동치성 검증 (Logical Equivalence) - 새로운 logical_verifier 활용
3. 하이브리드 결과 종합 및 최종 판정
"""

import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

try:
    from enhanced_key_structure_verifier import EnhancedKeyStructureVerifier
    STRUCTURAL_VERIFIER_AVAILABLE = True
except ImportError:
    STRUCTURAL_VERIFIER_AVAILABLE = False
    logging.warning("Enhanced structural verifier not available")

try:
    from logical_verifier import LogicalVerifier
    LOGICAL_VERIFIER_AVAILABLE = True
except ImportError:
    LOGICAL_VERIFIER_AVAILABLE = False
    logging.warning("Logical verifier not available")


class IntegratedVerifier:
    """
    구조적 + 논리적 검증을 통합하는 메인 검증기
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 하위 검증기들 초기화
        if STRUCTURAL_VERIFIER_AVAILABLE:
            self.structural_verifier = EnhancedKeyStructureVerifier()
        else:
            self.structural_verifier = None
            
        if LOGICAL_VERIFIER_AVAILABLE:
            self.logical_verifier = LogicalVerifier()
        else:
            self.logical_verifier = None
        
        self.verification_weights = {
            'structural': 0.6,  # 구조적 안전성 가중치
            'logical': 0.4      # 논리적 동치성 가중치
        }
    
    def verify_repair_safety(
        self,
        original_yaml_path: str,
        repaired_yaml_path: str,
        target_smells: List[str] = None,
        verification_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        수정된 워크플로우의 전체 안전성을 검증합니다.
        
        Args:
            original_yaml_path: 원본 YAML 파일 경로
            repaired_yaml_path: 수정된 YAML 파일 경로  
            target_smells: 허용된 스멜 수정 목록
            verification_mode: 검증 모드 ("structural", "logical", "hybrid")
            
        Returns:
            Dict: 통합 검증 결과
        """
        self.logger.info(f"통합 안전성 검증 시작: {verification_mode} 모드")
        
        try:
            # 수정된 YAML 내용 읽기
            with open(repaired_yaml_path, 'r', encoding='utf-8') as f:
                repaired_content = f.read()
            
            if verification_mode == "structural":
                return self._verify_structural_only(original_yaml_path, repaired_yaml_path)
            elif verification_mode == "logical":
                return self._verify_logical_only(original_yaml_path, repaired_content, target_smells)
            elif verification_mode == "hybrid":
                return self._verify_hybrid(original_yaml_path, repaired_yaml_path, repaired_content, target_smells)
            else:
                return self._create_error_result(f"지원하지 않는 검증 모드: {verification_mode}")
                
        except Exception as e:
            self.logger.error(f"통합 검증 중 오류: {e}")
            return self._create_error_result(f"검증 오류: {str(e)}")
    
    def _verify_structural_only(self, original_path: str, repaired_path: str) -> Dict[str, Any]:
        """구조적 검증만 수행"""
        if not self.structural_verifier:
            return self._create_error_result("구조적 검증기를 사용할 수 없습니다")
        
        self.logger.info("구조적 안전성 검증 수행 중...")
        
        try:
            structural_result = self.structural_verifier.verify_structural_safety(original_path, repaired_path)
            structural_safe = structural_result.get('is_safe', False)
            
            return {
                'is_safe': structural_safe,
                'verification_method': 'structural_only',
                'confidence_score': 1.0 if structural_safe else 0.0,
                'structural_result': structural_result,
                'logical_result': None,
                'details': {
                    'structural_weight': 1.0,
                    'logical_weight': 0.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"구조적 검증 오류: {e}")
            return self._create_error_result(f"구조적 검증 실패: {str(e)}")
    
    def _verify_logical_only(
        self, 
        original_path: str, 
        repaired_content: str, 
        target_smells: List[str]
    ) -> Dict[str, Any]:
        """논리적 검증만 수행"""
        if not self.logical_verifier:
            return self._create_error_result("논리적 검증기를 사용할 수 없습니다")
        
        self.logger.info("논리적 동치성 검증 수행 중...")
        
        try:
            logical_result = self.logical_verifier.verify_logical_equivalence(
                original_path, repaired_content, target_smells
            )
            
            return {
                'is_safe': logical_result['is_safe'],
                'verification_method': 'logical_only',
                'confidence_score': 1.0 if logical_result['is_safe'] else 0.0,
                'structural_result': None,
                'logical_result': logical_result,
                'details': {
                    'structural_weight': 0.0,
                    'logical_weight': 1.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"논리적 검증 오류: {e}")
            return self._create_error_result(f"논리적 검증 실패: {str(e)}")
    
    def _verify_hybrid(
        self, 
        original_path: str, 
        repaired_path: str,
        repaired_content: str, 
        target_smells: List[str]
    ) -> Dict[str, Any]:
        """하이브리드 검증 수행 (구조적 + 논리적)"""
        self.logger.info("하이브리드 검증 수행 중...")
        
        results = {}
        
        # 1단계: 구조적 검증
        if self.structural_verifier:
            self.logger.info("[1/2] 구조적 안전성 검증...")
            try:
                structural_result = self.structural_verifier.verify_structural_safety(original_path, repaired_path)
                structural_safe = structural_result.get('is_safe', False)
                results['structural'] = {
                    'is_safe': structural_safe,
                    'method': 'enhanced_key_structure',
                    'confidence': 1.0 if structural_safe else 0.0,
                    'details': structural_result
                }
            except Exception as e:
                self.logger.error(f"구조적 검증 실패: {e}")
                results['structural'] = {
                    'is_safe': False,
                    'method': 'enhanced_key_structure',
                    'confidence': 0.0,
                    'error': str(e)
                }
        else:
            results['structural'] = {
                'is_safe': False,
                'method': 'unavailable',
                'confidence': 0.0,
                'error': 'Structural verifier not available'
            }
        
        # 2단계: 논리적 검증
        if self.logical_verifier:
            self.logger.info("[2/2] 논리적 동치성 검증...")
            try:
                logical_result = self.logical_verifier.verify_logical_equivalence(
                    original_path, repaired_content, target_smells
                )
                results['logical'] = {
                    'is_safe': logical_result['is_safe'],
                    'method': 'smt_equivalence',
                    'confidence': 1.0 if logical_result['is_safe'] else 0.0,
                    'details': logical_result
                }
            except Exception as e:
                self.logger.error(f"논리적 검증 실패: {e}")
                results['logical'] = {
                    'is_safe': False,
                    'method': 'smt_equivalence',
                    'confidence': 0.0,
                    'error': str(e)
                }
        else:
            results['logical'] = {
                'is_safe': False,
                'method': 'unavailable',
                'confidence': 0.0,
                'error': 'Logical verifier not available'
            }
        
        # 3단계: 결과 종합 및 최종 판정
        final_result = self._combine_verification_results(results)
        
        return final_result
    
    def _combine_verification_results(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """
        구조적 + 논리적 검증 결과를 종합하여 최종 판정
        
        판정 규칙 (semantic_verifier.md 기반):
        1. 둘 다 SAFE → SAFE
        2. 하나라도 UNSAFE → UNSAFE  
        3. 가중평균으로 신뢰도 계산
        """
        structural = results.get('structural', {})
        logical = results.get('logical', {})
        
        structural_safe = structural.get('is_safe', False)
        logical_safe = logical.get('is_safe', False)
        
        # 최종 안전성 판정: AND 연산 (둘 다 안전해야 안전)
        final_is_safe = structural_safe and logical_safe
        
        # 신뢰도 계산: 가중평균
        structural_confidence = structural.get('confidence', 0.0)
        logical_confidence = logical.get('confidence', 0.0)
        
        combined_confidence = (
            structural_confidence * self.verification_weights['structural'] +
            logical_confidence * self.verification_weights['logical']
        )
        
        # 검증 실패 원인 분석
        failure_reasons = []
        if not structural_safe:
            failure_reasons.append("구조적 안전성 위반")
        if not logical_safe:
            failure_reasons.append("논리적 동치성 위반")
        
        return {
            'is_safe': final_is_safe,
            'verification_method': 'hybrid',
            'confidence_score': combined_confidence,
            'structural_result': structural,
            'logical_result': logical,
            'summary': {
                'structural_safe': structural_safe,
                'logical_safe': logical_safe,
                'both_safe': final_is_safe,
                'failure_reasons': failure_reasons
            },
            'details': {
                'structural_weight': self.verification_weights['structural'],
                'logical_weight': self.verification_weights['logical'],
                'combined_confidence': combined_confidence
            }
        }
    
    def verify_batch_repairs(
        self,
        original_dir: str,
        repaired_dir: str,
        output_file: str = None,
        target_smells: List[str] = None,
        max_files: int = None
    ) -> Dict[str, Any]:
        """
        배치 수리 검증 수행
        
        Args:
            original_dir: 원본 파일 디렉토리
            repaired_dir: 수정된 파일 디렉토리
            output_file: 결과 저장 파일 (선택사항)
            target_smells: 허용된 스멜 목록
            max_files: 최대 처리 파일 수
            
        Returns:
            Dict: 배치 검증 결과
        """
        self.logger.info(f"배치 검증 시작: {original_dir} vs {repaired_dir}")
        
        original_path = Path(original_dir)
        repaired_path = Path(repaired_dir)
        
        if not original_path.exists() or not repaired_path.exists():
            return self._create_error_result("입력 디렉토리가 존재하지 않습니다")
        
        results = {
            'total_files': 0,
            'processed_files': 0,
            'safe_files': 0,
            'unsafe_files': 0,
            'error_files': 0,
            'file_results': {},
            'summary': {}
        }
        
        # 원본 파일 목록 수집
        original_files = list(original_path.glob('*'))
        if max_files:
            original_files = original_files[:max_files]
        
        results['total_files'] = len(original_files)
        
        for original_file in original_files:
            if not original_file.is_file():
                continue
            
            repaired_file = repaired_path / original_file.name
            if not repaired_file.exists():
                self.logger.warning(f"수정된 파일 없음: {repaired_file}")
                continue
            
            self.logger.info(f"검증 중: {original_file.name}")
            
            try:
                file_result = self.verify_repair_safety(
                    str(original_file),
                    str(repaired_file),
                    target_smells,
                    "hybrid"
                )
                
                results['file_results'][original_file.name] = file_result
                results['processed_files'] += 1
                
                if file_result['is_safe']:
                    results['safe_files'] += 1
                else:
                    results['unsafe_files'] += 1
                    
            except Exception as e:
                self.logger.error(f"파일 검증 오류 {original_file.name}: {e}")
                results['file_results'][original_file.name] = self._create_error_result(str(e))
                results['error_files'] += 1
        
        # 요약 통계 계산
        if results['processed_files'] > 0:
            results['summary'] = {
                'safety_rate': results['safe_files'] / results['processed_files'],
                'error_rate': results['error_files'] / results['total_files'],
                'processing_rate': results['processed_files'] / results['total_files']
            }
        
        # 결과 파일 저장
        if output_file:
            self._save_results(results, output_file)
        
        self.logger.info(f"배치 검증 완료: {results['safe_files']}/{results['processed_files']} 안전")
        
        return results
    
    def _save_results(self, results: Dict[str, Any], output_file: str):
        """검증 결과를 파일에 저장"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.logger.info(f"결과 저장됨: {output_file}")
        except Exception as e:
            self.logger.error(f"결과 저장 실패: {e}")
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """오류 결과 생성"""
        return {
            'is_safe': False,
            'verification_method': 'error',
            'confidence_score': 0.0,
            'error': error_message,
            'structural_result': None,
            'logical_result': None
        }


def main():
    """
    테스트용 메인 함수
    """
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='통합 워크플로우 안전성 검증')
    parser.add_argument('original', help='원본 YAML 파일 또는 디렉토리')
    parser.add_argument('repaired', help='수정된 YAML 파일 또는 디렉토리')
    parser.add_argument('--mode', choices=['structural', 'logical', 'hybrid'], 
                       default='hybrid', help='검증 모드')
    parser.add_argument('--smells', nargs='*', help='허용된 스멜 목록')
    parser.add_argument('--output', help='결과 저장 파일')
    parser.add_argument('--max-files', type=int, help='최대 처리 파일 수')
    parser.add_argument('--batch', action='store_true', help='배치 모드')
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    verifier = IntegratedVerifier()
    
    if args.batch or Path(args.original).is_dir():
        # 배치 검증
        result = verifier.verify_batch_repairs(
            args.original,
            args.repaired,
            args.output,
            args.smells,
            args.max_files
        )
    else:
        # 단일 파일 검증
        result = verifier.verify_repair_safety(
            args.original,
            args.repaired,
            args.smells,
            args.mode
        )
        
        if args.output:
            verifier._save_results(result, args.output)
    
    # 결과 출력
    print("="*60)
    print("통합 안전성 검증 결과")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

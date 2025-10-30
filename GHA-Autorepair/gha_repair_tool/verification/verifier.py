"""
워크플로우 수정 검증 모듈

수정된 워크플로우의 동등성을 SMT 솔버(z3)와 Tree Edit Distance를 이용해 검증합니다.
"""

import logging
from typing import Dict, Any, Tuple, Optional, List
import yaml
import json

from utils import yaml_parser, process_runner


def verify_repair(
    original_yaml_path: str,
    repaired_yaml_content: str,
    verification_mode: str = "smt"
) -> Dict[str, Any]:
    """
    수정된 워크플로우의 동등성을 검증합니다.
    
    Args:
        original_yaml_path: 원본 YAML 파일 경로
        repaired_yaml_content: 수정된 YAML 내용
        verification_mode: 검증 모드 ("smt", "tree_edit", "hybrid")
        
    Returns:
        Dict: 검증 결과
              {
                  "is_equivalent": bool,
                  "confidence_score": float,  # 0.0 ~ 1.0
                  "verification_method": str,
                  "differences": List[Dict],
                  "smt_result": Dict,
                  "tree_edit_distance": float,
                  "details": Dict
              }
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"워크플로우 동등성 검증 시작: {verification_mode} 모드")
        
        # 원본 YAML 내용 읽기
        original_content = yaml_parser.read_yaml_content(original_yaml_path)
        if not original_content:
            return _create_verification_result(False, 0.0, verification_mode)
        
        # 검증 모드에 따른 처리
        if verification_mode == "smt":
            return _verify_with_smt(original_content, repaired_yaml_content)
        elif verification_mode == "tree_edit":
            return _verify_with_tree_edit_distance(original_content, repaired_yaml_content)
        elif verification_mode == "hybrid":
            return _verify_hybrid(original_content, repaired_yaml_content)
        else:
            logger.error(f"지원하지 않는 검증 모드: {verification_mode}")
            return _create_verification_result(False, 0.0, verification_mode)
            
    except Exception as e:
        logger.error(f"검증 중 오류 발생: {e}")
        return _create_verification_result(False, 0.0, verification_mode)


def _verify_with_smt(original_content: str, repaired_content: str) -> Dict[str, Any]:
    """
    SMT 솔버(z3)를 이용한 동등성 검증을 수행합니다.
    
    Args:
        original_content: 원본 YAML 내용
        repaired_content: 수정된 YAML 내용
        
    Returns:
        Dict: SMT 검증 결과
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1. YAML을 SMT 공식으로 변환
        original_formula = _convert_yaml_to_smt_formula(original_content)
        repaired_formula = _convert_yaml_to_smt_formula(repaired_content)
        
        # 2. Z3 솔버를 이용한 동등성 검증
        smt_result = _run_z3_equivalence_check(original_formula, repaired_formula)
        
        # 3. 결과 분석
        is_equivalent = smt_result.get("is_equivalent", False)
        confidence = 0.9 if is_equivalent else 0.1
        
        differences = smt_result.get("differences", [])
        
        return {
            "is_equivalent": is_equivalent,
            "confidence_score": confidence,
            "verification_method": "smt",
            "differences": differences,
            "smt_result": smt_result,
            "tree_edit_distance": None,
            "details": {
                "smt_formula_original": original_formula[:200] + "..." if len(original_formula) > 200 else original_formula,
                "smt_formula_repaired": repaired_formula[:200] + "..." if len(repaired_formula) > 200 else repaired_formula
            }
        }
        
    except Exception as e:
        logger.error(f"SMT 검증 중 오류: {e}")
        return _create_verification_result(False, 0.0, "smt")


def _verify_with_tree_edit_distance(original_content: str, repaired_content: str) -> Dict[str, Any]:
    """
    Tree Edit Distance를 이용한 구조적 유사성 검증을 수행합니다.
    
    Args:
        original_content: 원본 YAML 내용
        repaired_content: 수정된 YAML 내용
        
    Returns:
        Dict: Tree Edit Distance 검증 결과
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1. YAML을 트리 구조로 변환
        original_tree = _convert_yaml_to_tree(original_content)
        repaired_tree = _convert_yaml_to_tree(repaired_content)
        
        # 2. Tree Edit Distance 계산
        edit_distance = _calculate_tree_edit_distance(original_tree, repaired_tree)
        
        # 3. 정규화된 거리 계산 (0.0 ~ 1.0)
        max_tree_size = max(len(original_tree), len(repaired_tree))
        normalized_distance = edit_distance / max_tree_size if max_tree_size > 0 else 1.0
        
        # 4. 유사성 점수 계산 (거리가 클수록 유사성 낮음)
        similarity_score = 1.0 - normalized_distance
        
        # 5. 임계값 기반 동등성 판단 (0.8 이상이면 동등하다고 판단)
        threshold = 0.8
        is_equivalent = similarity_score >= threshold
        
        # 6. 구조적 차이점 분석
        differences = _analyze_tree_differences(original_tree, repaired_tree)
        
        return {
            "is_equivalent": is_equivalent,
            "confidence_score": similarity_score,
            "verification_method": "tree_edit",
            "differences": differences,
            "smt_result": None,
            "tree_edit_distance": edit_distance,
            "details": {
                "normalized_distance": normalized_distance,
                "threshold_used": threshold,
                "original_tree_size": len(original_tree),
                "repaired_tree_size": len(repaired_tree)
            }
        }
        
    except Exception as e:
        logger.error(f"Tree Edit Distance 검증 중 오류: {e}")
        return _create_verification_result(False, 0.0, "tree_edit")


def _verify_hybrid(original_content: str, repaired_content: str) -> Dict[str, Any]:
    """
    SMT와 Tree Edit Distance를 결합한 하이브리드 검증을 수행합니다.
    
    Args:
        original_content: 원본 YAML 내용
        repaired_content: 수정된 YAML 내용
        
    Returns:
        Dict: 하이브리드 검증 결과
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1. SMT 검증 수행
        smt_result = _verify_with_smt(original_content, repaired_content)
        
        # 2. Tree Edit Distance 검증 수행
        tree_result = _verify_with_tree_edit_distance(original_content, repaired_content)
        
        # 3. 결과 결합 (가중평균)
        smt_weight = 0.7
        tree_weight = 0.3
        
        combined_confidence = (
            smt_result["confidence_score"] * smt_weight +
            tree_result["confidence_score"] * tree_weight
        )
        
        # 4. 최종 동등성 판단 (둘 다 True이거나 결합 신뢰도가 0.7 이상)
        is_equivalent = (
            (smt_result["is_equivalent"] and tree_result["is_equivalent"]) or
            combined_confidence >= 0.7
        )
        
        # 5. 차이점 결합
        combined_differences = smt_result["differences"] + tree_result["differences"]
        
        return {
            "is_equivalent": is_equivalent,
            "confidence_score": combined_confidence,
            "verification_method": "hybrid",
            "differences": combined_differences,
            "smt_result": smt_result["smt_result"],
            "tree_edit_distance": tree_result["tree_edit_distance"],
            "details": {
                "smt_confidence": smt_result["confidence_score"],
                "tree_confidence": tree_result["confidence_score"],
                "weights": {"smt": smt_weight, "tree": tree_weight}
            }
        }
        
    except Exception as e:
        logger.error(f"하이브리드 검증 중 오류: {e}")
        return _create_verification_result(False, 0.0, "hybrid")


def _convert_yaml_to_smt_formula(yaml_content: str) -> str:
    """
    YAML 내용을 SMT 공식으로 변환합니다.
    
    Args:
        yaml_content: YAML 내용
        
    Returns:
        str: SMT 공식
    """
    try:
        # TODO: z3-solver를 이용한 실제 SMT 공식 생성
        # 현재는 간단한 구조적 표현으로 대체
        
        yaml_obj = yaml.safe_load(yaml_content)
        
        # 워크플로우의 핵심 구조를 SMT 공식으로 변환
        smt_formula = _yaml_object_to_smt(yaml_obj)
        
        return smt_formula
        
    except Exception as e:
        logging.getLogger(__name__).error(f"YAML to SMT 변환 중 오류: {e}")
        return ""


def _yaml_object_to_smt(obj: Any, prefix: str = "workflow") -> str:
    """
    YAML 객체를 SMT 공식으로 재귀적으로 변환합니다.
    
    Args:
        obj: YAML 객체
        prefix: SMT 변수 접두사
        
    Returns:
        str: SMT 공식
    """
    try:
        # TODO: 실제 z3 Python API 사용하여 구현
        
        if isinstance(obj, dict):
            formulas = []
            for key, value in obj.items():
                var_name = f"{prefix}_{key}"
                sub_formula = _yaml_object_to_smt(value, var_name)
                formulas.append(sub_formula)
            return f"(and {' '.join(formulas)})"
        
        elif isinstance(obj, list):
            formulas = []
            for i, item in enumerate(obj):
                var_name = f"{prefix}_{i}"
                sub_formula = _yaml_object_to_smt(item, var_name)
                formulas.append(sub_formula)
            return f"(and {' '.join(formulas)})"
        
        elif isinstance(obj, str):
            return f"(= {prefix} \"{obj}\")"
        
        elif isinstance(obj, (int, float, bool)):
            return f"(= {prefix} {str(obj).lower()})"
        
        else:
            return f"(= {prefix} unknown)"
            
    except Exception as e:
        logging.getLogger(__name__).error(f"객체 to SMT 변환 중 오류: {e}")
        return f"(= {prefix} error)"


def _run_z3_equivalence_check(formula1: str, formula2: str) -> Dict[str, Any]:
    """
    Z3 솔버를 이용해 두 공식의 동등성을 검증합니다.
    
    Args:
        formula1: 첫 번째 SMT 공식
        formula2: 두 번째 SMT 공식
        
    Returns:
        Dict: Z3 검증 결과
    """
    try:
        # TODO: 실제 z3-solver 구현
        
        # 현재는 간단한 문자열 비교로 대체
        is_equivalent = formula1 == formula2
        
        differences = []
        if not is_equivalent:
            differences.append({
                "type": "formula_mismatch",
                "description": "SMT formulas are different"
            })
        
        return {
            "is_equivalent": is_equivalent,
            "differences": differences,
            "solver_time": 0.001,
            "model": None
        }
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Z3 검증 중 오류: {e}")
        return {
            "is_equivalent": False,
            "differences": [{"type": "solver_error", "description": str(e)}],
            "solver_time": 0,
            "model": None
        }


def _convert_yaml_to_tree(yaml_content: str) -> Dict[str, Any]:
    """
    YAML 내용을 트리 구조로 변환합니다.
    
    Args:
        yaml_content: YAML 내용
        
    Returns:
        Dict: 트리 구조
    """
    try:
        yaml_obj = yaml.safe_load(yaml_content)
        return _create_tree_representation(yaml_obj)
        
    except Exception as e:
        logging.getLogger(__name__).error(f"YAML to Tree 변환 중 오류: {e}")
        return {}


def _create_tree_representation(obj: Any, path: str = "root") -> Dict[str, Any]:
    """
    객체를 트리 표현으로 변환합니다.
    
    Args:
        obj: 변환할 객체
        path: 현재 경로
        
    Returns:
        Dict: 트리 노드
    """
    node = {
        "path": path,
        "type": type(obj).__name__,
        "children": []
    }
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}"
            child_node = _create_tree_representation(value, child_path)
            node["children"].append(child_node)
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            child_path = f"{path}[{i}]"
            child_node = _create_tree_representation(item, child_path)
            node["children"].append(child_node)
    
    else:
        node["value"] = str(obj)
    
    return node


def _calculate_tree_edit_distance(tree1: Dict, tree2: Dict) -> float:
    """
    두 트리 간의 Edit Distance를 계산합니다.
    
    Args:
        tree1: 첫 번째 트리
        tree2: 두 번째 트리
        
    Returns:
        float: Edit Distance
    """
    try:
        # TODO: zss (Zhang-Shasha) 라이브러리 사용하여 실제 Tree Edit Distance 계산
        
        # 현재는 간단한 구조적 차이 계산으로 대체
        def count_nodes(tree):
            count = 1
            for child in tree.get("children", []):
                count += count_nodes(child)
            return count
        
        def compare_structures(t1, t2):
            if t1.get("type") != t2.get("type"):
                return 1
            
            children1 = t1.get("children", [])
            children2 = t2.get("children", [])
            
            if len(children1) != len(children2):
                return abs(len(children1) - len(children2))
            
            total_diff = 0
            for c1, c2 in zip(children1, children2):
                total_diff += compare_structures(c1, c2)
            
            return total_diff
        
        return float(compare_structures(tree1, tree2))
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Tree Edit Distance 계산 중 오류: {e}")
        return float('inf')


def _analyze_tree_differences(tree1: Dict, tree2: Dict) -> List[Dict[str, Any]]:
    """
    두 트리의 차이점을 분석합니다.
    
    Args:
        tree1: 첫 번째 트리
        tree2: 두 번째 트리
        
    Returns:
        List[Dict]: 차이점 리스트
    """
    differences = []
    
    try:
        # 간단한 구조적 차이 분석
        if tree1.get("type") != tree2.get("type"):
            differences.append({
                "type": "type_mismatch",
                "path": tree1.get("path", "unknown"),
                "original": tree1.get("type"),
                "repaired": tree2.get("type")
            })
        
        children1 = tree1.get("children", [])
        children2 = tree2.get("children", [])
        
        if len(children1) != len(children2):
            differences.append({
                "type": "children_count_mismatch",
                "path": tree1.get("path", "unknown"),
                "original_count": len(children1),
                "repaired_count": len(children2)
            })
        
        # 재귀적으로 자식 노드들 비교
        min_children = min(len(children1), len(children2))
        for i in range(min_children):
            child_diffs = _analyze_tree_differences(children1[i], children2[i])
            differences.extend(child_diffs)
        
    except Exception as e:
        logging.getLogger(__name__).error(f"트리 차이 분석 중 오류: {e}")
    
    return differences


def _create_verification_result(
    is_equivalent: bool, 
    confidence: float, 
    method: str
) -> Dict[str, Any]:
    """
    검증 결과를 생성합니다.
    
    Args:
        is_equivalent: 동등성 여부
        confidence: 신뢰도
        method: 검증 방법
        
    Returns:
        Dict: 검증 결과
    """
    return {
        "is_equivalent": is_equivalent,
        "confidence_score": confidence,
        "verification_method": method,
        "differences": [],
        "smt_result": None,
        "tree_edit_distance": None,
        "details": {}
    }

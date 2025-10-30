"""
GHA-Repair Tool

GitHub Actions 워크플로우의 구문 및 의미론적 오류를 자동으로 탐지하고 수정하는 도구입니다.

주요 기능:
- 구문 오류 탐지 및 수정 (actionlint + LLM)
- 의미론적 스멜 탐지 및 수정 (Tier-1 스멜)
- SMT 기반 동등성 검증
- Tree Edit Distance 기반 구조적 유사성 검증
- 다양한 수정 모드 지원 (baseline, two-phase, gha-repair)

사용법:
    python main.py --input workflow.yml --mode gha-repair

작성자: GHA-Repair Team
버전: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "GHA-Repair Team"
__description__ = "GitHub Actions Workflow Repair Tool"

# 주요 모듈들
from . import syntax_repair
from . import semantic_repair
from . import verification
from . import utils

__all__ = [
    'syntax_repair',
    'semantic_repair', 
    'verification',
    'utils'
]

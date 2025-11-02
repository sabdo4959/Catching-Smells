# yaml_parser.py
# GitHub Actions 워크플로우를 위한 일반화된 파서 및 분석기

import sys
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from pprint import pprint

# -----------------------------------------------------------------------------
# 1. 파서 (Parser) - YAML 파일을 읽어 파이썬 객체로 변환
# -----------------------------------------------------------------------------
class GHAWorkflowParser:
    """
    ruamel.yaml을 사용하여 주석과 구조를 보존하는 GHA 워크플로우 파서.
    """
    def __init__(self):
        """YAML 파서 인스턴스를 초기화합니다."""
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096  # 긴 줄이 있어도 줄 바꿈을 방지합니다.

    def parse(self, file_path: Path):
        """
        주어진 경로의 YAML 파일을 파싱합니다.

        Args:
            file_path: 파싱할 YAML 파일의 Path 객체.

        Returns:
            파싱된 YAML 데이터 객체. 오류 발생 시 None을 반환합니다.
        """
        if not file_path.is_file():
            print(f"ERROR: 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return self.yaml.load(f)
        except YAMLError as e:
            print(f"ERROR: YAML 파싱 실패. 원인: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"ERROR: 예기치 않은 오류 발생. 원인: {e}", file=sys.stderr)
            return None

# -----------------------------------------------------------------------------
# 2. 분석기 (Analyzer) - 파싱된 객체를 분석하여 구조화된 데이터로 추출
# -----------------------------------------------------------------------------
class GHAWorkflowAnalyzer:
    """
    파싱된 GHA 워크플로우 데이터를 분석하여 일반화된 구조로 추출합니다.
    이 클래스는 특정 잡이나 스텝 이름에 의존하지 않습니다.
    """
    def __init__(self, workflow_data: dict):
        """
        분석기 인스턴스를 초기화합니다.

        Args:
            workflow_data: GHAWorkflowParser에 의해 파싱된 데이터 객체.
        """
        if not isinstance(workflow_data, dict):
            raise TypeError("입력 데이터는 반드시 딕셔너리 형태여야 합니다.")
        self.data = workflow_data
        self.analysis_result = {}

    def analyze(self) -> dict:
        """
        워크플로우 분석을 시작하고, 구조화된 결과를 반환합니다.
        """
        self.analysis_result['name'] = self.data.get('name')
        self.analysis_result['triggers'] = self._analyze_triggers()
        self.analysis_result['permissions'] = self.data.get('permissions')
        self.analysis_result['jobs'] = self._analyze_jobs()

        return self.analysis_result

    def _analyze_triggers(self) -> list:
        """'on' 키워드에 명시된 트리거들을 분석합니다."""
        trigger_config = self.data.get('on', {})
        if not trigger_config:
            return []
        
        triggers = []
        if isinstance(trigger_config, str): # on: push
            triggers.append({'event': trigger_config})
        elif isinstance(trigger_config, list): # on: [push, pull_request]
            for event in trigger_config:
                triggers.append({'event': event})
        elif isinstance(trigger_config, dict): # on: push: branches: ...
            for event, config in trigger_config.items():
                trigger_detail = {'event': event}
                if isinstance(config, dict):
                    trigger_detail.update(config)
                triggers.append(trigger_detail)
        return triggers

    def _analyze_jobs(self) -> dict:
        """'jobs' 키워드 아래의 모든 잡들을 순회하며 분석합니다."""
        jobs_config = self.data.get('jobs', {})
        if not jobs_config:
            return {}
            
        analyzed_jobs = {}
        for job_name, job_data in jobs_config.items():
            analyzed_jobs[job_name] = self._analyze_single_job(job_data)
        return analyzed_jobs
        
    def _analyze_single_job(self, job_data: dict) -> dict:
        """단일 잡의 상세 정보를 분석합니다."""
        # 'needs'는 문자열일 수도, 리스트일 수도 있으므로 항상 리스트로 정규화합니다.
        needs = job_data.get('needs', [])
        if isinstance(needs, str):
            needs = [needs]
            
        return {
            'if_condition': job_data.get('if'),
            'runs-on': job_data.get('runs-on'),
            'permissions': job_data.get('permissions'),
            'needs': needs,
            'steps': self._analyze_steps(job_data.get('steps', []))
        }

    def _analyze_steps(self, steps_data: list) -> list:
        """잡 내의 모든 스텝들을 순회하며 분석합니다."""
        analyzed_steps = []
        if not steps_data:
            return analyzed_steps
            
        for step in steps_data:
            step_detail = {
                'name': step.get('name'),
                'id': step.get('id'),
                'if_condition': step.get('if'),
                'uses': step.get('uses'),
                'run': step.get('run'),
                'with': step.get('with'),
                'env': step.get('env')
            }
            analyzed_steps.append(step_detail)
        return analyzed_steps

# --- 데모 실행 코드 ---
if __name__ == "__main__":
    # 어떤 워크플로우든 분석할 수 있음을 보여주기 위한 샘플 YAML
    sample_yaml_content = """
name: 'Angular'
on:
  pull_request:
    paths:
      - 'npm/ng-packs/**/*.ts'
      - 'npm/ng-packs/**/*.html'
      - 'npm/ng-packs/*.json'
      - '!npm/ng-packs/scripts/**'
      - '!npm/ng-packs/packages/schematics/**'
    branches:
      - 'rel-*'
      - 'dev'
    types:
      - opened
      - synchronize
      - reopened
      - ready_for_review
permissions:
  contents: read

jobs:
  build-test-lint:
    if: ${{ !github.event.pull_request.draft }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
        with:
          fetch-depth: 0

      - uses: actions/cache@v4
        with:
          path: 'npm/ng-packs/node_modules'
          key: ${{ runner.os }}-${{ hashFiles('npm/ng-packs/yarn.lock') }}

      - uses: actions/cache@v4
        with:
          path: 'templates/app/angular/node_modules'
          key: ${{ runner.os }}-${{ hashFiles('templates/app/angular/yarn.lock') }}

      - name: Install packages
        run: yarn install
        working-directory: npm/ng-packs

      - name: Run lint
        run: yarn affected:lint --base=remotes/origin/${{ github.base_ref }}
        working-directory: npm/ng-packs

      - name: Run build
        run: yarn affected:build --base=remotes/origin/${{ github.base_ref }}
        working-directory: npm/ng-packs

      - name: Run test
        run: yarn affected:test --base=remotes/origin/${{ github.base_ref }}
        working-directory: npm/ng-packs
"""
    poc_file = Path("parser_demo.yml")
    poc_file.write_text(sample_yaml_content, encoding='utf-8')
    print(f"INFO: 데모용 워크플로우 파일 생성됨: '{poc_file}'")
    print("-" * 50)

    # 1. 파싱
    parser = GHAWorkflowParser()
    parsed_data = parser.parse(poc_file)

    if parsed_data:
        # 2. 분석
        print("INFO: 워크플로우 분석 시작...")
        analyzer = GHAWorkflowAnalyzer(parsed_data)
        analysis_result = analyzer.analyze()
        print("INFO: 워크플로우 분석 완료.")
        print("-" * 50)
        
        # 3. 결과 출력
        print("✅ 최종 분석 결과 (구조화된 딕셔너리):")
        pprint(analysis_result)
        print("-" * 50)
        
    # 4. 임시 파일 정리
    poc_file.unlink()
    print(f"INFO: 데모 파일 삭제됨: '{poc_file}'")
    print("INFO: 모든 작업 완료.")
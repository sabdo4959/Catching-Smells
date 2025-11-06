"""
논리적 동치성 검증기 테스트 스위트

LogicalVerifier의 모든 기능을 테스트합니다:
- 트리거 조건 검증
- if 조건 검증  
- 동시성 제어 검증
- 허용된 스멜 수정 예외 처리
- SMT 기반 논리적 동치성 증명
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
import sys

# 상위 디렉토리 추가
sys.path.append(str(Path(__file__).parent))

from logical_verifier import LogicalVerifier


class TestLogicalVerifier(unittest.TestCase):
    
    def setUp(self):
        """테스트 환경 설정"""
        self.verifier = LogicalVerifier()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """테스트 환경 정리"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_temp_yaml(self, content: dict, filename: str = "test.yml") -> str:
        """임시 YAML 파일 생성"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(content, f, default_flow_style=False)
        return filepath
    
    def test_identical_workflows_safe(self):
        """동일한 워크플로우는 안전해야 함"""
        workflow = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {'uses': 'actions/checkout@v4'},
                        {'run': 'echo "Hello"'}
                    ]
                }
            }
        }
        
        original_path = self._create_temp_yaml(workflow, "original.yml")
        repaired_content = yaml.dump(workflow)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertTrue(result['is_safe'])
        self.assertEqual(result['verification_method'], 'logical_smt')
    
    def test_trigger_change_unsafe(self):
        """트리거 변경은 기본적으로 안전하지 않음"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        repaired = {
            'on': 'pull_request',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertFalse(result['is_safe'])
        self.assertFalse(result['results']['trigger_verification']['is_safe'])
    
    def test_allowed_path_filter_addition(self):
        """허용된 경로 필터 추가는 안전함 (Smell 8)"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        repaired = {
            'on': {
                'push': {
                    'paths': ['src/**']
                }
            },
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content, target_smells=['smell_8']
        )
        
        self.assertTrue(result['is_safe'])
        self.assertTrue(result['results']['trigger_verification']['is_safe'])
    
    def test_if_condition_change_unsafe(self):
        """if 조건 변경은 기본적으로 안전하지 않음"""
        original = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.ref == 'refs/heads/main'",
                    'steps': []
                }
            }
        }
        
        repaired = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.ref == 'refs/heads/develop'",
                    'steps': []
                }
            }
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertFalse(result['is_safe'])
        self.assertFalse(result['results']['if_verification']['is_safe'])
    
    def test_allowed_fork_prevention_addition(self):
        """허용된 포크 방지 조건 추가는 안전함 (Smell 9, 10, 12)"""
        original = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'steps': []
                }
            }
        }
        
        repaired = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.repository == 'owner/repo'",
                    'steps': []
                }
            }
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content, target_smells=['smell_9']
        )
        
        self.assertTrue(result['is_safe'])
        self.assertTrue(result['results']['if_verification']['is_safe'])
    
    def test_step_if_condition_verification(self):
        """스텝 레벨 if 조건 검증"""
        original = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Deploy',
                            'run': 'echo "Deploying"',
                            'if': "github.ref == 'refs/heads/main'"
                        }
                    ]
                }
            }
        }
        
        repaired = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Deploy',
                            'run': 'echo "Deploying"',
                            'if': "github.ref == 'refs/heads/develop'"
                        }
                    ]
                }
            }
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertFalse(result['is_safe'])
        self.assertFalse(result['results']['if_verification']['is_safe'])
    
    def test_concurrency_addition_safe(self):
        """동시성 제어 추가는 허용된 스멜 수정시 안전함 (Smell 6, 7)"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        repaired = {
            'on': 'push',
            'concurrency': {
                'group': '${{ github.workflow }}-${{ github.ref }}',
                'cancel-in-progress': True
            },
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content, target_smells=['smell_6']
        )
        
        self.assertTrue(result['is_safe'])
        self.assertTrue(result['results']['concurrency_verification']['is_safe'])
    
    def test_complex_trigger_conditions(self):
        """복잡한 트리거 조건 테스트"""
        original = {
            'on': {
                'push': {
                    'branches': ['main']
                },
                'pull_request': {
                    'branches': ['main']
                }
            },
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        # 동일한 구조
        repaired = {
            'on': {
                'push': {
                    'branches': ['main']
                },
                'pull_request': {
                    'branches': ['main']
                }
            },
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertTrue(result['is_safe'])
        self.assertTrue(result['results']['trigger_verification']['is_safe'])
    
    def test_multiple_jobs_if_conditions(self):
        """다중 잡의 if 조건 검증"""
        original = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.ref == 'refs/heads/main'",
                    'steps': []
                },
                'deploy': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.event_name == 'push'",
                    'steps': []
                }
            }
        }
        
        repaired = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.ref == 'refs/heads/main'",
                    'steps': []
                },
                'deploy': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.event_name == 'pull_request'",  # 변경됨
                    'steps': []
                }
            }
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertFalse(result['is_safe'])
        self.assertFalse(result['results']['if_verification']['is_safe'])
    
    def test_summary_generation(self):
        """검증 결과 요약 생성 테스트"""
        workflow = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(workflow)
        repaired_content = yaml.dump(workflow)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertIn('summary', result)
        summary = result['summary']
        
        self.assertIn('total_checks', summary)
        self.assertIn('passed_checks', summary)
        self.assertIn('pass_rate', summary)
        self.assertIn('failed_checks', summary)
        
        self.assertEqual(summary['total_checks'], 3)  # trigger, if, concurrency
        self.assertEqual(summary['passed_checks'], 3)
        self.assertEqual(summary['pass_rate'], 1.0)
        self.assertEqual(len(summary['failed_checks']), 0)
    
    def test_yaml_parsing_error(self):
        """잘못된 YAML 파싱 오류 처리"""
        invalid_yaml = "invalid: yaml: content:\n  - broken"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("on: push\njobs: {}")
            original_path = f.name
        
        try:
            result = self.verifier.verify_logical_equivalence(original_path, invalid_yaml)
            # 잘못된 YAML은 파싱 오류로 안전하지 않다고 판정되어야 함
            self.assertFalse(result['is_safe'])
            # 오류 메시지가 포함되어야 함
            self.assertIn('오류', result.get('message', ''))
        finally:
            os.unlink(original_path)
    
    def test_empty_target_smells(self):
        """빈 타겟 스멜 목록 처리"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        repaired = {
            'on': 'pull_request',  # 변경됨
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content, target_smells=[]
        )
        
        self.assertFalse(result['is_safe'])
    
    def test_z3_availability_check(self):
        """Z3 가용성 확인"""
        result_key = 'z3_available'
        
        workflow = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(workflow)
        repaired_content = yaml.dump(workflow)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        self.assertIn(result_key, result)
        # Z3 가용성은 환경에 따라 다를 수 있음

    def test_strict_mode_functionality(self):
        """엄격 모드 기능 테스트 (examples에서 이동)"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        # 경로 필터 추가 (실제 논리적 변경)
        repaired = {
            'on': {
                'push': {
                    'paths': ['src/**', '*.js']
                }
            },
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        # 엄격 모드에서 mode_info 확인
        strict_result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content, strict_mode=True
        )
        
        # 엄격 모드 설정이 올바르게 적용되었는지 확인
        self.assertTrue(strict_result['mode_info']['strict_mode'])
        self.assertEqual(strict_result['mode_info']['total_allowed_smells'], 0)
        
        # 일반 모드와 비교하여 차이 확인
        normal_result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content
        )
        
        # 일반 모드에서는 스멜이 허용되어야 함
        self.assertFalse(normal_result['mode_info']['strict_mode'])
        self.assertEqual(normal_result['mode_info']['total_allowed_smells'], 6)

    def test_default_mode_with_safe_smells(self):
        """기본 모드에서 안전한 스멜들 자동 허용 테스트 (examples에서 이동)"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        # 포크 방지 조건 추가 (기본적으로 허용되어야 함)
        repaired = {
            'on': 'push',
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'if': "github.repository == 'owner/repo'",
                    'steps': []
                }
            }
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        # target_smells=None (기본값)으로 테스트
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        # 기본 모드에서는 일반적인 스멜들이 허용되어야 함
        self.assertTrue(result['is_safe'])
        self.assertFalse(result['mode_info']['strict_mode'])
        self.assertGreater(result['mode_info']['total_allowed_smells'], 0)
        # 기본 허용 스멜: smell_6, smell_7, smell_8, smell_9, smell_10, smell_12
        self.assertEqual(result['mode_info']['total_allowed_smells'], 6)

    def test_multiple_smell_allowance(self):
        """다중 스멜 허용 테스트 (examples에서 이동)"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        # 동시성 제어 추가
        repaired = {
            'on': 'push',
            'concurrency': {
                'group': '${{ github.workflow }}-${{ github.ref }}',
                'cancel-in-progress': True
            },
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        # 특정 스멜들만 허용
        result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content, 
            target_smells=['smell_6', 'smell_7', 'smell_8']
        )
        
        self.assertTrue(result['is_safe'])
        self.assertEqual(result['mode_info']['total_allowed_smells'], 3)
        self.assertListEqual(
            sorted(result['mode_info']['effective_smells']),
            ['smell_6', 'smell_7', 'smell_8']
        )

    def test_logic_change_always_unsafe(self):
        """논리적 변경은 스멜 허용과 관계없이 항상 위험 (examples에서 이동)"""
        original = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        # 트리거 변경 (논리적 변경)
        repaired = {
            'on': 'pull_request',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        # 스멜을 허용해도 논리적 변경은 위험해야 함
        result = self.verifier.verify_logical_equivalence(
            original_path, repaired_content, 
            target_smells=['smell_8', 'smell_9']
        )
        
        self.assertFalse(result['is_safe'])
        self.assertIn('trigger_verification', result['summary']['failed_checks'])

    def test_mode_info_consistency(self):
        """mode_info 정보 일관성 테스트 (examples에서 이동)"""
        workflow = {
            'on': 'push',
            'jobs': {'test': {'runs-on': 'ubuntu-latest', 'steps': []}}
        }
        
        original_path = self._create_temp_yaml(workflow)
        repaired_content = yaml.dump(workflow)
        
        # 다양한 모드에서 mode_info 검증
        test_cases = [
            {
                'params': {},
                'expected_strict': False,
                'expected_smell_count': 6
            },
            {
                'params': {'strict_mode': True},
                'expected_strict': True,
                'expected_smell_count': 0
            },
            {
                'params': {'target_smells': ['smell_8']},
                'expected_strict': False,
                'expected_smell_count': 1
            },
            {
                'params': {'target_smells': []},
                'expected_strict': False,
                'expected_smell_count': 0
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['params']):
                result = self.verifier.verify_logical_equivalence(
                    original_path, repaired_content, **case['params']
                )
                
                self.assertIn('mode_info', result)
                mode_info = result['mode_info']
                
                self.assertEqual(mode_info['strict_mode'], case['expected_strict'])
                self.assertEqual(mode_info['total_allowed_smells'], case['expected_smell_count'])
                self.assertIn('effective_smells', mode_info)

    def test_yaml_literal_block_if_condition_with_run_change(self):
        """YAML literal block (|) if 조건과 run 명령어 변수 변경 테스트"""
        # 실제 문제 케이스: if에 literal block이 있고 run에서 변수만 변경
        original = {
            'on': 'push',
            'jobs': {
                'release-pr': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Release Edge',
                            'if': 'github.event_name == \'push\' &&\n!contains(github.event.head_commit.message, \'[skip-release]\')\n',
                            'run': './scripts/release-edge.sh pr-${{ github.event.issue.number }}',
                            'env': {
                                'NODE_AUTH_TOKEN': '${{ secrets.NPM_AUTH_TOKEN }}'
                            }
                        }
                    ]
                }
            }
        }
        
        repaired = {
            'on': 'push',
            'jobs': {
                'release-pr': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Release Edge',
                            'if': 'github.event_name == \'push\' &&\n!contains(github.event.head_commit.message, \'[skip-release]\')\n',
                            'run': './scripts/release-edge.sh pr-${{ github.event.number }}',  # 변수만 변경
                            'env': {
                                'NODE_AUTH_TOKEN': '${{ secrets.NPM_AUTH_TOKEN }}'
                            }
                        }
                    ]
                }
            }
        }
        
        original_path = self._create_temp_yaml(original)
        repaired_content = yaml.dump(repaired)
        
        result = self.verifier.verify_logical_equivalence(original_path, repaired_content)
        
        # if 조건은 동일하므로 논리적으로 안전해야 함
        # (run 명령어는 LogicalVerifier가 검증하지 않음)
        self.assertTrue(result['is_safe'])
        self.assertTrue(result['results']['if_verification']['is_safe'])
        self.assertTrue(result['results']['trigger_verification']['is_safe'])

    def test_yaml_parsing_robust_handling(self):
        """YAML 파싱 문제가 있는 파일의 robust한 처리 테스트"""
        # 문법적으로 문제가 있는 YAML (name과 run이 분리된 구조)
        problematic_yaml_content = """
on: push
jobs:
  release-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Build Stub
      - run: pnpm build:stub
      - name: Build  
      - run: pnpm build:ci
      - name: Release Edge
        if: |
          github.event_name == 'push' &&
          !contains(github.event.head_commit.message, '[skip-release]')
        run: ./scripts/release-edge.sh pr-${{ github.event.issue.number }}
"""
        
        # 수정된 버전 (올바른 구조)
        fixed_yaml_content = """
on: push
jobs:
  release-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Build Stub
      - run: pnpm build:stub
      - name: Build  
      - run: pnpm build:ci
      - name: Release Edge
        if: |
          github.event_name == 'push' &&
          !contains(github.event.head_commit.message, '[skip-release]')
        run: ./scripts/release-edge.sh pr-${{ github.event.number }}
"""
        
        # 문제가 있는 원본 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(problematic_yaml_content)
            original_path = f.name
        
        try:
            result = self.verifier.verify_logical_equivalence(original_path, fixed_yaml_content)
            
            # 결과가 정상적으로 반환되어야 함 (오류로 실패하지 않음)
            self.assertIn('is_safe', result)
            # 파싱 문제나 다른 이유로 인해 안전하지 않을 수 있음
            self.assertIsInstance(result['is_safe'], bool)
            
        finally:
            os.unlink(original_path)


def run_comprehensive_test():
    """포괄적인 테스트 실행"""
    print("="*60)
    print("논리적 동치성 검증기 테스트 시작")
    print("="*60)
    
    # 테스트 스위트 실행
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLogicalVerifier)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    print(f"총 테스트: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")
    
    if result.failures:
        print("\n실패한 테스트:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n오류가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)

# src/evaluators/execution_evaluator.py
"""
Execution Evaluator - Chạy code với test cases
Đây là phần "ORM" (Outcome Reward Model) trong ORPS
FREE - chạy local
"""
import subprocess
import tempfile
import time
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class TestResult:
    """Result of a single test"""
    test_id: int
    input_data: str
    expected: str
    actual: str
    passed: bool
    error: Optional[str] = None
    runtime_ms: float = 0

@dataclass
class ExecutionResult:
    """Complete execution result"""
    problem_id: str
    model_name: str
    total_tests: int
    passed_tests: int
    pass_rate: float
    test_results: List[TestResult] = field(default_factory=list)
    total_runtime_ms: float = 0
    has_syntax_error: bool = False
    syntax_error_msg: Optional[str] = None
    has_runtime_error: bool = False
    runtime_error_msg: Optional[str] = None
    
    def to_dict(self):
        return {
            "problem_id": self.problem_id,
            "model_name": self.model_name,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "pass_rate": self.pass_rate,
            "test_results": [
                {"test_id": t.test_id, "input": t.input_data, "expected": t.expected,
                 "actual": t.actual, "passed": t.passed, "error": t.error}
                for t in self.test_results
            ],
            "total_runtime_ms": self.total_runtime_ms,
            "has_syntax_error": self.has_syntax_error,
            "has_runtime_error": self.has_runtime_error
        }


class ExecutionEvaluator:
    """
    Evaluates code by running with test cases
    This is the "Outcome" part of ORPS - objective verification
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def evaluate(self, code: str, test_cases: List[Dict], 
                 problem_id: str, model_name: str) -> ExecutionResult:
        """Run code against all test cases"""
        
        # Check syntax first
        syntax_err = self._check_syntax(code)
        if syntax_err:
            return ExecutionResult(
                problem_id=problem_id, model_name=model_name,
                total_tests=len(test_cases), passed_tests=0, pass_rate=0,
                has_syntax_error=True, syntax_error_msg=syntax_err
            )
        
        results = []
        total_runtime = 0
        
        for i, test in enumerate(test_cases):
            result = self._run_test(code, test, i + 1)
            results.append(result)
            total_runtime += result.runtime_ms
        
        passed = sum(1 for r in results if r.passed)
        
        return ExecutionResult(
            problem_id=problem_id,
            model_name=model_name,
            total_tests=len(test_cases),
            passed_tests=passed,
            pass_rate=passed / len(test_cases) if test_cases else 0,
            test_results=results,
            total_runtime_ms=total_runtime,
            has_runtime_error=any(r.error for r in results)
        )
    
    def _check_syntax(self, code: str) -> Optional[str]:
        try:
            compile(code, '<string>', 'exec')
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"
    
    def _run_test(self, code: str, test: Dict, test_id: int) -> TestResult:
        """Run code with a single test"""
        test_input = test.get("input", "")
        expected = str(test.get("expected_output", test.get("output", "")))
        
        # Create test harness
        harness = self._create_harness(code, test_input)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(harness)
            temp_file = f.name
        
        try:
            start = time.time()
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True, text=True, timeout=self.timeout
            )
            runtime = (time.time() - start) * 1000
            
            actual = result.stdout.strip()
            error = result.stderr.strip() if result.returncode != 0 else None
            
            # Normalize for comparison
            passed = self._normalize(actual) == self._normalize(expected)
            
            return TestResult(
                test_id=test_id, input_data=str(test_input),
                expected=expected, actual=actual,
                passed=passed, error=error, runtime_ms=runtime
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                test_id=test_id, input_data=str(test_input),
                expected=expected, actual="",
                passed=False, error=f"Timeout ({self.timeout}s)",
                runtime_ms=self.timeout * 1000
            )
        except Exception as e:
            return TestResult(
                test_id=test_id, input_data=str(test_input),
                expected=expected, actual="",
                passed=False, error=str(e), runtime_ms=0
            )
        finally:
            try: os.unlink(temp_file)
            except: pass
    
    def _create_harness(self, code: str, test_input: str) -> str:
        return f'''
import sys
from typing import List, Optional, Dict, Set, Tuple

# User code
{code}

# Run test
try:
    test_input = {test_input}
    if 'Solution' in dir():
        sol = Solution()
        methods = [m for m in dir(sol) if not m.startswith('_')]
        if methods:
            func = getattr(sol, methods[0])
            if isinstance(test_input, (list, tuple)):
                result = func(*test_input)
            else:
                result = func(test_input)
            print(result)
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
    
    def _normalize(self, s: str) -> str:
        """Normalize output for comparison"""
        s = s.strip()
        try:
            import ast
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                try: parsed = sorted(parsed)
                except: pass
            return str(parsed)
        except:
            return s


def extract_test_cases(problem: Dict) -> List[Dict]:
    """Extract test cases from problem"""
    tests = []
    if "examples" in problem:
        for ex in problem["examples"]:
            tests.append({
                "input": ex.get("input"),
                "expected_output": ex.get("output")
            })
    if "testcases" in problem:
        for tc in problem["testcases"]:
            tests.append({
                "input": tc.get("input"),
                "expected_output": tc.get("expected", tc.get("output"))
            })
    return tests

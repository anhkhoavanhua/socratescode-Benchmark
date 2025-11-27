"""
Layer 1: Code Correctness Evaluator
Based on APPS/MBPP benchmark methodology

Scientific basis:
- APPS (UC Berkeley, 2021): pass@k metric, functional correctness
- MBPP (Google Research, 2021): entry-level test execution
- HumanEval (OpenAI, 2021): code extraction and testing

Key metrics:
- pass@k: Probability at least 1 of k generations passes all tests
- Functional correctness: Syntax, runtime, logical errors
"""

import subprocess
import sys
import time
import tempfile
import os
import re
import json
import traceback
from dataclasses import dataclass
from typing import List, Any, Optional, Tuple, Dict
from config import config

@dataclass
class TestCase:
    """Single test case for a problem"""
    input_data: Any
    expected_output: Any
    description: str = ""

@dataclass
class CorrectnessResult:
    """Result of correctness evaluation"""
    passed: bool
    pass_rate: float
    tests_passed: int
    tests_total: int
    syntax_error: Optional[str] = None
    runtime_error: Optional[str] = None
    logical_errors: List[str] = None
    execution_time_ms: float = 0
    extracted_code: str = ""

class CodeExtractor:
    """Extract code from AI responses (various formats)"""
    
    @staticmethod
    def extract(response: str) -> str:
        """Extract Python code from AI response"""
        # Pattern 1: ```python ... ``` (Strict, closed blocks)
        # Use multiline regex to ensure closing backticks are at the start of a line (ignoring indented ones)
        patterns = [
            r'(?ms)```python\r?\n(.*?)^```',
            r'(?ms)```py\r?\n(.*?)^```',
            r'(?ms)```\r?\n(.*?)^```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                # Return longest code block
                return max(matches, key=len).strip()
        
        # Pattern 2: Unclosed blocks (try to find start of block until end)
        unclosed_patterns = [
             r'```python\r?\n(.*)',
             r'```py\r?\n(.*)',
             r'```\r?\n(.*)',
        ]
        
        for pattern in unclosed_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Pattern 3: Look for code-like content (Fallback)
        lines = response.split('\n')
        code_lines = []
        in_code = False
        code_indicators = ['def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ', 'return ']
        
        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(ind) for ind in code_indicators):
                in_code = True
            if in_code and (stripped or line.startswith(' ') or line.startswith('\t')):
                code_lines.append(line)
            elif in_code and not stripped:
                code_lines.append('')
        
        return '\n'.join(code_lines).strip() if code_lines else ""

class CodeCorrectnessEvaluator:
    """
    Evaluates code correctness using APPS/MBPP methodology
    
    Key principles:
    1. Automated test execution
    2. Multiple test cases per problem
    3. Pass@k metric calculation
    4. Error classification (syntax, runtime, logical)
    """
    
    def __init__(self, timeout: int = None):
        self.timeout = timeout or config.CODE_TIMEOUT
        self.extractor = CodeExtractor()
    
    def check_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """Check Python syntax without executing"""
        try:
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
    
    def execute_code(self, code: str, test_input: Any, 
                    func_name: str = None) -> Tuple[Any, float, Optional[str]]:
        """
        Execute code safely with timeout
        Returns: (output, execution_time_ms, error_message)
        """
        # Prepare wrapper code
        wrapper = f'''
import sys
import json
import time

# User code
{code}

# Helpers for Linked List
if 'ListNode' not in globals():
    class ListNode:
        def __init__(self, val=0, next=None):
            self.val = val
            self.next = next

def list_to_ll(items):
    if not items: return None
    dummy = ListNode(0)
    curr = dummy
    for i in items:
        curr.next = ListNode(i)
        curr = curr.next
    return dummy.next

def ll_to_list(node):
    res = []
    while node:
        res.append(node.val)
        node = node.next
    return res

if __name__ == "__main__":
    try:
        test_input = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
        start = time.perf_counter()
        
        candidates = [{repr(func_name) if func_name else "'solution'"}, 'solve', 'main', 'twoSum', 'threeSum', 'maxProfit', 'isValid', 'mergeTwoLists', 'longestPalindrome']
        
        func = None
        func_name = None
        
        # 1. Check top-level functions
        for fname in candidates:
            if fname in dir():
                f = eval(fname)
                if callable(f):
                    func = f
                    func_name = fname
                    break
        
        # 2. Check Solution class methods
        if func is None and 'Solution' in dir():
            try:
                sol = Solution()
                for fname in candidates:
                    if hasattr(sol, fname):
                        f = getattr(sol, fname)
                        if callable(f):
                            func = f
                            func_name = fname
                            break
            except:
                pass

        result = None
        if func:
            # Handle different input types
            if func_name == 'mergeTwoLists' and isinstance(test_input, list):
                # Convert inputs to Linked Lists
                args = [list_to_ll(arg) for arg in test_input]
                # Call function
                ll_result = func(*args)
                # Convert output back to list
                result = ll_to_list(ll_result)
            elif isinstance(test_input, list) and len(test_input) > 0:
                # Check if it looks like multiple arguments
                result = func(*test_input)
            elif test_input is not None:
                result = func(test_input)
            else:
                result = func()
        
        elapsed = (time.perf_counter() - start) * 1000
        print(json.dumps({{"ok": True, "result": result, "time": elapsed}}))
    except Exception as e:
        import traceback
        print(json.dumps({{"ok": False, "error": str(e), "trace": traceback.format_exc()}}))
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(wrapper)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file, json.dumps(test_input)],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                return None, 0, f"Runtime error: {result.stderr[:500]}"
            
            try:
                output = json.loads(result.stdout)
                if output.get("ok"):
                    return output.get("result"), output.get("time", 0), None
                return None, 0, output.get("error", "Unknown error")
            except json.JSONDecodeError:
                return result.stdout.strip(), 0, None
                
        except subprocess.TimeoutExpired:
            return None, self.timeout * 1000, "Timeout exceeded"
        except Exception as e:
            return None, 0, str(e)
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def compare_outputs(self, actual: Any, expected: Any, 
                       tolerance: float = 1e-6) -> bool:
        """Compare outputs with tolerance for floats"""
        if actual == expected:
            return True
            
        # Allow one of multiple valid answers (for strings)
        if isinstance(actual, str) and isinstance(expected, list) and all(isinstance(x, str) for x in expected):
            return actual in expected
            
        if actual is None or expected is None:
            return False
        
        # Float comparison
        if isinstance(actual, float) and isinstance(expected, float):
            return abs(actual - expected) < tolerance
        
        # List comparison
        if isinstance(actual, list) and isinstance(expected, list):
            if len(actual) != len(expected):
                return False
            return all(self.compare_outputs(a, e, tolerance) 
                      for a, e in zip(actual, expected))
        
        # String comparison
        return str(actual).strip() == str(expected).strip()
    
    def evaluate(self, ai_response: str, test_cases: List[TestCase],
                func_name: str = None) -> CorrectnessResult:
        """
        Evaluate AI response against test cases
        
        APPS/MBPP methodology:
        1. Extract code
        2. Check syntax
        3. Run each test case
        4. Calculate pass rate
        """
        logical_errors = []
        total_time = 0
        
        # Extract code
        code = self.extractor.extract(ai_response)
        
        if not code:
            return CorrectnessResult(
                passed=False,
                pass_rate=0.0,
                tests_passed=0,
                tests_total=len(test_cases),
                syntax_error="No code found in response",
                extracted_code=""
            )
        
        # Check syntax
        syntax_ok, syntax_error = self.check_syntax(code)
        if not syntax_ok:
            return CorrectnessResult(
                passed=False,
                pass_rate=0.0,
                tests_passed=0,
                tests_total=len(test_cases),
                syntax_error=syntax_error,
                extracted_code=code
            )
        
        # Run test cases
        tests_passed = 0
        for i, tc in enumerate(test_cases):
            output, exec_time, error = self.execute_code(code, tc.input_data, func_name)
            total_time += exec_time
            
            if error:
                if "Timeout" in error:
                    return CorrectnessResult(
                        passed=False,
                        pass_rate=tests_passed / len(test_cases),
                        tests_passed=tests_passed,
                        tests_total=len(test_cases),
                        runtime_error=error,
                        execution_time_ms=total_time,
                        extracted_code=code
                    )
                logical_errors.append(f"Test {i+1}: {error}")
            elif self.compare_outputs(output, tc.expected_output):
                tests_passed += 1
            else:
                logical_errors.append(f"Test {i+1}: Expected {tc.expected_output}, got {output}")
        
        pass_rate = tests_passed / len(test_cases) if test_cases else 0
        
        return CorrectnessResult(
            passed=pass_rate == 1.0,
            pass_rate=pass_rate,
            tests_passed=tests_passed,
            tests_total=len(test_cases),
            logical_errors=logical_errors if logical_errors else None,
            execution_time_ms=total_time,
            extracted_code=code
        )

# LeetCode problems với test cases
# Format: TestCase(input_data, expected_output, description)
# input_data should be the arguments to pass to the function
LEETCODE_PROBLEMS = {
    "two_sum": {
        "id": 1,
        "name": "Two Sum",
        "difficulty": "Easy",
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
        "test_cases": [
            TestCase([[2,7,11,15], 9], [0, 1], "Basic case"),
            TestCase([[3,2,4], 6], [1, 2], "Middle elements"),
            TestCase([[3,3], 6], [0, 1], "Same values"),
        ],
        "func_name": "twoSum"
    },
    "valid_parentheses": {
        "id": 20,
        "name": "Valid Parentheses",
        "difficulty": "Easy",
        "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
        "test_cases": [
            TestCase("()", True, "Simple valid"),
            TestCase("()[]{}", True, "Multiple valid"),
            TestCase("(]", False, "Invalid mix"),
            TestCase("([)]", False, "Wrong order"),
            TestCase("{[]}", True, "Nested valid"),
        ],
        "func_name": "isValid"
    },
    "merge_two_lists": {
        "id": 21,
        "name": "Merge Two Sorted Lists",
        "difficulty": "Easy",
        "description": "Merge two sorted linked lists and return it as a sorted list.",
        "test_cases": [
            TestCase([[1,2,4], [1,3,4]], [1,1,2,3,4,4], "Basic merge"),
            TestCase([[], []], [], "Both empty"),
            TestCase([[], [0]], [0], "One empty"),
        ],
        "func_name": "mergeTwoLists"
    },
    "three_sum": {
        "id": 15,
        "name": "3Sum",
        "difficulty": "Medium",
        "description": "Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]] such that i != j, i != k, and j != k, and nums[i] + nums[j] + nums[k] == 0.",
        "test_cases": [
            TestCase([[-1,0,1,2,-1,-4]], [[-1,-1,2],[-1,0,1]], "Basic case"),
            TestCase([[0,1,1]], [], "No solution"),
            TestCase([[0,0,0]], [[0,0,0]], "All zeros"),
        ],
        "func_name": "threeSum"
    },
    "longest_palindrome": {
        "id": 5,
        "name": "Longest Palindromic Substring",
        "difficulty": "Medium",
        "description": "Given a string s, return the longest palindromic substring in s.",
        "test_cases": [
            TestCase("babad", ["bab", "aba"], "Basic case"),  # Accept either
            TestCase("cbbd", "bb", "Even length"),
            TestCase("a", "a", "Single char"),
        ],
        "func_name": "longestPalindrome"
    }
}

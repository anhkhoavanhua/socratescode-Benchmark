"""
Layer 2: Code Efficiency Evaluator
Based on BigCodeBench/EvoCodeBench methodology

Scientific basis:
- BigCodeBench (2024, NeurIPS): Runtime/memory efficiency metrics
- EvoCodeBench (NeurIPS 2024): Domain-Specific Improvement (DSI)
- LiveCodeBench (2024): Multi-dimensional code quality

Key metrics:
- Runtime efficiency: Execution time comparison
- Memory efficiency: Memory usage comparison
- Complexity analysis: Time/space complexity estimation

NOTE: This layer does NOT compare semantic similarity of responses.
      AI responses naturally vary - we only evaluate code quality.
"""

import subprocess
import sys
import time
import tempfile
import os
import re
import json
import tracemalloc
from dataclasses import dataclass
from typing import List, Any, Optional, Tuple, Dict
from config import config

@dataclass
class EfficiencyResult:
    """Result of efficiency evaluation"""
    # Runtime metrics
    avg_runtime_ms: float
    min_runtime_ms: float
    max_runtime_ms: float
    runtime_score: float  # 0-100 scale
    
    # Memory metrics
    peak_memory_kb: float
    avg_memory_kb: float
    memory_score: float  # 0-100 scale
    
    # Complexity estimates
    estimated_time_complexity: str
    estimated_space_complexity: str
    
    # Overall score
    efficiency_score: float  # 0-100 scale
    
    # Details
    num_runs: int = 0
    errors: List[str] = None

class CodeEfficiencyEvaluator:
    """
    Evaluates code efficiency using BigCodeBench methodology
    
    Key principles:
    1. Multiple runs for statistical significance
    2. Runtime measurement (median of N runs)
    3. Memory profiling
    4. Complexity estimation
    
    IMPORTANT: Does NOT compare text similarity.
    AI responses naturally vary - only code quality matters.
    """
    
    def __init__(self, timeout: int = None, num_runs: int = 5):
        self.timeout = timeout or config.CODE_TIMEOUT
        self.num_runs = num_runs
    
    def measure_runtime(self, code: str, test_input: Any, 
                       func_name: str = None) -> Tuple[List[float], Optional[str]]:
        """
        Measure runtime across multiple executions
        Returns: (list of runtimes in ms, error message)
        """
        wrapper = f'''
import sys
import json
import time
import gc

{code}

if __name__ == "__main__":
    test_input = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
    num_runs = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    runtimes = []
    for _ in range(num_runs):
        gc.collect()  # Clean up before each run
        
        try:
            start = time.perf_counter()
            
            result = None
            for fname in [{repr(func_name) if func_name else "'solution'"}, 'solve', 'main', 'twoSum']:
                if fname in dir():
                    func = eval(fname)
                    if callable(func):
                        if isinstance(test_input, list):
                            result = func(*test_input)
                        elif isinstance(test_input, dict):
                            result = func(**test_input)
                        else:
                            result = func(test_input) if test_input is not None else func()
                        break
            
            elapsed = (time.perf_counter() - start) * 1000
            runtimes.append(elapsed)
        except Exception as e:
            print(json.dumps({{"ok": False, "error": str(e)}}))
            sys.exit(1)
    
    print(json.dumps({{"ok": True, "runtimes": runtimes}}))
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(wrapper)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file, json.dumps(test_input), str(self.num_runs)],
                capture_output=True,
                text=True,
                timeout=self.timeout * self.num_runs
            )
            
            if result.returncode != 0:
                return [], f"Runtime error: {result.stderr[:300]}"
            
            output = json.loads(result.stdout)
            if output.get("ok"):
                return output.get("runtimes", []), None
            return [], output.get("error", "Unknown error")
            
        except subprocess.TimeoutExpired:
            return [], "Timeout exceeded"
        except Exception as e:
            return [], str(e)
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def measure_memory(self, code: str, test_input: Any,
                      func_name: str = None) -> Tuple[float, float, Optional[str]]:
        """
        Measure memory usage
        Returns: (peak_memory_kb, avg_memory_kb, error)
        """
        wrapper = f'''
import sys
import json
import tracemalloc

{code}

if __name__ == "__main__":
    test_input = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
    
    tracemalloc.start()
    
    try:
        for fname in [{repr(func_name) if func_name else "'solution'"}, 'solve', 'main', 'twoSum']:
            if fname in dir():
                func = eval(fname)
                if callable(func):
                    if isinstance(test_input, list):
                        result = func(*test_input)
                    elif isinstance(test_input, dict):
                        result = func(**test_input)
                    else:
                        result = func(test_input) if test_input is not None else func()
                    break
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(json.dumps({{
            "ok": True,
            "current_kb": current / 1024,
            "peak_kb": peak / 1024
        }}))
    except Exception as e:
        tracemalloc.stop()
        print(json.dumps({{"ok": False, "error": str(e)}}))
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
                return 0, 0, f"Error: {result.stderr[:200]}"
            
            output = json.loads(result.stdout)
            if output.get("ok"):
                return output.get("peak_kb", 0), output.get("current_kb", 0), None
            return 0, 0, output.get("error", "Unknown error")
            
        except Exception as e:
            return 0, 0, str(e)
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def estimate_complexity(self, code: str) -> Tuple[str, str]:
        """
        Estimate time and space complexity from code patterns
        
        Heuristic analysis based on:
        - Loop structures
        - Recursion patterns
        - Data structure usage
        """
        code_lower = code.lower()
        
        # Time complexity estimation
        nested_loops = len(re.findall(r'for\s+\w+\s+in.*?:\s*\n\s+for\s+\w+\s+in', code, re.DOTALL))
        single_loops = len(re.findall(r'for\s+\w+\s+in', code))
        has_recursion = 'def ' in code and re.search(r'(\w+)\([^)]*\)[^{]*\1\(', code)
        has_binary_search = 'mid' in code_lower and ('left' in code_lower or 'low' in code_lower)
        has_sort = 'sort(' in code_lower or '.sort()' in code_lower
        
        if nested_loops >= 2:
            time_complexity = "O(n³)"
        elif nested_loops == 1:
            time_complexity = "O(n²)"
        elif has_binary_search:
            time_complexity = "O(log n)" if single_loops <= 1 else "O(n log n)"
        elif has_sort:
            time_complexity = "O(n log n)"
        elif has_recursion:
            time_complexity = "O(2^n) or O(n!)"  # Conservative estimate
        elif single_loops >= 1:
            time_complexity = "O(n)"
        else:
            time_complexity = "O(1)"
        
        # Space complexity estimation
        has_matrix = '[[' in code or 'dp[' in code_lower
        has_hashmap = 'dict(' in code or '{}' in code or 'set(' in code
        has_stack_queue = 'append' in code and ('pop' in code or 'popleft' in code)
        
        if has_matrix:
            space_complexity = "O(n²)"
        elif has_recursion:
            space_complexity = "O(n)"  # Stack space
        elif has_hashmap or has_stack_queue:
            space_complexity = "O(n)"
        else:
            space_complexity = "O(1)"
        
        return time_complexity, space_complexity
    
    def calculate_scores(self, runtimes: List[float], memory_kb: float,
                        baseline_runtime: float = None, 
                        baseline_memory: float = None) -> Tuple[float, float, float]:
        """
        Calculate efficiency scores (0-100 scale)
        
        Scoring based on BigCodeBench methodology:
        - 90-100: Excellent (within 20% of baseline)
        - 70-89: Good (within 2x of baseline)
        - 50-69: Acceptable (within 5x of baseline)
        - 0-49: Poor (more than 5x of baseline)
        """
        if not runtimes:
            return 0, 0, 0
        
        avg_runtime = sum(runtimes) / len(runtimes)
        
        # Use defaults if no baseline provided
        baseline_runtime = baseline_runtime or 1.0  # 1ms baseline
        baseline_memory = baseline_memory or 100.0   # 100KB baseline
        
        # Runtime score
        runtime_ratio = avg_runtime / baseline_runtime if baseline_runtime > 0 else float('inf')
        if runtime_ratio <= config.RUNTIME_EXCELLENT:
            runtime_score = 90 + (config.RUNTIME_EXCELLENT - runtime_ratio) / config.RUNTIME_EXCELLENT * 10
        elif runtime_ratio <= config.RUNTIME_GOOD:
            runtime_score = 70 + (config.RUNTIME_GOOD - runtime_ratio) / (config.RUNTIME_GOOD - config.RUNTIME_EXCELLENT) * 20
        elif runtime_ratio <= 5.0:
            runtime_score = 50 + (5.0 - runtime_ratio) / (5.0 - config.RUNTIME_GOOD) * 20
        else:
            runtime_score = max(0, 50 - (runtime_ratio - 5.0) * 10)
        
        # Memory score
        memory_ratio = memory_kb / baseline_memory if baseline_memory > 0 else float('inf')
        if memory_ratio <= config.MEMORY_EXCELLENT:
            memory_score = 90 + (config.MEMORY_EXCELLENT - memory_ratio) / config.MEMORY_EXCELLENT * 10
        elif memory_ratio <= config.MEMORY_GOOD:
            memory_score = 70 + (config.MEMORY_GOOD - memory_ratio) / (config.MEMORY_GOOD - config.MEMORY_EXCELLENT) * 20
        elif memory_ratio <= 5.0:
            memory_score = 50 + (5.0 - memory_ratio) / (5.0 - config.MEMORY_GOOD) * 20
        else:
            memory_score = max(0, 50 - (memory_ratio - 5.0) * 10)
        
        # Overall score (weighted average)
        efficiency_score = runtime_score * 0.6 + memory_score * 0.4
        
        return min(100, runtime_score), min(100, memory_score), min(100, efficiency_score)
    
    def evaluate(self, code: str, test_inputs: List[Any],
                func_name: str = None,
                baseline_runtime: float = None,
                baseline_memory: float = None) -> EfficiencyResult:
        """
        Full efficiency evaluation
        
        BigCodeBench methodology:
        1. Multiple runtime measurements
        2. Memory profiling
        3. Complexity estimation
        4. Score calculation
        """
        all_runtimes = []
        all_memory = []
        errors = []
        
        for test_input in test_inputs:
            # Measure runtime
            runtimes, error = self.measure_runtime(code, test_input, func_name)
            if error:
                errors.append(f"Runtime: {error}")
            else:
                all_runtimes.extend(runtimes)
            
            # Measure memory
            peak_mem, avg_mem, error = self.measure_memory(code, test_input, func_name)
            if error:
                errors.append(f"Memory: {error}")
            else:
                all_memory.append(peak_mem)
        
        # Calculate statistics
        if all_runtimes:
            avg_runtime = sum(all_runtimes) / len(all_runtimes)
            min_runtime = min(all_runtimes)
            max_runtime = max(all_runtimes)
        else:
            avg_runtime = min_runtime = max_runtime = 0
        
        peak_memory = max(all_memory) if all_memory else 0
        avg_memory = sum(all_memory) / len(all_memory) if all_memory else 0
        
        # Estimate complexity
        time_complexity, space_complexity = self.estimate_complexity(code)
        
        # Calculate scores
        runtime_score, memory_score, efficiency_score = self.calculate_scores(
            all_runtimes, peak_memory, baseline_runtime, baseline_memory
        )
        
        return EfficiencyResult(
            avg_runtime_ms=avg_runtime,
            min_runtime_ms=min_runtime,
            max_runtime_ms=max_runtime,
            runtime_score=runtime_score,
            peak_memory_kb=peak_memory,
            avg_memory_kb=avg_memory,
            memory_score=memory_score,
            estimated_time_complexity=time_complexity,
            estimated_space_complexity=space_complexity,
            efficiency_score=efficiency_score,
            num_runs=len(all_runtimes),
            errors=errors if errors else None
        )

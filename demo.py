#!/usr/bin/env python3
"""
Demo script to test the SocratesCode Evaluator
Tests the evaluation pipeline with sample AI responses
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluators.correctness import CodeCorrectnessEvaluator, LEETCODE_PROBLEMS, TestCase
from evaluators.efficiency import CodeEfficiencyEvaluator

def demo_correctness_evaluation():
    """Demo Layer 1: Code Correctness Evaluation"""
    print("\n" + "="*60)
    print("🧪 DEMO: Layer 1 - Code Correctness Evaluation")
    print("="*60)
    
    evaluator = CodeCorrectnessEvaluator()
    
    # Sample AI responses (simulated)
    sample_responses = {
        "two_sum": {
            "correct": '''
```python
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
```
''',
            "incorrect": '''
```python
def twoSum(nums, target):
    # Wrong approach - O(n^2) and incorrect logic
    for i in range(len(nums)):
        for j in range(len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]  # Bug: should be i != j
    return []
```
''',
            "syntax_error": '''
```python
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums)  # Missing colon
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
```
'''
        }
    }
    
    problem = LEETCODE_PROBLEMS["two_sum"]
    print(f"\n📝 Problem: {problem['name']}")
    print(f"   Test cases: {len(problem['test_cases'])}")
    
    for response_type, response in sample_responses["two_sum"].items():
        print(f"\n   Testing {response_type} response...")
        result = evaluator.evaluate(response, problem['test_cases'], problem['func_name'])
        
        status = "✅" if result.passed else "❌"
        print(f"   {status} Pass rate: {result.pass_rate*100:.0f}% ({result.tests_passed}/{result.tests_total})")
        
        if result.syntax_error:
            print(f"   ⚠️ Syntax error: {result.syntax_error}")
        if result.runtime_error:
            print(f"   ⚠️ Runtime error: {result.runtime_error}")
        if result.logical_errors:
            print(f"   ⚠️ Logical errors: {len(result.logical_errors)}")

def demo_efficiency_evaluation():
    """Demo Layer 2: Code Efficiency Evaluation"""
    print("\n" + "="*60)
    print("🧪 DEMO: Layer 2 - Code Efficiency Evaluation")
    print("="*60)
    
    evaluator = CodeEfficiencyEvaluator(num_runs=3)
    
    # Two different implementations of Two Sum
    implementations = {
        "optimal_hashmap": '''
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
''',
        "bruteforce_nested": '''
def twoSum(nums, target):
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
'''
    }
    
    # Test inputs
    test_inputs = [
        ([2, 7, 11, 15], 9),
        (list(range(1000)) + [500, 501], 1001),  # Larger input
    ]
    
    for name, code in implementations.items():
        print(f"\n📊 Testing: {name}")
        result = evaluator.evaluate(code, test_inputs, 'twoSum')
        
        print(f"   ⚡ Avg Runtime: {result.avg_runtime_ms:.3f}ms")
        print(f"   💾 Peak Memory: {result.peak_memory_kb:.2f}KB")
        print(f"   📈 Time Complexity: {result.estimated_time_complexity}")
        print(f"   📈 Space Complexity: {result.estimated_space_complexity}")
        print(f"   🎯 Runtime Score: {result.runtime_score:.1f}/100")
        print(f"   🎯 Memory Score: {result.memory_score:.1f}/100")
        print(f"   🎯 Efficiency Score: {result.efficiency_score:.1f}/100")

def demo_full_pipeline():
    """Demo full evaluation pipeline"""
    print("\n" + "="*60)
    print("🧪 DEMO: Full Evaluation Pipeline")
    print("="*60)
    
    from main import AICodeEvaluator
    
    evaluator = AICodeEvaluator()
    
    # Sample Claude response (manual input simulation)
    claude_responses = {
        "two_sum": '''
Here's an efficient solution using a hash map:

```python
def twoSum(nums, target):
    """
    Find two numbers that add up to target.
    Time: O(n), Space: O(n)
    """
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
```

This solution uses a hash map to achieve O(n) time complexity.
''',
        "valid_parentheses": '''
```python
def isValid(s):
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    
    for char in s:
        if char in pairs:
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()
        else:
            stack.append(char)
    
    return len(stack) == 0
```
'''
    }
    
    print("\n📝 Evaluating Claude responses (manual input):")
    
    for problem_key, response in claude_responses.items():
        if problem_key in LEETCODE_PROBLEMS:
            result = evaluator.evaluate_response('claude-manual', problem_key, response)
            
            problem = LEETCODE_PROBLEMS[problem_key]
            print(f"\n   {problem['name']}:")
            status = "✅" if result.correctness_passed else "❌"
            print(f"   {status} Correctness: {result.correctness_pass_rate*100:.0f}%")
            print(f"   ⚡ Efficiency: {result.efficiency_score:.1f}/100")
            print(f"   📊 Overall: {result.overall_score:.1f}/100")
    
    evaluator.print_summary()

def main():
    print("\n" + "="*60)
    print("🚀 SOCRATESCODE EVALUATOR - DEMO")
    print("="*60)
    print("\nThis demo tests the evaluation pipeline without API calls.")
    print("It uses sample AI responses to demonstrate the methodology.")
    
    # Run demos
    demo_correctness_evaluation()
    demo_efficiency_evaluation()
    demo_full_pipeline()
    
    print("\n" + "="*60)
    print("✅ DEMO COMPLETED")
    print("="*60)
    print("\nTo run with actual APIs:")
    print("  export GEMINI_API_KEY='your-key'")
    print("  export OPENAI_API_KEY='your-key'")
    print("  python main.py --models gemini gpt")
    print("\nFor Claude (manual input):")
    print("  python main.py --interactive")

if __name__ == "__main__":
    main()

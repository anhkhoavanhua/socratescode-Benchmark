#!/usr/bin/env python3
"""
SocratesCode Scientific Benchmark - Real Data Execution
Executes real API calls to Gemini and GPT, evaluates responses,
and calculates scientific metrics (Pass@k, Efficiency) based on actual data.
"""

import sys
import os
import math
import statistics
import argparse
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from evaluators.correctness import CodeCorrectnessEvaluator, LEETCODE_PROBLEMS
from evaluators.efficiency import CodeEfficiencyEvaluator
from utils.api_clients import AIClientFactory

class ScientificBenchmarkRunner:
    def __init__(self, n_samples: int = 5):
        self.n_samples = n_samples
        self.correctness_eval = CodeCorrectnessEvaluator()
        self.efficiency_eval = CodeEfficiencyEvaluator(num_runs=3) # 3 runs for efficiency stability
        self.problem = LEETCODE_PROBLEMS["two_sum"] # Focus on one problem for depth
        
    def calculate_pass_at_k(self, n: int, c: int, k: int) -> float:
        """Calculate pass@k metric: 1 - C(n-c, k) / C(n, k)"""
        if n - c < k:
            return 1.0
        if k <= 0: 
            return 0.0
            
        try:
            numer = math.comb(n - c, k)
            denom = math.comb(n, k)
            return 1.0 - (numer / denom)
        except ValueError:
            return 0.0

    def run_model_benchmark(self, model_name: str) -> Dict[str, Any]:
        """Run benchmark for a specific model"""
        print(f"\n🤖 Benchmarking {model_name} (n={self.n_samples})...")
        
        try:
            client = AIClientFactory.create(model_name)
        except Exception as e:
            print(f"   ❌ Failed to initialize {model_name}: {e}")
            return None

        results = []
        correct_count = 0
        efficiency_scores = []
        runtimes = []
        
        prompt = f"""
Solve the following LeetCode problem in Python.
Provide a clean, efficient solution with the function signature as specified.

Problem: {self.problem['name']}
Description: {self.problem['description']}

Function Name: {self.problem['func_name']}
Return only the Python code.
"""

        for i in range(self.n_samples):
            print(f"   Sample {i+1}/{self.n_samples}...", end="\r")
            
            # 1. Generate
            response = client.generate(prompt)
            if response.error:
                print(f"   ❌ Error: {response.error}")
                continue
                
            # 2. Evaluate Correctness
            c_result = self.correctness_eval.evaluate(
                response.response, 
                self.problem['test_cases'], 
                self.problem['func_name']
            )
            
            # 3. Evaluate Efficiency (if correct)
            e_result = None
            if c_result.passed:
                correct_count += 1
                # Extract code specifically for efficiency run
                code = c_result.extracted_code
                test_inputs = [tc.input_data for tc in self.problem['test_cases']]
                e_result = self.efficiency_eval.evaluate(
                    code, 
                    test_inputs, 
                    self.problem['func_name']
                )
                efficiency_scores.append(e_result.efficiency_score)
                runtimes.append(e_result.avg_runtime_ms)
            
            results.append({
                "correctness": c_result,
                "efficiency": e_result,
                "response": response
            })
            
        print(f"   ✅ Completed. Correct: {correct_count}/{self.n_samples}")
        
        # Calculate Metrics
        pass_at_1 = self.calculate_pass_at_k(self.n_samples, correct_count, 1)
        pass_at_5 = self.calculate_pass_at_k(self.n_samples, correct_count, 5) if self.n_samples >= 5 else 0.0
        
        avg_efficiency = statistics.mean(efficiency_scores) if efficiency_scores else 0.0
        avg_runtime = statistics.mean(runtimes) if runtimes else 0.0
        
        return {
            "model": model_name,
            "n": self.n_samples,
            "c": correct_count,
            "pass_at_1": pass_at_1,
            "pass_at_5": pass_at_5,
            "avg_efficiency": avg_efficiency,
            "avg_runtime": avg_runtime,
            "raw_results": results
        }

    def generate_report(self, all_data: List[Dict[str, Any]], filename: str = "SOCRATES_REAL_REPORT.md"):
        """Generate markdown report from real data"""
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        content = f"""# SocratesCode Scientific Benchmark Report (Real Data)

**Date:** {timestamp}
**Benchmark Script:** `run_scientific_benchmark.py`
**Problem Analyzed:** {self.problem['name']}

## 1. Executive Summary
This report presents empirical results from evaluating AI models using the SocratesCode pipeline. 
Data was collected by generating $n={self.n_samples}$ solutions per model and evaluating them against functional correctness and efficiency metrics.

---

## 2. Correctness Analysis (Layer 1)

| Model | n (Samples) | c (Correct) | **Pass@1** | **Pass@5** |
|-------|-------------|-------------|------------|------------|
"""
        
        for data in all_data:
            if not data: continue
            content += f"| {data['model'].upper()} | {data['n']} | {data['c']} | **{data['pass_at_1']:.4f}** | {data['pass_at_5']:.4f} |\n"
            
        content += """
> **Pass@k Analysis:**
> * **Pass@1** represents the reliability of the model on a single try.
> * **Pass@5** represents the potential of the model if allowed 5 attempts (e.g., with re-ranking).

---

## 3. Efficiency Profiling (Layer 2)

| Model | Avg Efficiency Score | Avg Runtime (ms) |
|-------|----------------------|------------------|
"""
        for data in all_data:
            if not data: continue
            content += f"| {data['model'].upper()} | {data['avg_efficiency']:.1f}/100 | {data['avg_runtime']:.3f} ms |\n"

        content += """
> **Efficiency Metrics:**
> Scores are based on runtime and memory usage relative to optimal baselines (BigCodeBench methodology).

---

## 4. Detailed Observations

"""
        for data in all_data:
            if not data: continue
            model = data['model'].upper()
            content += f"### {model}\n"
            
            # Find best solution
            best_run = max((r for r in data['raw_results'] if r['correctness'].passed), 
                          key=lambda x: x['efficiency'].efficiency_score, default=None)
            
            if best_run:
                content += f"- **Best Efficiency:** {best_run['efficiency'].efficiency_score:.1f}/100\n"
                content += f"- **Complexity:** {best_run['efficiency'].estimated_time_complexity}\n"
                content += f"- **Code Snippet:**\n```python\n{best_run['correctness'].extracted_code}\n```\n"
            else:
                content += "- No correct solutions found to analyze efficiency.\n"
            content += "\n"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"\n✅ Real benchmark report generated: {filename}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=5, help='Number of samples per model')
    args = parser.parse_args()

    runner = ScientificBenchmarkRunner(n_samples=args.samples)
    
    models = ['gemini', 'gpt']
    results = []
    
    for model in models:
        data = runner.run_model_benchmark(model)
        if data:
            results.append(data)
            
    runner.generate_report(results)

if __name__ == "__main__":
    main()
"""
SocratesCode AI Evaluator - Main Pipeline
Evaluates AI coding responses using scientific benchmark methodologies

Scientific basis:
- Layer 1: Code Correctness (APPS/MBPP methodology)
- Layer 2: Code Efficiency (BigCodeBench/EvoCodeBench methodology)
- Layer 3: Human Validation Sampling (ITS research)

Usage:
    python main.py --models gemini gpt claude --problems two_sum valid_parentheses
    python main.py --interactive
    python main.py --load-claude claude_responses.json
"""


import sys
from dotenv import load_dotenv
import os
import json
import csv
import argparse
import random
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

load_dotenv()


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from evaluators.correctness import (
    CodeCorrectnessEvaluator, 
    CorrectnessResult, 
    TestCase,
    LEETCODE_PROBLEMS,
    CodeExtractor
)
from evaluators.efficiency import CodeEfficiencyEvaluator, EfficiencyResult
from utils.api_clients import AIClientFactory, AIResponse

@dataclass
class EvaluationResult:
    """Complete evaluation result for one AI response"""
    model: str
    problem_id: str
    problem_name: str
    timestamp: str
    
    # Layer 1: Correctness
    correctness_passed: bool
    correctness_pass_rate: float
    tests_passed: int
    tests_total: int
    syntax_error: Optional[str]
    runtime_error: Optional[str]
    
    # Layer 2: Efficiency  
    avg_runtime_ms: float
    peak_memory_kb: float
    runtime_score: float
    memory_score: float
    efficiency_score: float
    time_complexity: str
    space_complexity: str
    
    # Overall
    overall_score: float
    needs_human_validation: bool
    
    # Raw data
    ai_response: str
    extracted_code: str
    api_latency_ms: float

class AICodeEvaluator:
    """
    Main evaluation pipeline
    
    Combines:
    - Layer 1: Code Correctness (pass@k, functional testing)
    - Layer 2: Code Efficiency (runtime, memory, complexity)
    - Layer 3: Human Validation Sampling (10% random)
    
    NO semantic similarity comparison - AI responses naturally vary.
    Only code correctness and efficiency matter.
    """
    
    def __init__(self):
        self.correctness_eval = CodeCorrectnessEvaluator()
        self.efficiency_eval = CodeEfficiencyEvaluator()
        self.code_extractor = CodeExtractor()
        self.results: List[EvaluationResult] = []
    
    def generate_prompt(self, problem: Dict) -> str:
        """Generate coding prompt for AI"""
        return f"""Solve the following LeetCode problem in Python.
Provide a clean, efficient solution with the function signature as specified.

Problem: {problem['name']} (ID: {problem['id']}, Difficulty: {problem['difficulty']})

Description: {problem['description']}

Provide only the Python code solution with the function named '{problem['func_name']}'.
Include necessary imports if needed.
"""
    
    def evaluate_response(self, 
                         model_name: str,
                         problem_key: str,
                         ai_response: str,
                         api_latency: float = 0) -> EvaluationResult:
        """
        Evaluate a single AI response
        
        Layer 1: Test code correctness
        Layer 2: Measure efficiency
        Layer 3: Flag for human validation (10% sample)
        """
        problem = LEETCODE_PROBLEMS[problem_key]
        
        # Extract code
        code = self.code_extractor.extract(ai_response)
        
        # Layer 1: Correctness
        correctness_result = self.correctness_eval.evaluate(
            ai_response,
            problem['test_cases'],
            problem['func_name']
        )
        
        # Layer 2: Efficiency (only if code is correct)
        if correctness_result.passed and code:
            test_inputs = [tc.input_data for tc in problem['test_cases']]
            efficiency_result = self.efficiency_eval.evaluate(
                code,
                test_inputs,
                problem['func_name']
            )
        else:
            efficiency_result = EfficiencyResult(
                avg_runtime_ms=0,
                min_runtime_ms=0,
                max_runtime_ms=0,
                runtime_score=0,
                peak_memory_kb=0,
                avg_memory_kb=0,
                memory_score=0,
                estimated_time_complexity="N/A",
                estimated_space_complexity="N/A",
                efficiency_score=0,
                num_runs=0
            )
        
        # Calculate overall score
        # Weight: Correctness 60%, Efficiency 40%
        overall_score = (
            correctness_result.pass_rate * 60 +
            efficiency_result.efficiency_score * 0.4
        )
        
        # Layer 3: Flag for human validation (10% sample + low scores)
        needs_human_validation = (
            random.random() < config.HUMAN_VALIDATION_RATE or
            overall_score < 50 or
            correctness_result.syntax_error is not None
        )
        
        result = EvaluationResult(
            model=model_name,
            problem_id=str(problem['id']),
            problem_name=problem['name'],
            timestamp=datetime.now().isoformat(),
            correctness_passed=correctness_result.passed,
            correctness_pass_rate=correctness_result.pass_rate,
            tests_passed=correctness_result.tests_passed,
            tests_total=correctness_result.tests_total,
            syntax_error=correctness_result.syntax_error,
            runtime_error=correctness_result.runtime_error,
            avg_runtime_ms=efficiency_result.avg_runtime_ms,
            peak_memory_kb=efficiency_result.peak_memory_kb,
            runtime_score=efficiency_result.runtime_score,
            memory_score=efficiency_result.memory_score,
            efficiency_score=efficiency_result.efficiency_score,
            time_complexity=efficiency_result.estimated_time_complexity,
            space_complexity=efficiency_result.estimated_space_complexity,
            overall_score=overall_score,
            needs_human_validation=needs_human_validation,
            ai_response=ai_response[:1000],  # Truncate for storage
            extracted_code=code[:500] if code else "",
            api_latency_ms=api_latency
        )
        
        self.results.append(result)
        return result
    
    def run_evaluation(self, 
                      models: List[str] = None,
                      problems: List[str] = None,
                      claude_responses: Dict[str, str] = None) -> List[EvaluationResult]:
        """
        Run full evaluation pipeline
        
        Args:
            models: List of model types ('gemini', 'gpt', 'claude')
            problems: List of problem keys from LEETCODE_PROBLEMS
            claude_responses: Pre-loaded Claude responses {problem_key: response}
        """
        models = models or ['gemini', 'gpt', 'claude']
        problems = problems or list(LEETCODE_PROBLEMS.keys())
        claude_responses = claude_responses or {}
        
        # Create AI clients
        clients = {}
        for model in models:
            try:
                clients[model] = AIClientFactory.create(model)
            except Exception as e:
                print(f"⚠️ Could not create {model} client: {e}")
        
        print("\n" + "="*70)
        print("🚀 SOCRATESCODE AI EVALUATOR")
        print("="*70)
        print(f"Models: {', '.join(clients.keys())}")
        print(f"Problems: {', '.join(problems)}")
        print("="*70 + "\n")
        
        results = []
        
        for problem_key in problems:
            problem = LEETCODE_PROBLEMS[problem_key]
            prompt = self.generate_prompt(problem)
            
            print(f"\n📝 Problem: {problem['name']} ({problem['difficulty']})")
            print("-" * 50)
            
            for model_name, client in clients.items():
                print(f"\n  🤖 Testing {model_name}...")
                
                # Get AI response
                if model_name == 'claude' and problem_key in claude_responses:
                    # Use pre-loaded Claude response
                    response = AIResponse(
                        model='claude',
                        response=claude_responses[problem_key],
                        prompt=prompt,
                        latency_ms=0
                    )
                else:
                    response = client.generate(prompt)
                
                if response.error:
                    print(f"     ❌ API Error: {response.error}")
                    continue
                
                # Evaluate
                result = self.evaluate_response(
                    model_name,
                    problem_key,
                    response.response,
                    response.latency_ms
                )
                
                # Print results
                status = "✅" if result.correctness_passed else "❌"
                print(f"     {status} Correctness: {result.correctness_pass_rate*100:.0f}% ({result.tests_passed}/{result.tests_total})")
                print(f"     ⚡ Efficiency: {result.efficiency_score:.1f}/100 (Runtime: {result.avg_runtime_ms:.2f}ms)")
                print(f"     📊 Overall: {result.overall_score:.1f}/100")
                
                if result.needs_human_validation:
                    print(f"     👁️ Flagged for human validation")
                
                results.append(result)
        
        return results
    
    def export_results(self, filepath: str = None):
        """Export results to CSV"""
        filepath = filepath or f"results/evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        
        if not self.results:
            print("No results to export")
            return
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self.results[0]).keys())
            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))
        
        print(f"\n✅ Results exported to {filepath}")
    
    def print_summary(self):
        """Print evaluation summary"""
        if not self.results:
            print("No results to summarize")
            return
        
        print("\n" + "="*70)
        print("📊 EVALUATION SUMMARY")
        print("="*70)
        
        # Group by model
        by_model = {}
        for r in self.results:
            if r.model not in by_model:
                by_model[r.model] = []
            by_model[r.model].append(r)
        
        for model, results in by_model.items():
            avg_correctness = sum(r.correctness_pass_rate for r in results) / len(results)
            avg_efficiency = sum(r.efficiency_score for r in results) / len(results)
            avg_overall = sum(r.overall_score for r in results) / len(results)
            passed_count = sum(1 for r in results if r.correctness_passed)
            
            print(f"\n🤖 {model.upper()}")
            print(f"   Problems passed: {passed_count}/{len(results)}")
            print(f"   Avg Correctness: {avg_correctness*100:.1f}%")
            print(f"   Avg Efficiency:  {avg_efficiency:.1f}/100")
            print(f"   Avg Overall:     {avg_overall:.1f}/100")
        
        # Needs validation count
        validation_needed = sum(1 for r in self.results if r.needs_human_validation)
        print(f"\n👁️ Flagged for human validation: {validation_needed}/{len(self.results)}")
        print("="*70)

def interactive_mode():
    """Interactive evaluation mode"""
    evaluator = AICodeEvaluator()
    
    print("\n" + "="*70)
    print("🎯 INTERACTIVE MODE")
    print("="*70)
    print("\nAvailable problems:")
    for key, prob in LEETCODE_PROBLEMS.items():
        print(f"  - {key}: {prob['name']} ({prob['difficulty']})")
    
    print("\nCommands:")
    print("  evaluate <model> <problem> - Evaluate a model on a problem")
    print("  paste <problem>            - Paste AI response for evaluation")
    print("  summary                    - Show summary")
    print("  export                     - Export results to CSV")
    print("  quit                       - Exit")
    print("="*70)
    
    while True:
        try:
            cmd = input("\n> ").strip().split()
            if not cmd:
                continue
            
            if cmd[0] == 'quit':
                break
            
            elif cmd[0] == 'evaluate' and len(cmd) >= 3:
                model, problem = cmd[1], cmd[2]
                if problem not in LEETCODE_PROBLEMS:
                    print(f"Unknown problem: {problem}")
                    continue
                
                client = AIClientFactory.create(model)
                prompt = evaluator.generate_prompt(LEETCODE_PROBLEMS[problem])
                response = client.generate(prompt)
                
                if response.error:
                    print(f"Error: {response.error}")
                    continue
                
                result = evaluator.evaluate_response(model, problem, response.response, response.latency_ms)
                print(f"\nResult: {result.overall_score:.1f}/100")
            
            elif cmd[0] == 'paste' and len(cmd) >= 2:
                problem = cmd[1]
                if problem not in LEETCODE_PROBLEMS:
                    print(f"Unknown problem: {problem}")
                    continue
                
                print("Paste AI response (enter 'END' when done):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == 'END':
                        break
                    lines.append(line)
                
                response = '\n'.join(lines)
                result = evaluator.evaluate_response('manual', problem, response)
                print(f"\nResult: {result.overall_score:.1f}/100")
            
            elif cmd[0] == 'summary':
                evaluator.print_summary()
            
            elif cmd[0] == 'export':
                evaluator.export_results()
            
            else:
                print("Unknown command")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description='SocratesCode AI Evaluator')
    parser.add_argument('--models', nargs='+', default=['gemini', 'gpt'],
                       help='Models to evaluate (gemini, gpt, claude)')
    parser.add_argument('--problems', nargs='+', 
                       help='Problems to test (default: all)')
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive mode')
    parser.add_argument('--load-claude', type=str,
                       help='Load Claude responses from JSON file')
    parser.add_argument('--output', type=str,
                       help='Output CSV file path')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    # Load Claude responses if provided
    claude_responses = {}
    if args.load_claude:
        try:
            with open(args.load_claude, 'r') as f:
                data = json.load(f)
            claude_responses = {item['problem']: item['response'] for item in data}
            print(f"✅ Loaded {len(claude_responses)} Claude responses")
        except Exception as e:
            print(f"⚠️ Could not load Claude responses: {e}")
    
    # Run evaluation
    evaluator = AICodeEvaluator()
    evaluator.run_evaluation(
        models=args.models,
        problems=args.problems,
        claude_responses=claude_responses
    )
    
    # Print summary and export
    evaluator.print_summary()
    evaluator.export_results(args.output)

if __name__ == "__main__":
    main()

# src/pipeline/main_pipeline.py
"""
Main Evaluation Pipeline - ORPS Adapted
Orchestrates: Collection → Execution → Algorithm Judge → Step Judge → Results
"""
import os
import sys
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import MODELS, get_api_keys, EvaluationConfig
from config.prompts import COLLECTION_PROMPT

from src.collectors import GPTCollector, GeminiCollector, GeminiJudge, AIResponse
from src.evaluators import (
    ExecutionEvaluator, extract_test_cases,
    AlgorithmJudge, get_optimal_info,
    StepQualityJudge
)

@dataclass
class ModelResult:
    """Result for one model on one problem"""
    problem_id: str
    model_name: str
    response: Dict
    execution: Dict
    algorithm_eval: Dict
    reasoning_eval: Dict
    combined_score: float

@dataclass
class ProblemResult:
    """Results for all models on one problem"""
    problem_id: str
    problem_title: str
    model_results: Dict[str, ModelResult]
    best_overall: str


class EvaluationPipeline:
    """
    Main ORPS-based evaluation pipeline
    
    Flow:
    1. Collect AI responses (reasoning steps + code)
    2. Execute code with tests (Outcome verification - FREE)
    3. Judge algorithm quality (Self-critique)
    4. Judge step quality (Process evaluation, guided by execution)
    5. Aggregate scores
    """
    
    def __init__(self, config: EvaluationConfig = None):
        self.config = config or EvaluationConfig()
        self.api_keys = get_api_keys()
        
        # Initialize collectors
        self.collectors = {}
        self._init_collectors()
        
        # Initialize evaluators
        self.executor = ExecutionEvaluator(timeout=self.config.code_timeout_seconds)
        
        # Initialize judge (FREE with Gemini Flash!)
        if self.api_keys["google"]:
            self.judge = GeminiJudge(
                api_key=self.api_keys["google"],
                model_id=MODELS[self.config.judge_model].model_id
            )
            self.algo_judge = AlgorithmJudge(self.judge)
            self.step_judge = StepQualityJudge(self.judge)
        else:
            self.judge = None
            print("⚠️  No Google API key - LLM judges disabled")
    
    def _init_collectors(self):
        """Initialize collectors for each model"""
        for model_name in self.config.test_models:
            if model_name not in MODELS:
                print(f"⚠️  Unknown model: {model_name}")
                continue
            
            model_config = MODELS[model_name]
            
            if model_config.api_type == "openai" and self.api_keys["openai"]:
                self.collectors[model_name] = GPTCollector(model_config, self.api_keys["openai"])
            elif model_config.api_type == "google" and self.api_keys["google"]:
                self.collectors[model_name] = GeminiCollector(model_config, self.api_keys["google"])
    
    def run(self, problems: List[Dict]) -> Dict[str, Any]:
        """Run complete evaluation"""
        print("=" * 60)
        print("🚀 ORPS-BASED AI REASONING EVALUATION")
        print(f"   Models: {', '.join(self.config.test_models)}")
        print(f"   Problems: {len(problems)}")
        print(f"   Judge: {self.config.judge_model}")
        print("=" * 60)
        
        all_results = []
        
        for i, problem in enumerate(problems):
            title = problem.get("title", problem.get("id", "Unknown"))
            print(f"\n[{i+1}/{len(problems)}] {title}")
            print("-" * 40)
            
            result = self._evaluate_problem(problem)
            all_results.append(result)
            
            # Save intermediate
            self._save_results(all_results)
        
        # Summary
        summary = self._create_summary(all_results)
        
        return {
            "config": asdict(self.config),
            "timestamp": datetime.now().isoformat(),
            "results": [self._result_to_dict(r) for r in all_results],
            "summary": summary
        }
    
    def _evaluate_problem(self, problem: Dict) -> ProblemResult:
        """Evaluate all models on one problem"""
        model_results = {}
        
        for model_name in self.config.test_models:
            collector = self.collectors.get(model_name)
            if not collector:
                continue
            
            print(f"\n  📤 {model_name}...")
            
            try:
                # 1. COLLECT response
                response = collector.collect(problem, COLLECTION_PROMPT)
                print(f"     ✓ {len(response.reasoning_steps)} steps, {len(response.code)} chars code")
            except Exception as e:
                print(f"     ❌ Collection failed: {e}")
                continue
            
            # 2. EXECUTE code (ORM - FREE!)
            print(f"  ⚡ Execution...")
            test_cases = extract_test_cases(problem)
            exec_result = None
            if test_cases:
                exec_result = self.executor.evaluate(
                    response.code, test_cases,
                    response.problem_id, model_name
                )
                print(f"     ✓ {exec_result.pass_rate:.0%} pass ({exec_result.passed_tests}/{exec_result.total_tests})")
            else:
                print(f"     ⚠ No test cases")
            
            # 3. JUDGE algorithm (Self-Critique)
            algo_eval = None
            if self.judge:
                print(f"  🧠 Algorithm judge...")
                optimal = get_optimal_info(problem.get("id", problem.get("title", "")))
                algo_eval = self.algo_judge.evaluate(problem, response, optimal)
                print(f"     ✓ Score: {algo_eval.overall_score}/5")
            
            # 4. JUDGE steps (Process, guided by execution)
            step_eval = None
            if self.judge:
                print(f"  📝 Step judge...")
                step_eval = self.step_judge.evaluate(problem, response, exec_result)
                print(f"     ✓ Score: {step_eval.overall_score}/5")
            
            # 5. COMBINE scores
            combined = self._calculate_combined(exec_result, algo_eval, step_eval)
            print(f"  📊 Combined: {combined:.1f}/100")
            
            model_results[model_name] = ModelResult(
                problem_id=response.problem_id,
                model_name=model_name,
                response=response.to_dict(),
                execution=exec_result.to_dict() if exec_result else {},
                algorithm_eval=algo_eval.to_dict() if algo_eval else {},
                reasoning_eval=step_eval.to_dict() if step_eval else {},
                combined_score=combined
            )
        
        # Find best
        best = max(model_results.values(), key=lambda x: x.combined_score).model_name if model_results else ""
        
        return ProblemResult(
            problem_id=problem.get("id", problem.get("title", "unknown")),
            problem_title=problem.get("title", "Unknown"),
            model_results=model_results,
            best_overall=best
        )
    
    def _calculate_combined(self, exec_result, algo_eval, step_eval) -> float:
        """Calculate weighted combined score (0-100)"""
        exec_score = exec_result.pass_rate * 100 if exec_result else 0
        algo_score = algo_eval.overall_score * 20 if algo_eval else 0  # 0-5 → 0-100
        step_score = step_eval.overall_score * 20 if step_eval else 0
        
        return round(
            self.config.execution_weight * exec_score +
            self.config.algorithm_weight * algo_score +
            self.config.step_quality_weight * step_score,
            2
        )
    
    def _create_summary(self, results: List[ProblemResult]) -> Dict:
        """Create summary statistics"""
        summary = {model: {
            "problems": 0, "avg_pass_rate": 0, "avg_algo_score": 0,
            "avg_step_score": 0, "avg_combined": 0, "wins": 0
        } for model in self.config.test_models}
        
        for result in results:
            for model_name, mr in result.model_results.items():
                s = summary[model_name]
                s["problems"] += 1
                s["avg_pass_rate"] += mr.execution.get("pass_rate", 0)
                s["avg_algo_score"] += mr.algorithm_eval.get("overall_score", 0)
                s["avg_step_score"] += mr.reasoning_eval.get("overall_score", 0)
                s["avg_combined"] += mr.combined_score
            
            if result.best_overall in summary:
                summary[result.best_overall]["wins"] += 1
        
        # Calculate averages
        for s in summary.values():
            n = s["problems"]
            if n > 0:
                s["avg_pass_rate"] = round(s["avg_pass_rate"] / n, 3)
                s["avg_algo_score"] = round(s["avg_algo_score"] / n, 2)
                s["avg_step_score"] = round(s["avg_step_score"] / n, 2)
                s["avg_combined"] = round(s["avg_combined"] / n, 2)
        
        return summary
    
    def _result_to_dict(self, result: ProblemResult) -> Dict:
        return {
            "problem_id": result.problem_id,
            "problem_title": result.problem_title,
            "model_results": {
                name: {
                    "problem_id": mr.problem_id,
                    "model_name": mr.model_name,
                    "execution": mr.execution,
                    "algorithm_eval": mr.algorithm_eval,
                    "reasoning_eval": mr.reasoning_eval,
                    "combined_score": mr.combined_score
                }
                for name, mr in result.model_results.items()
            },
            "best_overall": result.best_overall
        }
    
    def _save_results(self, results: List[ProblemResult]):
        """Save intermediate results"""
        os.makedirs(self.config.output_dir, exist_ok=True)
        path = os.path.join(self.config.output_dir, "results.json")
        
        with open(path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "completed": len(results),
                "results": [self._result_to_dict(r) for r in results]
            }, f, indent=2)


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ORPS AI Reasoning Evaluation")
    parser.add_argument("--problems", required=True, help="Path to problems JSON")
    parser.add_argument("--models", nargs="+", default=["gemini-pro"], help="Models to test")
    parser.add_argument("--judge", default="gemini-flash", help="Judge model")
    parser.add_argument("--num", type=int, default=10, help="Number of problems")
    parser.add_argument("--output", default="data/results", help="Output dir")
    
    args = parser.parse_args()
    
    # Load problems
    with open(args.problems) as f:
        problems = json.load(f)[:args.num]
    
    # Configure
    config = EvaluationConfig(
        test_models=args.models,
        judge_model=args.judge,
        num_problems=len(problems),
        output_dir=args.output
    )
    
    # Run
    pipeline = EvaluationPipeline(config)
    results = pipeline.run(problems)
    
    # Save final
    final_path = os.path.join(args.output, "final_results.json")
    with open(final_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for model, stats in results["summary"].items():
        print(f"\n{model}:")
        print(f"  Pass Rate: {stats['avg_pass_rate']:.1%}")
        print(f"  Algorithm: {stats['avg_algo_score']}/5")
        print(f"  Reasoning: {stats['avg_step_score']}/5")
        print(f"  Combined: {stats['avg_combined']}/100")
        print(f"  Wins: {stats['wins']}")
    
    print(f"\n✅ Results: {final_path}")


if __name__ == "__main__":
    main()

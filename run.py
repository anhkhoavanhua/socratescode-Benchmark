#!/usr/bin/env python3
"""
Quick Run Script for ORPS AI Evaluation
Usage: python run.py
"""
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import validate_api_keys, EvaluationConfig
from src.pipeline import EvaluationPipeline

def main():
    print("=" * 60)
    print("🚀 ORPS AI REASONING EVALUATION")
    print("=" * 60)
    
    # Check API keys
    print("\n📋 Checking API keys...")
    if not validate_api_keys(["gemini-2.5-flash-lite"]):
        print("\n❌ Set GOOGLE_API_KEY to continue:")
        print("   export GOOGLE_API_KEY='AIza...'")
        return
    
    # Load problems
    print("\n📚 Loading problems...")
    with open("data/leetcode_problems.json") as f:
        problems = json.load(f)
    
    # Quick test: first 3 problems
    problems = problems[:3]
    print(f"   Using {len(problems)} problems for quick test")
    
    # Configure - using FREE Gemini only!
    config = EvaluationConfig(
        test_models=["gemini-2.5-flash-lite"],  # FREE
        judge_model="gemini-flash",   # FREE
        num_problems=len(problems)
    )
    
    # Run
    print("\n🔬 Starting evaluation...")
    pipeline = EvaluationPipeline(config)
    results = pipeline.run(problems)
    
    # Save
    os.makedirs("data/results", exist_ok=True)
    with open("data/results/final.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    
    for model, stats in results["summary"].items():
        print(f"\n{model}:")
        print(f"  ✓ Pass Rate: {stats['avg_pass_rate']:.1%}")
        print(f"  ✓ Algorithm Score: {stats['avg_algo_score']}/5")
        print(f"  ✓ Reasoning Score: {stats['avg_step_score']}/5")
        print(f"  ✓ Combined Score: {stats['avg_combined']}/100")
    
    print(f"\n✅ Results saved to: data/results/final.json")
    print("\n💡 To compare GPT vs Gemini, run:")
    print("   export OPENAI_API_KEY='sk-...'")
    print("   python src/pipeline/main_pipeline.py --problems data/leetcode_problems.json --models gemini-pro gpt-4o-mini")


if __name__ == "__main__":
    main()

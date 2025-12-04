# src/evaluators/algorithm_judge.py
"""
Algorithm Quality Judge - Đánh giá algorithm choice
Sử dụng LLM-as-Judge (Gemini Flash - FREE)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class AlgorithmEvaluation:
    """Algorithm evaluation result"""
    problem_id: str
    model_name: str
    optimality_score: float
    appropriateness_score: float
    justification_score: float
    overall_score: float
    feedback: str
    raw_response: Dict = None
    
    def to_dict(self):
        return {
            "problem_id": self.problem_id,
            "model_name": self.model_name,
            "optimality_score": self.optimality_score,
            "appropriateness_score": self.appropriateness_score,
            "justification_score": self.justification_score,
            "overall_score": self.overall_score,
            "feedback": self.feedback
        }


class AlgorithmJudge:
    """
    Evaluates algorithm/approach quality
    Part of ORPS "Self-Critique" mechanism
    """
    
    PROMPT = """You are an expert algorithm evaluator.

## Problem:
{problem}

## Optimal Solution:
- Time: {optimal_time}
- Space: {optimal_space}  
- Approach: {optimal_approach}

## AI's Algorithm:
{ai_algorithm}
- Time: {ai_time}
- Space: {ai_space}

Score 0-5:
1. Optimality: Is it optimal?
2. Appropriateness: Right for this problem?
3. Justification: Well explained?

JSON only:
```json
{{"optimality_score": X, "appropriateness_score": X, "justification_score": X, "overall_score": X.X, "feedback": "..."}}
```"""
    
    def __init__(self, judge_client):
        self.judge = judge_client
    
    def evaluate(self, problem: Dict, ai_response, optimal_info: Dict = None) -> AlgorithmEvaluation:
        """Evaluate algorithm quality"""
        optimal = optimal_info or {}
        
        prompt = self.PROMPT.format(
            problem=problem.get("title", "") + "\n" + problem.get("description", "")[:500],
            optimal_time=optimal.get("time", "Unknown"),
            optimal_space=optimal.get("space", "Unknown"),
            optimal_approach=optimal.get("approach", "Not specified"),
            ai_algorithm=ai_response.algorithm_description[:500],
            ai_time=ai_response.time_complexity,
            ai_space=ai_response.space_complexity
        )
        
        response = self.judge.judge(prompt)
        
        if "error" in response:
            return AlgorithmEvaluation(
                problem_id=ai_response.problem_id,
                model_name=ai_response.model_name,
                optimality_score=0, appropriateness_score=0,
                justification_score=0, overall_score=0,
                feedback=f"Error: {response.get('error')}",
                raw_response=response
            )
        
        return AlgorithmEvaluation(
            problem_id=ai_response.problem_id,
            model_name=ai_response.model_name,
            optimality_score=response.get("optimality_score", 0),
            appropriateness_score=response.get("appropriateness_score", 0),
            justification_score=response.get("justification_score", 0),
            overall_score=response.get("overall_score", 0),
            feedback=response.get("feedback", ""),
            raw_response=response
        )


# ============================================
# OPTIMAL SOLUTIONS DATABASE
# ============================================

OPTIMAL_SOLUTIONS = {
    "two-sum": {"time": "O(n)", "space": "O(n)", "approach": "Hash map"},
    "valid-parentheses": {"time": "O(n)", "space": "O(n)", "approach": "Stack"},
    "maximum-subarray": {"time": "O(n)", "space": "O(1)", "approach": "Kadane's algorithm"},
    "climbing-stairs": {"time": "O(n)", "space": "O(1)", "approach": "DP with optimization"},
    "best-time-to-buy-and-sell-stock": {"time": "O(n)", "space": "O(1)", "approach": "Single pass min tracking"},
    "contains-duplicate": {"time": "O(n)", "space": "O(n)", "approach": "Hash set"},
    "single-number": {"time": "O(n)", "space": "O(1)", "approach": "XOR"},
    "reverse-linked-list": {"time": "O(n)", "space": "O(1)", "approach": "Iterative reversal"},
    "merge-two-sorted-lists": {"time": "O(n+m)", "space": "O(1)", "approach": "Two pointers"},
    "move-zeroes": {"time": "O(n)", "space": "O(1)", "approach": "Two pointers in-place"},
}

def get_optimal_info(problem_id: str) -> Optional[Dict]:
    """Get optimal solution for problem"""
    normalized = problem_id.lower().replace(" ", "-").replace("_", "-")
    return OPTIMAL_SOLUTIONS.get(normalized)

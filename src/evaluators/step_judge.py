# src/evaluators/step_judge.py
"""
Step-Level Quality Judge - Đánh giá từng reasoning step
Đây là phần "PRM-style" trong ORPS (nhưng không cần train!)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class StepEvaluation:
    """Evaluation for a single step"""
    step_number: int
    step_title: str
    correctness: float
    clarity: float
    completeness: float
    logical_flow: float
    step_score: float
    issues: str
    
    def to_dict(self):
        return {
            "step_number": self.step_number,
            "step_title": self.step_title,
            "correctness": self.correctness,
            "clarity": self.clarity,
            "completeness": self.completeness,
            "logical_flow": self.logical_flow,
            "step_score": self.step_score,
            "issues": self.issues
        }

@dataclass
class ReasoningEvaluation:
    """Complete reasoning evaluation"""
    problem_id: str
    model_name: str
    step_evaluations: List[StepEvaluation] = field(default_factory=list)
    avg_correctness: float = 0
    avg_clarity: float = 0
    avg_completeness: float = 0
    avg_logical_flow: float = 0
    overall_score: float = 0
    
    def to_dict(self):
        return {
            "problem_id": self.problem_id,
            "model_name": self.model_name,
            "step_evaluations": [s.to_dict() for s in self.step_evaluations],
            "avg_correctness": self.avg_correctness,
            "avg_clarity": self.avg_clarity,
            "avg_completeness": self.avg_completeness,
            "avg_logical_flow": self.avg_logical_flow,
            "overall_score": self.overall_score
        }


class StepQualityJudge:
    """
    Evaluates reasoning step quality using LLM-as-Judge
    Faster batch version - evaluates all steps at once
    """
    
    PROMPT = """Evaluate ALL reasoning steps for this coding problem.

## Problem:
{problem}

## AI's Steps:
{all_steps}

## Execution Result:
{execution_result}

For EACH step, score 0-5: correctness, clarity, completeness, logical_flow.

JSON only:
```json
{{
    "step_scores": [
        {{"step": 1, "correctness": X, "clarity": X, "completeness": X, "flow": X, "issues": "..."}},
        {{"step": 2, "correctness": X, "clarity": X, "completeness": X, "flow": X, "issues": "..."}}
    ],
    "overall_reasoning_score": X.X,
    "major_issues": ["..."],
    "strengths": ["..."]
}}
```"""
    
    def __init__(self, judge_client):
        self.judge = judge_client
    
    def evaluate(self, problem: Dict, ai_response, 
                 execution_result=None) -> ReasoningEvaluation:
        """Evaluate all steps in one call (faster)"""
        
        # Format steps
        all_steps = self._format_steps(ai_response.reasoning_steps)
        
        # Format execution result
        exec_info = "Not executed"
        if execution_result:
            exec_info = f"Pass rate: {execution_result.pass_rate:.0%} ({execution_result.passed_tests}/{execution_result.total_tests})"
            if execution_result.has_syntax_error:
                exec_info += f"\nSyntax Error: {execution_result.syntax_error_msg}"
        
        prompt = self.PROMPT.format(
            problem=problem.get("title", "") + "\n" + problem.get("description", "")[:500],
            all_steps=all_steps,
            execution_result=exec_info
        )
        
        response = self.judge.judge(prompt)
        
        if "error" in response:
            return ReasoningEvaluation(
                problem_id=ai_response.problem_id,
                model_name=ai_response.model_name,
                overall_score=0
            )
        
        # Parse step scores
        step_evals = []
        for score in response.get("step_scores", []):
            step_evals.append(StepEvaluation(
                step_number=score.get("step", 0),
                step_title="",
                correctness=score.get("correctness", 0),
                clarity=score.get("clarity", 0),
                completeness=score.get("completeness", 0),
                logical_flow=score.get("flow", 0),
                step_score=(score.get("correctness", 0) + score.get("clarity", 0) + 
                           score.get("completeness", 0) + score.get("flow", 0)) / 4,
                issues=score.get("issues", "")
            ))
        
        # Calculate averages
        if step_evals:
            avg_c = sum(s.correctness for s in step_evals) / len(step_evals)
            avg_cl = sum(s.clarity for s in step_evals) / len(step_evals)
            avg_co = sum(s.completeness for s in step_evals) / len(step_evals)
            avg_f = sum(s.logical_flow for s in step_evals) / len(step_evals)
        else:
            avg_c = avg_cl = avg_co = avg_f = 0
        
        return ReasoningEvaluation(
            problem_id=ai_response.problem_id,
            model_name=ai_response.model_name,
            step_evaluations=step_evals,
            avg_correctness=round(avg_c, 2),
            avg_clarity=round(avg_cl, 2),
            avg_completeness=round(avg_co, 2),
            avg_logical_flow=round(avg_f, 2),
            overall_score=response.get("overall_reasoning_score", 0)
        )
    
    def _format_steps(self, steps) -> str:
        """Format steps for prompt"""
        formatted = []
        for step in steps:
            formatted.append(f"### Step {step.step_number}: {step.title}")
            formatted.append(step.content[:300])  # Limit each step
            formatted.append("")
        return "\n".join(formatted)

# config/prompts.py
"""
Prompt templates cho AI Reasoning Evaluation System
Adapted from ORPS methodology
"""

# ============================================
# PROMPT 1: DATA COLLECTION
# Yêu cầu AI giải LeetCode với reasoning steps
# ============================================

COLLECTION_PROMPT = """You are an expert programmer solving a LeetCode problem.

## Problem:
{problem_description}

## Instructions:
Solve this problem step-by-step. You MUST structure your response EXACTLY as follows:

### STEP 1: Problem Analysis
- What is the input/output?
- What are the constraints?
- What are the edge cases to consider?

### STEP 2: Algorithm Selection
- What algorithm/approach will you use?
- Why is this the best approach?
- What is the time complexity?
- What is the space complexity?

### STEP 3: Implementation Strategy
- Break down the implementation into logical parts
- Explain the key logic before writing code

### STEP 4: Edge Cases Handling
- How will you handle empty input?
- How will you handle boundary conditions?

### STEP 5: Code Implementation
```python
# Your complete, working code here
class Solution:
    def solve(self, ...):
        pass
```

### STEP 6: Complexity Analysis
- Final time complexity: O(?)
- Final space complexity: O(?)
- Explanation

IMPORTANT: Follow this exact format. Each step must have clear content."""

# ============================================
# PROMPT 2: ALGORITHM QUALITY JUDGE
# ============================================

ALGORITHM_JUDGE_PROMPT = """You are an expert algorithm evaluator.

## Problem:
{problem_description}

## Optimal Solution Info:
- Best time complexity: {optimal_time}
- Best space complexity: {optimal_space}
- Recommended approach: {optimal_approach}

## AI's Algorithm:
{ai_algorithm_description}
- Time: {ai_time}
- Space: {ai_space}

## Evaluation (0-5 scale):
1. **Optimality**: Is algorithm optimal?
2. **Appropriateness**: Is it appropriate for this problem?
3. **Justification**: How well justified?

Respond in JSON only:
```json
{{
    "optimality_score": <0-5>,
    "appropriateness_score": <0-5>,
    "justification_score": <0-5>,
    "overall_score": <average>,
    "feedback": "<brief explanation>"
}}
```"""

# ============================================
# PROMPT 3: STEP-LEVEL QUALITY JUDGE
# ============================================

STEP_JUDGE_PROMPT = """You are evaluating reasoning quality.

## Problem:
{problem_description}

## Previous Steps:
{previous_steps}

## Step to Evaluate:
**Step {step_number}: {step_title}**
{step_content}

## Criteria (0-5):
1. **Correctness**: Logic correct?
2. **Clarity**: Clear explanation?
3. **Completeness**: Covers what it should?
4. **Logical Flow**: Connects to previous steps?

Respond in JSON only:
```json
{{
    "correctness": <0-5>,
    "clarity": <0-5>,
    "completeness": <0-5>,
    "logical_flow": <0-5>,
    "step_score": <average>,
    "issues": "<issues or 'None'>"
}}
```"""

# ============================================
# PROMPT 4: BATCH STEP EVALUATION (Faster)
# ============================================

BATCH_STEP_JUDGE_PROMPT = """Evaluate ALL reasoning steps at once.

## Problem:
{problem_description}

## AI's Reasoning Steps:
{all_steps}

## Execution Result:
{execution_result}

For EACH step, score (0-5): correctness, clarity, completeness, logical_flow.

Respond in JSON only:
```json
{{
    "step_scores": [
        {{"step": 1, "correctness": X, "clarity": X, "completeness": X, "flow": X, "issues": "..."}},
        {{"step": 2, "correctness": X, "clarity": X, "completeness": X, "flow": X, "issues": "..."}}
    ],
    "overall_reasoning_score": <1-5>,
    "major_issues": ["...", "..."],
    "strengths": ["...", "..."]
}}
```"""

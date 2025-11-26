# SocratesCode AI Evaluator

## Đánh giá AI Coding Responses dựa trên các phương pháp Benchmark khoa học

### 📚 Cơ sở khoa học

Chương trình sử dụng 3 layers đánh giá dựa trên các nghiên cứu được công nhận:

#### Layer 1: Code Correctness (APPS/MBPP Methodology)
- **APPS** (UC Berkeley, 2021): 10,000 problems, pass@k metric
- **MBPP** (Google Research, 2021): Entry-level Python problems
- **HumanEval** (OpenAI, 2021): Functional correctness testing

#### Layer 2: Code Efficiency (BigCodeBench Methodology)
- **BigCodeBench** (2024, NeurIPS): Runtime/memory efficiency
- **EvoCodeBench** (NeurIPS 2024): Domain-Specific Improvement
- **LiveCodeBench** (2024): Multi-dimensional evaluation

#### Layer 3: Human Validation Sampling (ITS Research)
- 10% random sampling cho human review
- Based on Intelligent Tutoring Systems research

### 🔑 Key Features

- ✅ **KHÔNG so sánh semantic similarity** - AI responses tự nhiên khác nhau
- ✅ Chỉ đánh giá code **correctness** và **efficiency**
- ✅ Hỗ trợ **Gemini API**, **GPT API**, và **Claude manual input**
- ✅ Automated test execution
- ✅ Runtime/memory profiling
- ✅ Complexity estimation

### 📦 Installation

```bash
pip install google-generativeai openai
```

### 🔧 Configuration

Set API keys via environment variables:

```bash
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"
```

Hoặc edit trực tiếp trong `config.py`.

### 🚀 Usage

#### 1. Command Line Mode

```bash
# Evaluate Gemini and GPT on all problems
python main.py --models gemini gpt

# Evaluate specific problems
python main.py --models gemini gpt --problems two_sum valid_parentheses

# Include Claude with pre-loaded responses
python main.py --models gemini gpt claude --load-claude claude_responses.json
```

#### 2. Interactive Mode

```bash
python main.py --interactive
```

Commands:
- `evaluate <model> <problem>` - Evaluate a model
- `paste <problem>` - Paste AI response for evaluation
- `summary` - Show results summary
- `export` - Export to CSV

#### 3. Claude Manual Input

Vì Claude chưa có API, bạn có thể:

**Option A**: Nhập manual trong interactive mode
```bash
python main.py --interactive
> paste two_sum
[Paste Claude's response]
END
```

**Option B**: Pre-load responses từ JSON file
```json
[
    {
        "problem": "two_sum",
        "response": "def twoSum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []"
    }
]
```

```bash
python main.py --load-claude claude_responses.json
```

### 📊 Output Format

```
📊 EVALUATION SUMMARY
======================================================================

🤖 GEMINI
   Problems passed: 4/5
   Avg Correctness: 85.0%
   Avg Efficiency:  78.5/100
   Avg Overall:     82.1/100

🤖 GPT
   Problems passed: 5/5
   Avg Correctness: 100.0%
   Avg Efficiency:  82.3/100
   Avg Overall:     91.4/100

👁️ Flagged for human validation: 2/10
```

### 📁 File Structure

```
socratescode_evaluator/
├── config.py                 # Configuration
├── main.py                   # Main pipeline
├── evaluators/
│   ├── __init__.py
│   ├── correctness.py        # Layer 1: Code correctness
│   └── efficiency.py         # Layer 2: Code efficiency
├── utils/
│   ├── __init__.py
│   └── api_clients.py        # API clients
├── data/                     # Test data
└── results/                  # Output results
```

### 🔬 Evaluation Metrics

#### Correctness (60% weight)
- Pass rate: % test cases passed
- Syntax errors detected
- Runtime errors detected
- Logical errors identified

#### Efficiency (40% weight)
- Runtime score (0-100)
- Memory score (0-100)
- Time complexity estimate
- Space complexity estimate

#### Overall Score
```
overall_score = correctness_pass_rate * 60 + efficiency_score * 0.4
```

### 📝 Adding New Problems

Edit `evaluators/correctness.py`:

```python
LEETCODE_PROBLEMS["new_problem"] = {
    "id": 123,
    "name": "New Problem",
    "difficulty": "Medium",
    "description": "Problem description...",
    "test_cases": [
        TestCase([input], expected_output, "description"),
    ],
    "func_name": "solveProblem"
}
```

### 🎯 Research References

1. Chen et al. (2021). "Evaluating Large Language Models Trained on Code" - HumanEval
2. Austin et al. (2021). "Program Synthesis with Large Language Models" - MBPP
3. Hendrycks et al. (2021). "Measuring Coding Challenge Competence With APPS"
4. BigCodeBench (2024). "BigCodeBench: Benchmarking Code Generation"
5. EvoCodeBench (2024). "How Do Your Code LLMs Perform?"

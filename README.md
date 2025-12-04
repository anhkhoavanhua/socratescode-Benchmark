# ORPS AI Reasoning Evaluation
## Đánh giá Reasoning Steps của AI khi giải LeetCode

Hệ thống đánh giá và so sánh **reasoning quality** của AI models (GPT, Gemini) sử dụng phương pháp **ORPS** (Outcome-Refining Process Supervision).

---

## 🎯 ORPS là gì?

```
ORPS = Execution Verification + Self-Critique
         (ORM - FREE)          (LLM Judge - FREE với Gemini)
```

**Khác biệt so với các phương pháp cũ:**

| Phương pháp | Đánh giá | Chi phí |
|-------------|----------|---------|
| ORM (cũ) | Chỉ output cuối | Rẻ, không biết sai ở đâu |
| PRM (cũ) | Từng step | **Rất đắt** (cần train model) |
| **ORPS** | Từng step + Output | **Rẻ** (không cần train!) |

---

## 🚀 Quick Start

### 1. Cài đặt
```bash
pip install -r requirements.txt
```

### 2. Set API Key (Gemini FREE!)
```bash
export GOOGLE_API_KEY='AIza...'
```

### 3. Chạy
```bash
python run.py
```

---

## 📊 Output

```
📊 FINAL SUMMARY
============================================

gemini-pro:
  ✓ Pass Rate: 75.0%        # Code chạy đúng
  ✓ Algorithm Score: 4.2/5  # Thuật toán tối ưu không?
  ✓ Reasoning Score: 4.0/5  # Từng bước giải có logic không?
  ✓ Combined Score: 82.5    # Điểm tổng hợp
```

---

## 🔬 Cách hoạt động

```
┌─────────────────────────────────────────────────────────┐
│                    ORPS PIPELINE                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1️⃣ COLLECT                                              │
│     LeetCode → [GPT/Gemini] → Reasoning Steps + Code     │
│                                                          │
│  2️⃣ EXECUTE (ORM - FREE!)                                │
│     Code → [Run Tests] → Pass/Fail + Runtime             │
│     → Objective ground truth                             │
│                                                          │
│  3️⃣ JUDGE ALGORITHM (Self-Critique)                      │
│     Steps → [Gemini Flash] → Algorithm Score             │
│     → "AI chọn thuật toán có tối ưu không?"              │
│                                                          │
│  4️⃣ JUDGE STEPS (Process, guided by execution)           │
│     Steps + Execution → [Gemini Flash] → Step Scores     │
│     → "Từng bước có đúng logic không?"                   │
│                                                          │
│  5️⃣ AGGREGATE                                            │
│     Combined = 40%*Exec + 35%*Algo + 25%*Steps           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 💰 Chi phí

| Component | Cost |
|-----------|------|
| Gemini Pro (test) | **FREE** |
| Gemini Flash (judge) | **FREE** |
| Code execution | **FREE** |
| GPT-4o-mini (nếu dùng) | ~$0.50/100 problems |
| GPT-4o (nếu dùng) | ~$5/100 problems |

**Hoàn toàn FREE nếu chỉ dùng Gemini!**

---

## 📁 Project Structure

```
soccode-ai-evaluation/
├── config/
│   ├── api_config.py     # Model configs
│   └── prompts.py        # Prompt templates
│
├── src/
│   ├── collectors/       # Thu thập từ GPT/Gemini
│   ├── evaluators/
│   │   ├── execution_evaluator.py  # ORM - chạy code
│   │   ├── algorithm_judge.py      # Đánh giá thuật toán
│   │   └── step_judge.py           # Đánh giá từng step
│   └── pipeline/
│       └── main_pipeline.py        # Orchestration
│
├── data/
│   ├── leetcode_problems.json
│   └── results/
│
├── run.py                # Quick start
└── requirements.txt
```

---

## 🔧 Advanced Usage

### So sánh GPT vs Gemini
```bash
export OPENAI_API_KEY='sk-...'
export GOOGLE_API_KEY='AIza...'

python src/pipeline/main_pipeline.py \
    --problems data/leetcode_problems.json \
    --models gemini-pro gpt-4o-mini \
    --judge gemini-flash \
    --num 10
```

### Dùng với dataset của bạn từ soccode
```python
# Load từ soccode folder
with open("/path/to/soccode/ai/test-script/test_data/leetcode_problem_20.json") as f:
    problems = json.load(f)
```

---

## 📚 References

- [ORPS Paper](https://arxiv.org/abs/2412.15118) - Peking Univ + Microsoft, Dec 2024
- [Let's Verify Step by Step](https://arxiv.org/abs/2305.20050) - OpenAI PRM paper

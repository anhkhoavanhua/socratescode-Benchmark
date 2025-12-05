#!/usr/bin/env python3
"""
Streamlit Demo App - SocratesCode Benchmark Execution Flow
Visualizes the ORPS-based AI evaluation pipeline using REAL data
"""
import streamlit as st
# Force reload
import json
import os
from pathlib import Path

# Page config
st.set_page_config(
    page_title="SocratesCode Benchmark Demo",
    page_icon="🧠",
    layout="wide"
)

# ============================================
# DATA LOADING
# ============================================

@st.cache_data
def load_problems():
    """Load problems from data file"""
    path = Path("data/leetcode_problems.json")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []

@st.cache_data
def load_results():
    """Load evaluation results"""
    # Try to load results.json as it contains more data
    path = Path("data/results/results.json")
    if not path.exists():
        path = Path("data/results/final.json")

    if path.exists():
        with open(path) as f:
            data = json.load(f)
            
        # Dynamically calculate summary if not present
        if "results" in data:
            summary = {}
            for res in data["results"]:
                for model_name, mr in res.get("model_results", {}).items():
                    if model_name not in summary:
                        summary[model_name] = {
                            "problems": 0,
                            "passed": 0,
                            "total_algo_score": 0,
                            "total_step_score": 0,
                            "total_combined": 0,
                            "wins": 0
                        }
                    
                    stats = summary[model_name]
                    stats["problems"] += 1
                    
                    exec_data = mr.get("execution", {})
                    if exec_data.get("pass_rate", 0) == 1.0:
                        stats["passed"] += 1
                        
                    stats["total_algo_score"] += mr.get("algorithm_eval", {}).get("overall_score", 0)
                    stats["total_step_score"] += mr.get("reasoning_eval", {}).get("overall_score", 0)
                    stats["total_combined"] += mr.get("combined_score", 0)
            
            # Calculate averages
            final_summary = {}
            for model, stats in summary.items():
                if stats["problems"] > 0:
                    final_summary[model] = {
                        "problems": stats["problems"],
                        "avg_pass_rate": stats["passed"] / stats["problems"],
                        "avg_algo_score": stats["total_algo_score"] / stats["problems"],
                        "avg_step_score": stats["total_step_score"] / stats["problems"],
                        "avg_combined": stats["total_combined"] / stats["problems"],
                        "wins": 0 
                    }
            
            # Calculate wins
            for res in data["results"]:
                best_score = -1
                best_model = None
                for model_name, mr in res.get("model_results", {}).items():
                    score = mr.get("combined_score", 0)
                    if score > best_score:
                        best_score = score
                        best_model = model_name
                
                if best_model and best_model in final_summary:
                    final_summary[best_model]["wins"] = final_summary[best_model].get("wins", 0) + 1

            data["summary"] = final_summary
            
        return data
    return None

@st.cache_data
def load_all_result_files():
    """Load all result files for historical comparison"""
    results_dir = Path("data/results")
    all_results = {}
    if results_dir.exists():
        for f in results_dir.glob("*.json"):
            try:
                with open(f) as file:
                    all_results[f.name] = json.load(file)
            except:
                pass
    return all_results

# Load data
problems = load_problems()
results = load_results()
all_results = load_all_result_files()

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.title("🧠 SocratesCode")
    st.markdown("**ORPS-Based AI Evaluation**")
    
    st.divider()
    
    # Data status
    st.markdown("### 📊 Data Status")
    st.markdown(f"- **Problems loaded:** {len(problems)}")
    st.markdown(f"- **Results available:** {'✅' if results else '❌'}")
    st.markdown(f"- **Result files:** {len(all_results)}")
    
    st.divider()
    
    st.markdown("### Pipeline Steps")
    st.markdown("""
    1. 📚 **Load Problem**
    2. 📤 **Collect AI Response**
    3. ⚡ **Execute Code** (ORM)
    4. 🧠 **Judge Algorithm** 
    5. 📝 **Judge Steps** (PRM)
    6. 📊 **Combine Scores**
    """)
    
    st.divider()
    
    # Show weights from config if available
    if results and "config" in results:
        config = results["config"]
        st.markdown("### Score Weights (from config)")
        st.markdown(f"- Execution: **{config.get('execution_weight', 0.4):.0%}**")
        st.markdown(f"- Algorithm: **{config.get('algorithm_weight', 0.35):.0%}**")
        st.markdown(f"- Reasoning: **{config.get('step_quality_weight', 0.25):.0%}**")

# ============================================
# MAIN CONTENT
# ============================================

st.title("🚀 SocratesCode Benchmark - Execution Flow Demo")

if not results:
    st.error("⚠️ No evaluation results found. Run the benchmark first:")
    st.code("python run.py", language="bash")
    st.stop()

st.markdown(f"""
Showing results from **{results.get('timestamp', 'Unknown')}**  
Models tested: **{', '.join(list(results.get('summary', {}).keys()))}**
""")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Summary", "🔬 Problem Details", "⚔️ Model Comparison", "📈 Pipeline Flow", "⚙️ Raw Data"])

# ============================================
# TAB 1: Summary
# ============================================

with tab1:
    st.header("Evaluation Summary")
    
    if "summary" in results:
        # Model comparison table
        summary_data = []
        for model, stats in results["summary"].items():
            summary_data.append({
                "Model": model,
                "Problems": stats.get('problems', 0),
                "Pass Rate": f"{stats.get('avg_pass_rate', 0):.1%}",
                "Algorithm Score": f"{stats.get('avg_algo_score', 0):.2f}/5",
                "Reasoning Score": f"{stats.get('avg_step_score', 0):.2f}/5",
                "Combined Score": f"{stats.get('avg_combined', 0):.1f}/100",
                "Wins": stats.get('wins', 0)
            })
        
        st.table(summary_data)
        
        # Visual metrics
        st.subheader("Performance Breakdown")
        
        for model, stats in results["summary"].items():
            st.markdown(f"### {model}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Pass Rate", f"{stats.get('avg_pass_rate', 0):.1%}")
            with col2:
                st.metric("Algorithm", f"{stats.get('avg_algo_score', 0):.2f}/5")
            with col3:
                st.metric("Reasoning", f"{stats.get('avg_step_score', 0):.2f}/5")
            with col4:
                st.metric("Combined", f"{stats.get('avg_combined', 0):.1f}/100")
            
            # Progress bars
            col1, col2, col3 = st.columns(3)
            with col1:
                st.progress(stats.get('avg_pass_rate', 0), text="Execution")
            with col2:
                st.progress(stats.get('avg_algo_score', 0) / 5, text="Algorithm")
            with col3:
                st.progress(stats.get('avg_step_score', 0) / 5, text="Reasoning")

# ============================================
# TAB 2: Problem Details
# ============================================

with tab2:
    st.header("Problem-Level Results")
    
    if "results" in results:
        # Problem selector
        problem_titles = [r.get('problem_title', r.get('problem_id')) for r in results["results"]]
        selected_problem = st.selectbox("Select Problem", problem_titles)
        
        # Find selected result
        selected_result = None
        for r in results["results"]:
            if r.get('problem_title', r.get('problem_id')) == selected_problem:
                selected_result = r
                break
        
        if selected_result:
            st.subheader(f"📝 {selected_result.get('problem_title')}")
            st.markdown(f"**Problem ID:** `{selected_result.get('problem_id')}`")
            st.markdown(f"**Best Model:** `{selected_result.get('best_overall')}`")
            
            # Show problem description
            problem_data = next((p for p in problems if p.get('id') == selected_result.get('problem_id')), None)
            if problem_data:
                with st.expander("📖 Problem Description", expanded=False):
                    st.markdown(f"**Difficulty:** {problem_data.get('difficulty')}")
                    st.markdown(problem_data.get('description', ''))
                    
                    st.markdown("**Examples:**")
                    for ex in problem_data.get('examples', []):
                        st.code(f"Input: {ex.get('input')}\nOutput: {ex.get('output')}")
            
            st.divider()
            
            # Model results
            for model_name, mr in selected_result.get('model_results', {}).items():
                st.subheader(f"🤖 {model_name}")
                
                # Scores overview
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    exec_data = mr.get('execution', {})
                    pass_rate = exec_data.get('pass_rate', 0)
                    st.metric("Pass Rate", f"{pass_rate:.0%}", 
                              delta=f"{exec_data.get('passed_tests', 0)}/{exec_data.get('total_tests', 0)} tests")
                with col2:
                    algo_data = mr.get('algorithm_eval', {})
                    st.metric("Algorithm", f"{algo_data.get('overall_score', 0):.1f}/5")
                with col3:
                    step_data = mr.get('reasoning_eval', {})
                    st.metric("Reasoning", f"{step_data.get('overall_score', 0):.1f}/5")
                with col4:
                    st.metric("Combined", f"{mr.get('combined_score', 0):.1f}/100")
                
                # Detailed breakdowns
                col1, col2 = st.columns(2)
                
                with col1:
                    # Execution details
                    with st.expander("⚡ Execution Details", expanded=True):
                        exec_data = mr.get('execution', {})
                        
                        if exec_data.get('has_syntax_error'):
                            st.error(f"❌ Syntax Error: {exec_data.get('syntax_error_msg')}")
                        elif exec_data.get('has_runtime_error'):
                            st.warning("⚠️ Runtime errors occurred")
                        else:
                            st.success("✅ No errors")
                        
                        st.markdown(f"**Runtime:** {exec_data.get('total_runtime_ms', 0):.2f}ms")
                        
                        # Test results
                        st.markdown("**Test Results:**")
                        for test in exec_data.get('test_results', []):
                            status = "✅" if test.get('passed') else "❌"
                            st.markdown(f"{status} **Test {test.get('test_id')}**")
                            st.code(f"Input: {test.get('input')}\nExpected: {test.get('expected')}\nActual: {test.get('actual')}")
                            if test.get('error'):
                                st.error(test.get('error'))
                
                with col2:
                    # Algorithm evaluation
                    with st.expander("🧠 Algorithm Evaluation", expanded=True):
                        algo_data = mr.get('algorithm_eval', {})
                        
                        st.progress(algo_data.get('optimality_score', 0) / 5, 
                                   text=f"Optimality: {algo_data.get('optimality_score', 0)}/5")
                        st.progress(algo_data.get('appropriateness_score', 0) / 5,
                                   text=f"Appropriateness: {algo_data.get('appropriateness_score', 0)}/5")
                        st.progress(algo_data.get('justification_score', 0) / 5,
                                   text=f"Justification: {algo_data.get('justification_score', 0)}/5")
                        
                        if algo_data.get('feedback'):
                            st.info(f"**Feedback:** {algo_data.get('feedback')}")
                    
                    # Step evaluation
                    with st.expander("📝 Reasoning Evaluation", expanded=True):
                        step_data = mr.get('reasoning_eval', {})
                        
                        # Averages
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Avg Correctness", f"{step_data.get('avg_correctness', 0):.2f}/5")
                            st.metric("Avg Clarity", f"{step_data.get('avg_clarity', 0):.2f}/5")
                        with col_b:
                            st.metric("Avg Completeness", f"{step_data.get('avg_completeness', 0):.2f}/5")
                            st.metric("Avg Flow", f"{step_data.get('avg_logical_flow', 0):.2f}/5")
                        
                        # Per-step scores
                        st.markdown("**Reasoning Steps Detail:**")
                        for step_eval in step_data.get('step_evaluations', []):
                            step_num = step_eval.get('step_number')
                            score = step_eval.get('step_score', 0)
                            
                            with st.expander(f"Step {step_num} (Score: {score:.2f}/5)"):
                                st.progress(score/5)
                                
                                sc1, sc2, sc3, sc4 = st.columns(4)
                                with sc1: st.metric("Correctness", f"{step_eval.get('correctness', 0)}/5")
                                with sc2: st.metric("Clarity", f"{step_eval.get('clarity', 0)}/5")
                                with sc3: st.metric("Completeness", f"{step_eval.get('completeness', 0)}/5")
                                with sc4: st.metric("Flow", f"{step_eval.get('logical_flow', 0)}/5")
                                
                                if step_eval.get('issues') and step_eval.get('issues') != "None":
                                    st.error(f"**Issues:** {step_eval.get('issues')}")
                                else:
                                    st.success("No issues found")
                
                st.divider()

# ============================================
# TAB 3: Model Comparison
# ============================================

with tab3:
    st.header("⚔️ Head-to-Head Comparison")
    
    if "results" in results:
        # Problem selector
        problem_titles = [r.get('problem_title', r.get('problem_id')) for r in results["results"]]
        selected_problem_cmp = st.selectbox("Select Problem for Comparison", problem_titles, key="cmp_prob_select")
        
        # Find selected result
        cmp_result = None
        for r in results["results"]:
            if r.get('problem_title', r.get('problem_id')) == selected_problem_cmp:
                cmp_result = r
                break
        
        if cmp_result:
            available_models = list(cmp_result.get('model_results', {}).keys())
            
            if len(available_models) < 2:
                st.warning("Need at least 2 models to compare.")
                if len(available_models) == 1:
                     st.info(f"Only data for **{available_models[0]}** is available.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    model_a = st.selectbox("Model A", available_models, index=0)
                with col2:
                    model_b = st.selectbox("Model B", available_models, index=1 if len(available_models) > 1 else 0)
                
                if model_a and model_b:
                    res_a = cmp_result['model_results'][model_a]
                    res_b = cmp_result['model_results'][model_b]
                    
                    st.divider()
                    
                    # Score Comparison
                    st.subheader("Score Comparison")
                    
                    metrics = [
                        ("Pass Rate", f"{res_a['execution']['pass_rate']:.1%}", f"{res_b['execution']['pass_rate']:.1%}"),
                        ("Algorithm", f"{res_a['algorithm_eval']['overall_score']:.1f}/5", f"{res_b['algorithm_eval']['overall_score']:.1f}/5"),
                        ("Reasoning", f"{res_a['reasoning_eval']['overall_score']:.1f}/5", f"{res_b['reasoning_eval']['overall_score']:.1f}/5"),
                        ("Combined", f"{res_a['combined_score']:.1f}", f"{res_b['combined_score']:.1f}")
                    ]
                    
                    # Display metrics side-by-side
                    c1, c2, c3 = st.columns([2, 2, 2])
                    with c1: st.markdown(f"**Metric**")
                    with c2: st.markdown(f"**{model_a}**")
                    with c3: st.markdown(f"**{model_b}**")
                    
                    for name, val_a, val_b in metrics:
                        c1, c2, c3 = st.columns([2, 2, 2])
                        with c1: st.markdown(name)
                        with c2: st.markdown(val_a)
                        with c3: st.markdown(val_b)
                    
                    st.divider()
                    
                    # Detailed breakdown
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        st.markdown(f"### {model_a} Details")
                        with st.expander("Algorithm Feedback"):
                            st.write(res_a['algorithm_eval'].get('feedback', 'No feedback'))
                        with st.expander("Reasoning Issues"):
                            issues = []
                            for step in res_a['reasoning_eval']['step_evaluations']:
                                if step.get('issues') and step.get('issues') != "None":
                                    issues.append(f"**Step {step['step_number']}**: {step['issues']}")
                            if issues:
                                for issue in issues:
                                    st.markdown(issue)
                            else:
                                st.success("No reasoning issues found.")
                                
                    with c2:
                        st.markdown(f"### {model_b} Details")
                        with st.expander("Algorithm Feedback"):
                            st.write(res_b['algorithm_eval'].get('feedback', 'No feedback'))
                        with st.expander("Reasoning Issues"):
                            issues = []
                            for step in res_b['reasoning_eval']['step_evaluations']:
                                if step.get('issues') and step.get('issues') != "None":
                                    issues.append(f"**Step {step['step_number']}**: {step['issues']}")
                            if issues:
                                for issue in issues:
                                    st.markdown(issue)
                            else:
                                st.success("No reasoning issues found.")

# ============================================
# TAB 3: Pipeline Flow
# ============================================

with tab4:
    st.header("Evaluation Pipeline Architecture")
    
    # Flow diagram
    st.markdown("""
    ```
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   PROBLEM   │───▶│  COLLECTOR  │───▶│  EXECUTOR   │───▶│   JUDGES    │───▶│   SCORES    │
    │             │    │             │    │             │    │             │    │             │
    │ • Title     │    │ • API Call  │    │ • Syntax    │    │ • Algorithm │    │ • Combined  │
    │ • Tests     │    │ • Parse     │    │ • Run Tests │    │ • Steps     │    │ • Summary   │
    │ • Examples  │    │ • Extract   │    │ • Timeout   │    │ • LLM-Judge │    │ • Ranking   │
    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
    ```
    """)
    
    st.divider()
    
    # Component details
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("🔧 ExecutionEvaluator (ORM)", expanded=True):
            st.markdown("""
            **Location:** `src/evaluators/execution_evaluator.py`
            
            **Purpose:** Objective code verification (FREE - runs locally)
            
            **Process:**
            1. `_check_syntax()` - Validates Python syntax via `compile()`
            2. `_create_harness()` - Wraps code with test input
            3. `subprocess.run()` - Executes with timeout
            4. `_normalize()` - Compares output vs expected
            
            **Output:** `ExecutionResult`
            - `pass_rate`: 0.0 - 1.0
            - `test_results`: Per-test details
            - `has_syntax_error`, `has_runtime_error`
            """)
        
        with st.expander("📤 Collectors"):
            st.markdown("""
            **Location:** `src/collectors/`
            
            **Types:**
            - `GeminiCollector` - Google Gemini API
            - `GPTCollector` - OpenAI API
            
            **Output:** `AIResponse`
            - `reasoning_steps`: List of steps
            - `code`: Extracted solution
            - `time_complexity`, `space_complexity`
            """)
    
    with col2:
        with st.expander("🧠 AlgorithmJudge", expanded=True):
            st.markdown("""
            **Location:** `src/evaluators/algorithm_judge.py`
            
            **Criteria (0-5 each):**
            - **Optimality**: Is it the best approach?
            - **Appropriateness**: Right for this problem?
            - **Justification**: Well explained?
            
            **Uses:** LLM-as-Judge (Gemini Flash - FREE)
            
            **Reference:** `OPTIMAL_SOLUTIONS` dict for comparison
            """)
        
        with st.expander("📝 StepQualityJudge (PRM)"):
            st.markdown("""
            **Location:** `src/evaluators/step_judge.py`
            
            **Per-step criteria (0-5):**
            - **Correctness**: Is the reasoning accurate?
            - **Clarity**: Is it clearly explained?
            - **Completeness**: Are details covered?
            - **Logical Flow**: Does it connect well?
            
            **Key:** Guided by execution result!
            """)
    
    st.divider()
    
    # Score combination formula
    st.subheader("📊 Score Combination")
    
    if results and "config" in results:
        config = results["config"]
        exec_w = config.get('execution_weight', 0.4)
        algo_w = config.get('algorithm_weight', 0.35)
        step_w = config.get('step_quality_weight', 0.25)
        
        st.latex(rf"""
        \text{{Combined}} = {exec_w:.0%} \times \text{{Execution}} + {algo_w:.0%} \times \text{{Algorithm}} + {step_w:.0%} \times \text{{Reasoning}}
        """)
        
        st.markdown(f"""
        | Component | Weight | Scale | Contribution |
        |-----------|--------|-------|--------------|
        | Execution | {exec_w:.0%} | 0-100 (pass_rate × 100) | 0-{exec_w*100:.0f} |
        | Algorithm | {algo_w:.0%} | 0-100 (score × 20) | 0-{algo_w*100:.0f} |
        | Reasoning | {step_w:.0%} | 0-100 (score × 20) | 0-{step_w*100:.0f} |
        | **Total** | **100%** | | **0-100** |
        """)

# ============================================
# TAB 4: Raw Data
# ============================================

with tab5:
    st.header("Raw Data Explorer")
    
    data_choice = st.radio("Select data to view:", 
                          ["Full Results", "Config", "Problems", "All Result Files"])
    
    if data_choice == "Full Results":
        st.json(results)
    elif data_choice == "Config":
        st.json(results.get("config", {}))
    elif data_choice == "Problems":
        st.json(problems)
    elif data_choice == "All Result Files":
        file_choice = st.selectbox("Select file:", list(all_results.keys()))
        if file_choice:
            st.json(all_results[file_choice])

# ============================================
# FOOTER
# ============================================

st.divider()
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>SocratesCode Benchmark - ORPS-Based AI Reasoning Evaluation</p>
    <p>Based on APPS, MBPP, HumanEval, BigCodeBench, and LiveCodeBench methodologies</p>
</div>
""", unsafe_allow_html=True)

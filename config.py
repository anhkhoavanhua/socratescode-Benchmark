"""
SocratesCode AI Evaluator - Configuration
Based on scientific benchmarks: APPS, MBPP, BigCodeBench, LiveCodeBench

Research basis:
- APPS (UC Berkeley, 2021): pass@k metric, 21.2 test cases avg
- MBPP (Google Research, 2021): entry-level Python problems  
- BigCodeBench (2024): realistic efficiency metrics
- EvoCodeBench (NeurIPS 2024): Domain-Specific Improvement
"""

import os
from dataclasses import dataclass

@dataclass
class Config:
    # API Keys (set via environment or directly)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Models
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GPT_MODEL: str = "gpt-4o-mini"
    
    # Execution limits (from BigCodeBench methodology)
    CODE_TIMEOUT: int = 10  # seconds
    MAX_MEMORY_MB: int = 256
    
    # Efficiency thresholds (relative to optimal)
    RUNTIME_EXCELLENT: float = 1.2   # Within 20%
    RUNTIME_GOOD: float = 2.0        # Within 2x
    MEMORY_EXCELLENT: float = 1.2
    MEMORY_GOOD: float = 2.0
    
    # Validation sampling (from ITS research)
    HUMAN_VALIDATION_RATE: float = 0.10
    
    # Paths
    DATA_DIR: str = "data"
    RESULTS_DIR: str = "results"

config = Config()

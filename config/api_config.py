# config/api_config.py
"""
API configuration cho AI Reasoning Evaluation System
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ModelConfig:
    """Configuration cho một model"""
    name: str
    api_type: str  # 'openai' or 'google'
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096

# ============================================
# SUPPORTED MODELS
# ============================================

MODELS = {
    # OpenAI Models
    "gpt-4": ModelConfig("GPT-4", "openai", "gpt-4-turbo-preview"),
    "gpt-4-turbo": ModelConfig("GPT-4 Turbo", "openai", "gpt-4-turbo"),
    "gpt-4o": ModelConfig("GPT-4o", "openai", "gpt-4o"),
    "gpt-4o-mini": ModelConfig("GPT-4o Mini", "openai", "gpt-4o-mini"),
    
    # Google Models (FREE tier!)
    "gemini-pro": ModelConfig("Gemini 1.5 Pro", "google", "gemini-1.5-pro"),
    "gemini-flash": ModelConfig("Gemini 1.5 Flash", "google", "gemini-2.5-flash-lite"),
    "gemini-flash-2": ModelConfig("Gemini 2.0 Flash", "google", "gemini-2.0-flash-exp"),
    "gemini-2.5-flash-lite": ModelConfig("Gemini 2.5 Flash Lite", "google", "gemini-2.5-flash-lite"),
}

# Defaults
DEFAULT_TEST_MODELS = ["gemini-pro"]  # Start with FREE model
DEFAULT_JUDGE_MODEL = "gemini-flash"   # FREE for judging

# ============================================
# API KEYS
# ============================================

def get_api_keys():
    """Load API keys from environment"""
    return {
        "openai": os.environ.get("OPENAI_API_KEY"),
        "google": os.environ.get("GOOGLE_API_KEY")
    }

def validate_api_keys(models: List[str] = None):
    """Validate required API keys"""
    keys = get_api_keys()
    models = models or DEFAULT_TEST_MODELS
    
    need_openai = any(MODELS[m].api_type == "openai" for m in models if m in MODELS)
    need_google = any(MODELS[m].api_type == "google" for m in models if m in MODELS)
    
    missing = []
    if need_openai and not keys["openai"]:
        missing.append("OPENAI_API_KEY")
    if need_google and not keys["google"]:
        missing.append("GOOGLE_API_KEY")
    
    if missing:
        print(f"⚠️  Missing: {', '.join(missing)}")
        for key in missing:
            print(f"   export {key}='your-key'")
        return False
    
    print("✅ API keys OK")
    return True

# ============================================
# EVALUATION CONFIG
# ============================================

@dataclass
class EvaluationConfig:
    """Settings for evaluation pipeline"""
    test_models: List[str] = field(default_factory=lambda: ["gemini-pro"])
    judge_model: str = "gemini-flash"
    num_problems: int = 10
    
    # Weights for combined score
    execution_weight: float = 0.4
    algorithm_weight: float = 0.35
    step_quality_weight: float = 0.25
    
    # Execution
    code_timeout_seconds: int = 10
    
    # Output
    output_dir: str = "data/results"
    save_raw_responses: bool = True

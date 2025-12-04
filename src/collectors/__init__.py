# src/collectors/__init__.py
from .base_collector import BaseCollector, AIResponse, ReasoningStep
from .gpt_collector import GPTCollector
from .gemini_collector import GeminiCollector, GeminiJudge

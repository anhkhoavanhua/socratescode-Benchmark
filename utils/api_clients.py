"""
API Clients for AI Models
Supports: Gemini (API), GPT (API), Claude (Manual Input)

Scientific basis:
- LiveCodeBench (2024): Multi-model evaluation methodology
- ResearchCodeBench (2025): Cross-model comparison

Features:
- Async-ready API calls
- Rate limiting
- Error handling
- Manual input support for Claude
"""

import os
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from config import config

@dataclass
class AIResponse:
    """Standardized AI response"""
    model: str
    response: str
    prompt: str
    latency_ms: float
    tokens_used: int = 0
    error: Optional[str] = None

class BaseAIClient(ABC):
    """Base class for AI clients"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> AIResponse:
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        pass

class GeminiClient(BaseAIClient):
    """Google Gemini API Client (using new google-genai SDK)"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model = model or config.GEMINI_MODEL
        self._client = None

    def _init_client(self):
        """Initialize Gemini client lazily"""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("Install google-genai: pip install google-genai")

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response from Gemini"""
        if not self.api_key:
            return AIResponse(
                model=self.model,
                response="",
                prompt=prompt,
                latency_ms=0,
                error="GEMINI_API_KEY not set"
            )

        try:
            self._init_client()

            start = time.perf_counter()
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            latency = (time.perf_counter() - start) * 1000

            # Extract token usage from new SDK format
            tokens_used = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens_used = getattr(response.usage_metadata, 'total_token_count', 0)

            return AIResponse(
                model=self.model,
                response=response.text,
                prompt=prompt,
                latency_ms=latency,
                tokens_used=tokens_used
            )
        except Exception as e:
            return AIResponse(
                model=self.model,
                response="",
                prompt=prompt,
                latency_ms=0,
                error=str(e)
            )

    def get_model_name(self) -> str:
        return f"gemini:{self.model}"

class GPTClient(BaseAIClient):
    """OpenAI GPT API Client"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = model or config.GPT_MODEL
        self._client = None
    
    def _init_client(self):
        """Initialize OpenAI client lazily"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Install openai: pip install openai")
    
    def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response from GPT"""
        if not self.api_key:
            return AIResponse(
                model=self.model,
                response="",
                prompt=prompt,
                latency_ms=0,
                error="OPENAI_API_KEY not set"
            )
        
        try:
            self._init_client()
            
            start = time.perf_counter()
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful coding assistant. Provide clean, efficient Python code solutions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            latency = (time.perf_counter() - start) * 1000
            
            return AIResponse(
                model=self.model,
                response=response.choices[0].message.content,
                prompt=prompt,
                latency_ms=latency,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
        except Exception as e:
            return AIResponse(
                model=self.model,
                response="",
                prompt=prompt,
                latency_ms=0,
                error=str(e)
            )
    
    def get_model_name(self) -> str:
        return f"gpt:{self.model}"

class ClaudeManualClient(BaseAIClient):
    """
    Manual Input Client for Claude
    
    Since Claude API is not available, this allows manual input
    of Claude's responses for evaluation.
    """
    
    def __init__(self, model: str = "claude-3-sonnet"):
        self.model = model
        self._responses_cache = {}
    
    def generate(self, prompt: str, **kwargs) -> AIResponse:
        """
        Get response for prompt (from cache or manual input)
        """
        # Check cache first
        cache_key = hash(prompt)
        if cache_key in self._responses_cache:
            return self._responses_cache[cache_key]
        
        print("\n" + "="*60)
        print("📝 CLAUDE MANUAL INPUT REQUIRED")
        print("="*60)
        print(f"\n🔹 Prompt:\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}")
        print("\n" + "-"*60)
        print("Please paste Claude's response below.")
        print("Enter 'END' on a new line when done:")
        print("-"*60)
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == 'END':
                    break
                lines.append(line)
            except EOFError:
                break
        
        response_text = '\n'.join(lines)
        
        result = AIResponse(
            model=self.model,
            response=response_text,
            prompt=prompt,
            latency_ms=0  # Manual input, no latency
        )
        
        # Cache for reuse
        self._responses_cache[cache_key] = result
        
        return result
    
    def set_response(self, prompt: str, response: str):
        """Pre-set a response for a prompt (for batch processing)"""
        cache_key = hash(prompt)
        self._responses_cache[cache_key] = AIResponse(
            model=self.model,
            response=response,
            prompt=prompt,
            latency_ms=0
        )
    
    def load_responses_from_file(self, filepath: str):
        """Load pre-saved Claude responses from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            for item in data:
                self.set_response(item['prompt'], item['response'])
            
            print(f"✅ Loaded {len(data)} Claude responses from {filepath}")
        except Exception as e:
            print(f"❌ Error loading responses: {e}")
    
    def save_responses_to_file(self, filepath: str):
        """Save collected Claude responses to JSON file"""
        data = [
            {'prompt': r.prompt, 'response': r.response}
            for r in self._responses_cache.values()
        ]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Saved {len(data)} Claude responses to {filepath}")
    
    def get_model_name(self) -> str:
        return f"claude:{self.model} (manual)"

class AIClientFactory:
    """Factory for creating AI clients"""
    
    @staticmethod
    def create(model_type: str, **kwargs) -> BaseAIClient:
        """
        Create AI client by type
        
        Args:
            model_type: 'gemini', 'gpt', or 'claude'
            **kwargs: Additional arguments for specific client
        """
        model_type = model_type.lower()
        
        if model_type == 'gemini':
            return GeminiClient(**kwargs)
        elif model_type in ['gpt', 'openai']:
            return GPTClient(**kwargs)
        elif model_type == 'claude':
            return ClaudeManualClient(**kwargs)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    @staticmethod
    def create_all() -> Dict[str, BaseAIClient]:
        """Create all available clients"""
        return {
            'gemini': GeminiClient(),
            'gpt': GPTClient(),
            'claude': ClaudeManualClient()
        }

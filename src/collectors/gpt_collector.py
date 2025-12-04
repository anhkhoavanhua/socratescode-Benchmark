# src/collectors/gpt_collector.py
"""
OpenAI GPT response collector
"""
from typing import Dict, Any
from .base_collector import BaseCollector

class GPTCollector(BaseCollector):
    """Collector for OpenAI GPT models"""
    
    def _init_client(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
    
    def _call_api(self, prompt: str) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model_config.model_id,
            messages=[
                {"role": "system", "content": "You are an expert programmer. Follow the exact format requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.model_config.temperature,
            max_tokens=self.model_config.max_tokens
        )
        return {
            "content": response.choices[0].message.content,
            "tokens": {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }

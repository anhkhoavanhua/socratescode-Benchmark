# src/collectors/gemini_collector.py
"""
Google Gemini response collector + Judge
"""
from typing import Dict, Any
import json
import re
from google import genai
from google.genai import types
from .base_collector import BaseCollector

class GeminiCollector(BaseCollector):
    """Collector for Google Gemini models"""
    
    def _init_client(self):
        self.client = genai.Client(api_key=self.api_key)
    
    def _call_api(self, prompt: str) -> Dict[str, Any]:
        config = types.GenerateContentConfig(
            temperature=self.model_config.temperature,
            max_output_tokens=self.model_config.max_tokens,
            system_instruction="You are an expert programmer. Follow the exact format requested."
        )
        
        response = self.client.models.generate_content(
            model=self.model_config.model_id,
            contents=prompt,
            config=config
        )
        
        tokens = {}
        if response.usage_metadata:
            tokens = {
                "input": response.usage_metadata.prompt_token_count,
                "output": response.usage_metadata.candidates_token_count,
            }
        return {"content": response.text, "tokens": tokens}


class GeminiJudge:
    """
    LLM-as-Judge using Gemini Flash (FREE!)
    This is the "Self-Critique" component of ORPS
    """
    
    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash-lite"):
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id
        self.config = types.GenerateContentConfig(
            temperature=0.3,  # Lower for consistent judgments
            max_output_tokens=2048,
            system_instruction="You are an expert evaluator. Respond with valid JSON only, no markdown."
        )
    
    def judge(self, prompt: str) -> Dict[str, Any]:
        """Make a judgment call and parse JSON response"""
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=self.config
        )
        content = response.text
        
        # Extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            return {"error": f"JSON parse failed: {e}", "raw": response.text}
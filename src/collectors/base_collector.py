# src/collectors/base_collector.py
"""
Base class cho response collectors
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
import time

@dataclass
class ReasoningStep:
    """A single reasoning step"""
    step_number: int
    title: str
    content: str
    
    def to_dict(self):
        return {"step_number": self.step_number, "title": self.title, "content": self.content}

@dataclass
class AIResponse:
    """Structured response from AI model"""
    model_name: str
    problem_id: str
    raw_response: str
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    code: str = ""
    algorithm_description: str = ""
    time_complexity: str = "Unknown"
    space_complexity: str = "Unknown"
    response_time_ms: float = 0
    tokens_used: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "model_name": self.model_name,
            "problem_id": self.problem_id,
            "raw_response": self.raw_response,
            "reasoning_steps": [s.to_dict() for s in self.reasoning_steps],
            "code": self.code,
            "algorithm_description": self.algorithm_description,
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
            "response_time_ms": self.response_time_ms,
            "tokens_used": self.tokens_used
        }

class BaseCollector(ABC):
    """Abstract base for AI response collectors"""
    
    def __init__(self, model_config, api_key: str):
        self.model_config = model_config
        self.api_key = api_key
        self.client = None
        self._init_client()
    
    @abstractmethod
    def _init_client(self):
        pass
    
    @abstractmethod
    def _call_api(self, prompt: str) -> Dict[str, Any]:
        pass
    
    def collect(self, problem: Dict[str, Any], prompt_template: str) -> AIResponse:
        """Collect response for a problem"""
        prompt = prompt_template.format(problem_description=self._format_problem(problem))
        
        start = time.time()
        result = self._call_api(prompt)
        elapsed = (time.time() - start) * 1000
        
        parsed = self._parse_response(result["content"])
        
        return AIResponse(
            model_name=self.model_config.name,
            problem_id=problem.get("id", problem.get("title", "unknown")),
            raw_response=result["content"],
            reasoning_steps=parsed["steps"],
            code=parsed["code"],
            algorithm_description=parsed["algorithm"],
            time_complexity=parsed["time_complexity"],
            space_complexity=parsed["space_complexity"],
            response_time_ms=elapsed,
            tokens_used=result.get("tokens", {})
        )
    
    def _format_problem(self, problem: Dict) -> str:
        """Format problem for prompt"""
        parts = []
        if "title" in problem:
            parts.append(f"**{problem['title']}**\n")
        if "description" in problem:
            parts.append(problem["description"])
        if "examples" in problem:
            parts.append("\n**Examples:**")
            for i, ex in enumerate(problem["examples"], 1):
                parts.append(f"\nExample {i}:")
                parts.append(f"  Input: {ex.get('input', 'N/A')}")
                parts.append(f"  Output: {ex.get('output', 'N/A')}")
        if "constraints" in problem:
            parts.append("\n**Constraints:**")
            for c in problem["constraints"]:
                parts.append(f"  - {c}")
        return "\n".join(parts)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format"""
        result = {
            "steps": [],
            "code": "",
            "algorithm": "",
            "time_complexity": "Unknown",
            "space_complexity": "Unknown"
        }
        
        # Extract steps
        step_pattern = r"### STEP (\d+): ([^\n]+)\n(.*?)(?=### STEP|\Z)"
        for match in re.finditer(step_pattern, response, re.DOTALL):
            step_num, title, content = match.groups()
            result["steps"].append(ReasoningStep(
                step_number=int(step_num),
                title=title.strip(),
                content=content.strip()
            ))
            if "Algorithm" in title:
                result["algorithm"] = content.strip()
            if "Complexity" in title:
                time_m = re.search(r"time complexity:\s*O\([^)]+\)", content, re.I)
                space_m = re.search(r"space complexity:\s*O\([^)]+\)", content, re.I)
                if time_m: result["time_complexity"] = time_m.group()
                if space_m: result["space_complexity"] = space_m.group()
        
        # Extract code
        code_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
        if code_match:
            result["code"] = code_match.group(1).strip()
        else:
            code_match = re.search(r"```\n(.*?)```", response, re.DOTALL)
            if code_match:
                result["code"] = code_match.group(1).strip()
        
        return result
    
    def collect_batch(self, problems: List[Dict], prompt_template: str, 
                      delay: float = 1.0) -> List[AIResponse]:
        """Collect responses for multiple problems"""
        responses = []
        for i, problem in enumerate(problems):
            print(f"  [{self.model_config.name}] {i+1}/{len(problems)}: {problem.get('title', 'Unknown')}")
            try:
                responses.append(self.collect(problem, prompt_template))
            except Exception as e:
                print(f"    ❌ Error: {e}")
                responses.append(AIResponse(
                    model_name=self.model_config.name,
                    problem_id=problem.get("id", "unknown"),
                    raw_response=f"ERROR: {e}"
                ))
            if i < len(problems) - 1:
                time.sleep(delay)
        return responses

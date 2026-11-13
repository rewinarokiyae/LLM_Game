"""
LLM Provider Abstraction.
Defines interface for language model providers to allow pluggable backends:
- Ollama
- Offline Deterministic Engine
- Future Cloud Providers (Gemini, Anthropic, OpenAI)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class LLMProvider(ABC):
    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM service is currently reachable."""
        pass


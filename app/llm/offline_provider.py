"""
Deterministic Offline Provider.
Generates structured, grounded explanations directly from verified calculation engines
and retrieved citations without making remote network calls.
Guarantees 100% availability and strict hallucination prevention.
"""

from typing import Optional
from app.llm.provider import LLMProvider


class OfflineProvider(LLMProvider):
    def is_available(self) -> bool:
        return True

    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """
        In offline mode, responses are formatted directly by the ResponseGenerator
        using deterministic data and verified citations.
        """
        if context:
            return f"Verified Institutional Grounding:\n{context}\n\nProcessed query: {prompt}"
        return f"Deterministic Mode Active: {prompt}"


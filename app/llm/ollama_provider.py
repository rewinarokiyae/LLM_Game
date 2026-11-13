"""
Ollama LLM Provider.
Integrates with locally hosted Ollama instances via REST API.
Handles connection checks, timeouts, and JSON error handling gracefully.
"""

from typing import Optional
import json
import urllib.request
import urllib.error
from app.config.settings import settings
from app.config.logging_config import logger
from app.llm.provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = settings.LLM_TIMEOUT_SECONDS
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Fast connectivity check using socket connection before HTTP."""
        import socket
        try:
            # Parse host and port from base_url
            url_part = self.base_url.replace("http://", "").replace("https://", "").split("/")[0]
            host, port_str = url_part.split(":") if ":" in url_part else (url_part, 11434)
            port = int(port_str)
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except Exception:
            return False

    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        url = f"{self.base_url}/api/generate"
        full_prompt = prompt
        if context:
            full_prompt = f"Grounded Context:\n{context}\n\nUser Question:\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "system": system_prompt or "You are an accurate, grounded university workload intelligence assistant. Answer solely based on the provided context.",
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama call failed ({e}). Returning fallback response.")
            raise ConnectionError(f"Ollama error: {e}")

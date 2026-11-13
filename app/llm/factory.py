"""
LLM Provider Factory.
Returns active LLM provider based on settings and connectivity checks.
"""

from app.config.settings import settings
from app.config.logging_config import logger
from app.llm.provider import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.offline_provider import OfflineProvider


class LLMFactory:
    _instance: LLMProvider = None

    @classmethod
    def get_provider(cls) -> LLMProvider:
        if cls._instance is not None:
            return cls._instance

        provider_type = settings.LLM_PROVIDER.lower()

        if provider_type == "ollama":
            ollama = OllamaProvider()
            if ollama.is_available():
                logger.info(f"Ollama connected successfully at {settings.OLLAMA_BASE_URL} (Model: {settings.OLLAMA_MODEL})")
                cls._instance = ollama
                return cls._instance
            else:
                logger.info("Ollama is not running or unreachable. Falling back to Deterministic Offline Mode.")

        # Default to Offline Provider
        cls._instance = OfflineProvider()
        return cls._instance

    @classmethod
    def get_status(cls) -> str:
        provider = cls.get_provider()
        if isinstance(provider, OllamaProvider) and provider.is_available():
            return f"Ollama Connected ({settings.OLLAMA_MODEL})"
        return "Deterministic Offline Mode (LLM Not Connected)"


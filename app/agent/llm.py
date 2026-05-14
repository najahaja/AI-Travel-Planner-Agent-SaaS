"""LLM factory — Groq only, singleton cached instance."""
# pyrefly: ignore [missing-import]
from langchain_core.language_models import BaseChatModel
from app.core.config import settings
# pyrefly: ignore [missing-import]
from loguru import logger

_llm_instance: BaseChatModel | None = None


def get_llm() -> BaseChatModel:
    """Return a cached Groq LLM instance (singleton — created once at startup)."""
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    if not settings.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set in .env — "
            "get a free key at https://console.groq.com"
        )
    # pyrefly: ignore [missing-import-error]
    from langchain_groq import ChatGroq
    logger.info(f"[LLM] Initializing Groq model: {settings.LLM_MODEL}")
    # pyrefly: ignore [missing-import-error]
    _llm_instance = ChatGroq(
        model=settings.LLM_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.7,
        max_tokens=4096,
        request_timeout=60,
        streaming=False,
    )
    logger.info("[LLM] Groq client ready.")
    return _llm_instance


def reset_llm():
    """Reset the singleton (useful after config changes or in tests)."""
    global _llm_instance
    _llm_instance = None

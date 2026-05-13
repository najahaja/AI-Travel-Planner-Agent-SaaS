"""LLM factory — Groq provider with singleton caching and timeout."""
from langchain_core.language_models import BaseChatModel
from app.core.config import settings
from loguru import logger

_llm_instance: BaseChatModel | None = None


def get_llm() -> BaseChatModel:
    """Return a cached Groq LLM instance (singleton to avoid recreating on every call)."""
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in environment")
        from langchain_groq import ChatGroq
        logger.info(f"[LLM] Initializing Groq: {settings.LLM_MODEL}")
        _llm_instance = ChatGroq(
            model=settings.LLM_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.7,
            max_tokens=4096,
            # Groq is very fast; set a generous timeout to avoid hanging
            request_timeout=60,
            streaming=False,
        )
        return _llm_instance

    elif provider == "google":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in environment")
        from langchain_google_genai import ChatGoogleGenerativeAI
        logger.info(f"[LLM] Initializing Google Gemini: {settings.LLM_MODEL}")
        _llm_instance = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
            max_output_tokens=4096,
        )
        return _llm_instance

    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in environment")
        from langchain_openai import ChatOpenAI
        logger.info(f"[LLM] Initializing OpenAI: {settings.LLM_MODEL}")
        _llm_instance = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            max_tokens=4096,
            request_timeout=60,
        )
        return _llm_instance

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            "Valid options: 'groq', 'google', 'openai'"
        )


def reset_llm():
    """Reset the LLM singleton (useful for testing or config changes)."""
    global _llm_instance
    _llm_instance = None

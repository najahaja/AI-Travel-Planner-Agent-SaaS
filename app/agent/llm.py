"""LLM factory — supports Google Gemini and OpenAI."""
from langchain_core.language_models import BaseChatModel
from app.core.config import settings
from loguru import logger


def get_llm() -> BaseChatModel:
    """Return configured LLM based on settings."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "google":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in environment")
        from langchain_google_genai import ChatGoogleGenerativeAI
        logger.debug(f"Using Google Gemini: {settings.LLM_MODEL}")
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
            max_output_tokens=4096,
            convert_system_message_to_human=True,
        )

    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in environment")
        from langchain_openai import ChatOpenAI
        logger.debug(f"Using OpenAI: {settings.LLM_MODEL}")
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            max_tokens=4096,
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Choose 'google' or 'openai'.")

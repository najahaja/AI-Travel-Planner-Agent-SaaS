from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Travel Planner Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-must-be-32-chars-minimum"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./travel_planner.db"

    # ── LLM — Groq only ──────────────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = None
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # ── RAG ──────────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # ── External APIs ─────────────────────────────────────────────────────────
    OPENWEATHER_API_KEY: Optional[str] = None
    UNSPLASH_ACCESS_KEY: Optional[str] = None
    EXCHANGE_RATE_API_KEY: Optional[str] = None

    # ── Super Admin Seed ─────────────────────────────────────────────────────
    SUPER_ADMIN_EMAIL: str = "superadmin@travelplanner.com"
    SUPER_ADMIN_PASSWORD: str = "SuperAdmin@2026!"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_CHAT: str = "20/minute"
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

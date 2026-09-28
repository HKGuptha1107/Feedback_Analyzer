"""Application configuration module.
Loads environment variables safely with robust fallback defaults for local development.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in project root or current working dir
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)


class Settings:
    """Strongly typed application configuration settings."""

    # Project metadata
    PROJECT_NAME: str = "Feedback Analyzer"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

    # Database: defaults to SQLite for zero-friction local development,
    # or PostgreSQL when configured via Docker or environment.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./feedback_intelligence.db"
    )

    # Groq AI settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")

    # Hindsight LLM & Memory settings
    HINDSIGHT_API_LLM_PROVIDER: str = os.getenv("HINDSIGHT_API_LLM_PROVIDER", "groq")
    HINDSIGHT_API_LLM_API_KEY: str = os.getenv("HINDSIGHT_API_LLM_API_KEY", os.getenv("GROQ_API_KEY", ""))
    HINDSIGHT_URL: str = os.getenv("HINDSIGHT_URL", "https://api.hindsight.vectorize.io")
    HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")
    HINDSIGHT_BANK_ID: str = os.getenv("HINDSIGHT_BANK_ID", "flowdesk-feedback-bank")

    # Web & CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()

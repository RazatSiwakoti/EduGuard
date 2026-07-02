"""
Centralized application configuration.
Loads environment variables from the project root .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# EduGuard project root
# .../EduGuard/backend/app/config.py
# parents[2] -> .../EduGuard
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):

    # Application
    APP_NAME: str
    ENVIRONMENT: str
    DEBUG: bool

    # Database
    DATABASE_URL: str

    # Frontend
    FRONTEND_URL: str
    ALLOWED_ORIGINS: str

    # Authentication
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str

    # Scheduler
    CHECKPOINT_WEEK: int
    SCHEDULER_TIMEZONE: str

    # ML
    MODEL_PATH: str
    RISK_THRESHOLD: float


    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
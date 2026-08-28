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

    # "console" writes each message to var/outbox/*.eml and sends nothing.
    # "smtp" dials the real server. Split out of ENVIRONMENT deliberately:
    # tying live mail to "am I in production" meant the only way to prove
    # SMTP works was to declare a dev laptop a production system, which
    # also changes unrelated behaviour. This key does one thing.
    #
    # DEFAULTED, not required. Every other setting here is mandatory, and
    # adding a mandatory key makes an existing .env fail startup with a
    # pydantic error that names every setting at once - which reads like a
    # corrupt config rather than a missing line. A new key that already has
    # the safe answer does not deserve to break a working checkout.
    EMAIL_BACKEND: str = "console"

    # The externally reachable base URL of THIS API.
    #
    # Acknowledgment links are clicked from a mail client, on a machine
    # that is not this one, so they cannot be relative. They also cannot
    # borrow FRONTEND_URL: the receipt page is rendered by the backend,
    # because a student has no account and therefore cannot be handed a
    # page that lives behind the SPA's auth.
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Scheduler
    CHECKPOINT_WEEK: int
    SCHEDULER_TIMEZONE: str

    # Standard 5-field cron: minute hour day-of-month month day-of-week,
    # read in SCHEDULER_TIMEZONE. The default is the Monday 08:00 sweep
    # that used to be a literal inside scheduler.py, where nobody
    # demonstrating the system could reach it.
    ALERT_SWEEP_CRON: str = "0 8 * * 1"

    # ML
    MODEL_PATH: str
    RISK_THRESHOLD: float


    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

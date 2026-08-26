"""
Configuration Management
Loads all settings from environment variables
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    """Application Configuration"""
    
    # Application
    APP_NAME = os.getenv("APP_NAME", "EduGuard")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # API
    API_PREFIX = "/api"
    
    # Database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'test.db')}"
    )
    
    # Frontend CORS
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    
    # Email/SMTP Configuration
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@eduguard.com")
    
    # Authentication
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # ML/Risk Assessment
    MODEL_PATH = os.getenv("MODEL_PATH", "models/risk_model.pkl")
    RISK_THRESHOLD = float(os.getenv("RISK_THRESHOLD", "0.5"))
    
    # Scheduler & Timezone
    CHECKPOINT_WEEK = int(os.getenv("CHECKPOINT_WEEK", "4"))
    TIMEZONE = os.getenv("TIMEZONE", "Australia/Sydney")
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "Australia/Sydney")


settings = Settings()


def get_current_time():
    """Return the current local datetime according to configured TIMEZONE (defaults to Australia/Sydney)"""
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        tz = ZoneInfo(settings.TIMEZONE)
        return datetime.now(tz).replace(tzinfo=None)
    except Exception:
        from datetime import datetime
        return datetime.now()

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from typing import Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Standardised POD System"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretpodkey1234567890changeinproduction"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Environment variable support for Postgres
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = None

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "pod_user"
    POSTGRES_PASSWORD: str = "pod_password"
    POSTGRES_DB: str = "pod_db"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        user = self.DB_USER or os.getenv("DB_USER") or self.POSTGRES_USER
        password = self.DB_PASSWORD or os.getenv("DB_PASSWORD") or self.POSTGRES_PASSWORD
        host = self.DB_HOST or os.getenv("DB_HOST") or self.POSTGRES_SERVER
        port = self.DB_PORT or os.getenv("DB_PORT") or self.POSTGRES_PORT
        db_name = self.DB_NAME or os.getenv("DB_NAME") or self.POSTGRES_DB
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    
    # Storage
    STORAGE_TYPE: str = "local" # local or minio
    LOCAL_STORAGE_DIR: str = "./uploaded_evidence"
    
    # Evidence Engine thresholds
    GPS_MISMATCH_THRESHOLD_METERS: float = 150.0
    OPENCV_BLUR_THRESHOLD: float = 100.0
    OPENCV_BRIGHTNESS_MIN: float = 40.0
    OPENCV_BRIGHTNESS_MAX: float = 220.0

    # SMS Service Configuration
    SMS_PROVIDER: Optional[str] = None  # e.g., 'fast2sms', 'twilio', 'generic', 'sandbox', 'mock'
    FAST2SMS_API_KEY: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    SMS_API_URL: Optional[str] = None
    SMS_API_KEY: Optional[str] = None

settings = Settings()


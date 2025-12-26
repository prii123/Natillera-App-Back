from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET_NAME: Optional[str] = None
    # Mantener SECRET_KEY para otras funcionalidades si es necesario
    SECRET_KEY: str = "fallback-secret-key"

    class Config:
        env_file = ".env"

settings = Settings()

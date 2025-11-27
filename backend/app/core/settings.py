import os
from typing import List
from urllib.parse import urlparse


class Settings:
    DEBUG = os.getenv("DEBUG", "1") == "1"
    # Secrets (externalized)
    JWKS_URL = os.getenv("RSN_JWKS_URL", "https://vault.internal.rsn/v1/rsn/jwks")
    JWKS_CACHE_SECONDS = int(os.getenv("RSN_JWKS_CACHE_SECONDS", "300"))
    JWT_AUD = os.getenv("RSN_JWT_AUD", "rsn-api")
    SECRET_KEY = os.getenv("RSN_SECRET_KEY")
    if not SECRET_KEY:
        if DEBUG:
            SECRET_KEY = "dev-secret-key"
        else:
            raise RuntimeError("RSN_SECRET_KEY environment variable is not set. Fail Closed.")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        o for o in os.getenv("RSN_CORS", "https://app.rsn.ai").split(",") if o
    ]

    # Database
    DB_URL = os.getenv("DB_URL", "sqlite:///./rsn-light.db")

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://rsn-redis:6379/0")
    _redis_parsed = urlparse(REDIS_URL)
    REDIS_HOST = _redis_parsed.hostname or "localhost"
    REDIS_PORT = _redis_parsed.port or 6379

    # MinIO
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "rexsyn-nexus")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}

    # MLflow
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://rsn-mlflow:5000")

    # Science calculators
    SCIENCE_MODE = os.getenv("SCIENCE_MODE", "placeholder")  # placeholder | external
    POSEBUSTERS_CMD = os.getenv("POSEBUSTERS_CMD", "")
    DOCKQ_CMD = os.getenv("DOCKQ_CMD", "")
    SAXS_CMD = os.getenv("SAXS_CMD", "")


settings = Settings()

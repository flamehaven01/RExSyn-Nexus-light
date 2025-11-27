"""
Lightweight pytest configuration for the OSS light edition.

- Forces SQLite + dummy secrets so the app can start without external deps.
- Keeps import path stable for `app` package.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Minimal environment for local tests (no external services required)
os.environ.setdefault("RSN_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DB_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("RSN_JWKS_URL", "local")
os.environ.setdefault("MLFLOW_TRACKING_URI", "")
os.environ.setdefault("MINIO_ENDPOINT", "")


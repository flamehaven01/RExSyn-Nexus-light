"""
Backward-compatible database helpers.

Older tests import ``app.core.db`` directly, so this module re-exports the
newer database utilities defined in ``app.db.database``.
"""

from app.db.database import SessionLocal, get_db, init_db, Base  # noqa: F401

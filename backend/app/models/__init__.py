"""
Compatibility layer for legacy imports such as ``app.models.job``.

Newer code keeps ORM definitions in ``app.db.models``, so this package
re-exports the relevant objects for older tests and integrations.
"""

from app.db.models import *  # noqa: F401,F403

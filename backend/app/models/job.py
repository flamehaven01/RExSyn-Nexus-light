"""
Legacy shim so ``from app.models.job import Job`` remains valid.
"""

from app.db.models import Job  # noqa: F401

"""
Celery Application Configuration
=================================

Background task queue for long-running predictions.
"""

import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

# Broker / backend configuration (override via env for local smoke)
BROKER_URL = os.getenv("BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
RESULT_BACKEND = os.getenv("RESULT_BACKEND", BROKER_URL)

# Create Celery app
celery_app = Celery(
    "rexsyn_nexus",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks.prediction_tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_expires=3600 * 24 * 7,  # 7 days

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600 * 2,  # 2 hours hard limit
    task_soft_time_limit=3600,  # 1 hour soft limit

    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes max backoff
    task_retry_jitter=True,

    # Worker settings
    worker_prefetch_multiplier=1,  # Disable prefetching for fair distribution
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Beat schedule (for periodic tasks)
    beat_schedule={
        "cleanup-expired-jobs": {
            "task": "app.tasks.prediction_tasks.cleanup_expired_jobs",
            "schedule": 3600,  # Every hour
        },
    },
)

# Optional eager mode for local smoke (no broker)
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in {"1", "true", "yes"}:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


# ============================================================================
# Task Signals
# ============================================================================

@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Log when task starts."""
    print(f"Task {task.name} [{task_id}] started")


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """Log when task completes."""
    print(f"Task {task.name} [{task_id}] completed")


@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    """Log when task fails."""
    print(f"Task [{task_id}] failed: {exception}")


# ============================================================================
# Helper Functions
# ============================================================================

def get_task_status(task_id: str) -> dict:
    """
    Get status of a Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        dict with task status
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
        "error": str(result.info) if result.failed() else None,
    }


def revoke_task(task_id: str, terminate: bool = False):
    """
    Cancel a running task.

    Args:
        task_id: Celery task ID
        terminate: If True, terminate immediately (SIGKILL)
    """
    celery_app.control.revoke(task_id, terminate=terminate)

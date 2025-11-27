import logging

try:
    import mlflow  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    mlflow = None

logger = logging.getLogger(__name__)


class MLflowService:
    def log_artifact(self, run_id: str, path: str, artifact_path: str = ""):
        """Log artifact to an existing MLflow run without creating a new one."""
        if not run_id:
            raise ValueError("run_id is required to log artifacts to an existing run")

        if mlflow is None:
            logger.warning("MLflow missing; skip log_artifact run_id=%s path=%s", run_id, path)
            return

        # Use existing run context; do not create a new run
        with mlflow.start_run(run_id=run_id):
            mlflow.log_artifact(path, artifact_path=artifact_path)

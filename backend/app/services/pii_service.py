"""PII Cascade Delete Service for GDPR Article 17 Compliance

Implements right to erasure across:
1. PostgreSQL (job metadata, user data)
2. MLflow (experiment runs, artifacts)
3. MinIO (PDB files, checkpoints, logs)
4. Redis (cached results)
"""

import hashlib
import logging
from typing import Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:  # pragma: no cover - optional heavy deps
    import mlflow  # type: ignore
except Exception as e:  # pragma: no cover
    mlflow = None
    logging.getLogger(__name__).warning("MLflow unavailable: %s", e)

try:  # pragma: no cover - optional
    from minio import Minio  # type: ignore
except Exception as e:  # pragma: no cover
    Minio = None  # type: ignore
    logging.getLogger(__name__).warning("MinIO client unavailable: %s", e)

try:  # pragma: no cover - optional
    from redis import Redis  # type: ignore
except Exception as e:  # pragma: no cover
    Redis = None  # type: ignore
    logging.getLogger(__name__).warning("Redis client unavailable: %s", e)
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.db.database import SessionLocal
from app.models.job import Job
from app.core.config import settings

logger = logging.getLogger(__name__)


class PIIService:
    """
    GDPR Article 17 compliant PII deletion service with dependency injection.

    All storage clients can be injected for testability and loose coupling.
    If not provided, default implementations are created.
    """

    def __init__(
        self,
        db: Session = None,
        redis_client: Redis = None,
        minio_client: Minio = None
    ):
        """
        Initialize PIIService with dependency injection.

        Args:
            db: Optional SQLAlchemy session
            redis_client: Optional Redis client instance
            minio_client: Optional MinIO client instance
        """
        logger.info("Initializing PIIService with DI pattern")

        # Initialize database session (injected or create new)
        self._owns_db = db is None
        if db is not None:
            self.db = db
            logger.info("Using injected database session")
        else:
            self.db = SessionLocal()
            logger.info("Created new database session from SessionLocal()")

        # Initialize Redis client (injected or create new)
        if redis_client is not None:
            self.redis = redis_client
            logger.info("Using injected Redis client")
        elif Redis is not None:
            logger.info(f"Creating Redis client: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            self.redis = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=False
            )
            logger.info("Redis client created successfully")
        else:
            self.redis = None
            logger.warning("Redis not available; skipping redis client init (light mode)")

        # Initialize MinIO client (injected or create new)
        if minio_client is not None:
            self.minio = minio_client
            logger.info("Using injected MinIO client")
        elif Minio is not None:
            logger.info(f"Creating MinIO client: {settings.MINIO_ENDPOINT}")
            self.minio = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            logger.info("MinIO client created successfully")
        else:
            self.minio = None
            logger.warning("MinIO not available; skipping minio client init (light mode)")

        logger.info("PIIService initialized successfully with all storage clients")

    def close(self):
        """Close owned resources."""
        try:
            if self._owns_db and getattr(self, "db", None):
                self.db.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def cascade_delete(self, job_id: str, org_id: str) -> Dict[str, Any]:
        """
        Cascade delete all PII/artifacts for a job.

        Args:
            job_id: Job identifier
            org_id: Organization ID for authorization

        Returns:
            Deletion summary with counts and audit hash

        Raises:
            ValueError: If job not found or unauthorized
        """
        logger.info(f"Starting cascade delete for job {job_id}")

        # 1. Verify job exists and belongs to org
        job = self.db.query(Job).filter(
            Job.id == job_id,
            Job.org_id == org_id
        ).first()

        if not job:
            logger.error(f"Job {job_id} not found or unauthorized for org {org_id}")
            raise ValueError(f"Job {job_id} not found or unauthorized")

        deletion_log = {
            "job_id": job_id,
            "org_id": org_id,
            "timestamp": datetime.utcnow().isoformat(),
            "deleted_items": []
        }

        # 2. Delete from PostgreSQL first (validates authorization)
        logger.info("Deleting from PostgreSQL")
        db_result = self._delete_from_postgres(job_id)
        deletion_log["deleted_items"].extend(db_result)

        # 3-5. Parallel deletion from MLflow, MinIO, Redis (independent operations)
        logger.info("Starting parallel deletion from MLflow, MinIO, Redis")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._delete_from_mlflow, job_id): "mlflow",
                executor.submit(self._delete_from_minio, job_id): "minio",
                executor.submit(self._delete_from_redis, job_id): "redis"
            }

            for future in as_completed(futures):
                storage_name = futures[future]
                try:
                    result = future.result()
                    deletion_log["deleted_items"].extend(result)
                    logger.info(f"Completed deletion from {storage_name}: {len(result)} items")
                except Exception as e:
                    logger.error(f"Failed to delete from {storage_name}: {e}")

        # 6. Generate audit hash
        audit_hash = self._generate_audit_hash(deletion_log)

        # 7. Log to audit trail
        self._log_audit_trail(job_id, org_id, audit_hash, deletion_log)

        logger.info(f"Cascade delete completed for job {job_id}: {len(deletion_log['deleted_items'])} items deleted")

        return {
            "artifact_count": len(deletion_log["deleted_items"]),
            "mlflow_deleted": any(item["storage"] == "mlflow" for item in deletion_log["deleted_items"]),
            "minio_deleted": any(item["storage"] == "minio" for item in deletion_log["deleted_items"]),
            "postgres_deleted": any(item["storage"] == "postgres" for item in deletion_log["deleted_items"]),
            "redis_deleted": any(item["storage"] == "redis" for item in deletion_log["deleted_items"]),
            "audit_hash": audit_hash
        }

    def _delete_from_postgres(self, job_id: str) -> List[Dict]:
        """Delete job and related records from PostgreSQL."""
        deleted = []

        try:
            # Delete job record (cascades to related tables via FK constraints)
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                self.db.delete(job)
                self.db.commit()
                deleted.append({
                    "storage": "postgres",
                    "type": "job_record",
                    "identifier": job_id
                })
                logger.info(f"Deleted job {job_id} from PostgreSQL")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete from PostgreSQL: {e}")
            raise

        return deleted

    def _delete_from_mlflow(self, job_id: str) -> List[Dict]:
        """Delete MLflow runs and artifacts."""
        deleted = []

        try:
            # Search for runs associated with this job
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
            runs = mlflow.search_runs(
                filter_string=f"tags.job_id = '{job_id}'",
                output_format="list"
            )

            for run in runs:
                run_id = run.info.run_id
                mlflow.delete_run(run_id)
                deleted.append({
                    "storage": "mlflow",
                    "type": "run",
                    "identifier": run_id
                })
                logger.info(f"Deleted MLflow run {run_id} for job {job_id}")

        except Exception as e:
            logger.error(f"Failed to delete from MLflow: {e}")
            # Don't raise - continue with other deletions

        return deleted

    def _delete_from_minio(self, job_id: str) -> List[Dict]:
        """Delete MinIO objects (PDB files, checkpoints, logs)."""
        deleted = []

        try:
            bucket_name = settings.MINIO_BUCKET
            prefix = f"jobs/{job_id}/"

            # List all objects with this prefix
            objects = self.minio.list_objects(
                bucket_name,
                prefix=prefix,
                recursive=True
            )

            for obj in objects:
                self.minio.remove_object(bucket_name, obj.object_name)
                deleted.append({
                    "storage": "minio",
                    "type": "object",
                    "identifier": obj.object_name
                })
                logger.info(f"Deleted MinIO object {obj.object_name}")

        except Exception as e:
            logger.error(f"Failed to delete from MinIO: {e}")
            # Don't raise - continue with other deletions

        return deleted

    def _delete_from_redis(self, job_id: str) -> List[Dict]:
        """Delete Redis cache entries for this job."""
        deleted = []

        try:
            # Delete job-specific cache keys
            patterns = [
                f"rex:job:{job_id}:*",
                f"rex:result:{job_id}",
                f"rex:status:{job_id}",
                f"rex:plddt:{job_id}"
            ]

            keys_to_delete = set()
            for pattern in patterns:
                for key in self.redis.keys(pattern):
                    keys_to_delete.add(key)

            if keys_to_delete:
                self.redis.delete(*keys_to_delete)
                for key in keys_to_delete:
                    identifier = key.decode() if isinstance(key, bytes) else key
                    deleted.append({
                        "storage": "redis",
                        "type": "cache_key",
                        "identifier": identifier
                    })
                    logger.info(f"Deleted Redis key {identifier}")

        except Exception as e:
            logger.error(f"Failed to delete from Redis: {e}")
            # Don't raise - continue

        return deleted

    def _generate_audit_hash(self, deletion_log: Dict) -> str:
        """Generate SHA-256 hash of deletion log for audit trail."""
        log_str = str(deletion_log)
        return hashlib.sha256(log_str.encode()).hexdigest()

    def _log_audit_trail(
        self,
        job_id: str,
        org_id: str,
        audit_hash: str,
        deletion_log: Dict
    ):
        """Log deletion to audit trail (compliance requirement)."""
        # In production, this would write to a tamper-proof audit log
        # (e.g., append-only database, blockchain, or WORM storage)
        
        audit_key = f"rex:audit:pii_delete:{job_id}"
        self.redis.setex(
            audit_key,
            86400 * 365,  # Retain for 1 year
            str({
                "job_id": job_id,
                "org_id": org_id,
                "timestamp": deletion_log["timestamp"],
                "audit_hash": audit_hash,
                "item_count": len(deletion_log["deleted_items"])
            })
        )
        
        logger.info(
            f"PII deletion audit trail created for job {job_id} "
            f"(hash: {audit_hash[:16]}...)"
        )

    def bulk_delete_by_user(self, user_id: str, org_id: str) -> Dict[str, Any]:
        """
        Delete all PII for a user (full GDPR erasure).

        Args:
            user_id: User identifier
            org_id: Organization ID for authorization

        Returns:
            Summary of deleted jobs and artifacts
        """
        logger.info(f"Starting bulk delete for user {user_id} in org {org_id}")

        # Find all jobs for this user
        jobs = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.org_id == org_id
        ).all()

        logger.info(f"Found {len(jobs)} jobs to delete for user {user_id}")

        # Parallel deletion of multiple jobs (max 5 concurrent to avoid overload)
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_job = {
                executor.submit(self.cascade_delete, job.id, org_id): job.id
                for job in jobs
            }

            for future in as_completed(future_to_job):
                job_id = future_to_job[future]
                try:
                    result = future.result()
                    results.append({
                        "job_id": job_id,
                        "success": True,
                        "audit_hash": result["audit_hash"]
                    })
                    logger.info(f"Successfully deleted job {job_id}")
                except Exception as e:
                    logger.error(f"Failed to delete job {job_id}: {e}")
                    results.append({
                        "job_id": job_id,
                        "success": False,
                        "error": str(e)
                    })

        successful = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])
        logger.info(f"Bulk delete completed: {successful} succeeded, {failed} failed")

        return {
            "user_id": user_id,
            "total_jobs": len(jobs),
            "successful_deletions": successful,
            "failed_deletions": failed,
            "results": results
        }

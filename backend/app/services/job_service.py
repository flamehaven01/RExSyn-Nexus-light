"""
Job Service - Business Logic for Job Lifecycle
===============================================

Handles job lifecycle operations following Single Responsibility Principle.

Extracted from God Object anti-pattern (backend/app/db/models.py and backend/app/api/v1/job_management.py).

Responsibilities:
- Job creation and initialization
- Job cancellation and deletion
- Expiration calculation
- Job queries and filtering

NOT responsible for:
- State transitions (see JobStateManager)
- Access control (see JobAccessController)
- Data persistence (handled by SQLAlchemy models)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.db.models import Job, Result, FileStorage, AuditLog, JobStatus, Organization
from app.services.storage_service import delete_job_files


class JobService:
    """Core business logic for job lifecycle operations."""

    def __init__(self, db: Session):
        """
        Initialize service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_job(
        self,
        job_id: str,
        user_id: str,
        org_id: str,
        sequence: str,
        experiment_type: str,
        method: str,
        ethics_config: Optional[Dict[str, Any]] = None,
        prediction_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """
        Create a new job with initialization.

        Args:
            job_id: Unique job identifier
            user_id: User creating the job
            org_id: Organization ID
            sequence: Protein sequence
            experiment_type: Type of experiment
            method: Prediction method (alphafold3, esmfold, etc.)
            ethics_config: Optional ethics configuration
            prediction_config: Optional prediction configuration
            metadata: Optional additional metadata

        Returns:
            Created Job instance

        Raises:
            ValueError: If job_id already exists
        """
        # Check if job already exists
        existing = self.db.query(Job).filter(Job.id == job_id).first()
        if existing:
            raise ValueError(f"Job with ID '{job_id}' already exists")

        # Get organization for retention settings
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        retention_days = org.data_retention_days if org else 30

        # Calculate expiration
        created_at = datetime.utcnow()
        expires_at = self.calculate_expiration(created_at, retention_days)

        # Create job
        job = Job(
            id=job_id,
            user_id=user_id,
            org_id=org_id,
            sequence=sequence,
            experiment_type=experiment_type,
            method=method,
            ethics_config=ethics_config or {},
            prediction_config=prediction_config or {},
            metadata=metadata or {},
            status=JobStatus.QUEUED,
            progress=0.0,
            created_at=created_at,
            expires_at=expires_at,
            stage_index=0,
            total_stages=7,
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return job

    def cancel_job(self, job: Job) -> Job:
        """
        Cancel a running or queued job.

        Args:
            job: Job to cancel

        Returns:
            Updated job

        Raises:
            ValueError: If job cannot be cancelled (already completed/failed)
        """
        if job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
            raise ValueError(
                f"Cannot cancel job with status '{job.status}'. "
                "Only queued or running jobs can be cancelled."
            )

        # TODO: Cancel Celery task if exists
        # from app.celery_app import revoke_task
        # if job.celery_task_id:
        #     revoke_task(job.celery_task_id, terminate=True)

        job.status = JobStatus.CANCELLED
        self.db.commit()
        self.db.refresh(job)

        return job

    def delete_job(self, job: Job, force: bool = False) -> Dict[str, Any]:
        """
        Delete a job and all associated data.

        Args:
            job: Job to delete
            force: If True, delete regardless of status (admin only)

        Returns:
            Dictionary with deletion summary

        Raises:
            ValueError: If job cannot be deleted (still running and not forced)
        """
        # Check if job can be deleted
        if not force and job.status in [JobStatus.RUNNING, JobStatus.QUEUED]:
            raise ValueError(
                f"Cannot delete job with status '{job.status}'. "
                "Cancel the job first or use force=True (admin only)."
            )

        deletion_summary = {
            "job_id": job.id,
            "files_deleted": 0,
            "database_records_deleted": 0,
            "errors": [],
        }

        # Delete files from storage
        try:
            delete_job_files(job.id)
            # Count files that were deleted
            file_count = self.db.query(FileStorage).filter(
                FileStorage.job_id == job.id
            ).count()
            deletion_summary["files_deleted"] = file_count
        except Exception as e:
            deletion_summary["errors"].append(f"File deletion error: {str(e)}")

        # Delete database records
        try:
            # Delete related records
            file_storage_count = self.db.query(FileStorage).filter(
                FileStorage.job_id == job.id
            ).delete()
            audit_log_count = self.db.query(AuditLog).filter(
                AuditLog.job_id == job.id
            ).delete()
            result_count = self.db.query(Result).filter(
                Result.job_id == job.id
            ).delete()

            # Delete job
            self.db.delete(job)
            self.db.commit()

            deletion_summary["database_records_deleted"] = (
                file_storage_count + audit_log_count + result_count + 1
            )
        except Exception as e:
            self.db.rollback()
            deletion_summary["errors"].append(f"Database deletion error: {str(e)}")
            raise

        return deletion_summary

    def retry_job(self, job: Job) -> Job:
        """
        Retry a failed job.

        Args:
            job: Failed job to retry

        Returns:
            Updated job ready for retry

        Raises:
            ValueError: If job is not in failed state or retry limit exceeded
        """
        if job.status != JobStatus.FAILED:
            raise ValueError(
                f"Cannot retry job with status '{job.status}'. "
                "Only failed jobs can be retried."
            )

        # Check retry limit (max 3 retries)
        if job.retry_count >= 3:
            raise ValueError(
                f"Retry limit exceeded. Job has already been retried {job.retry_count} times."
            )

        # Reset job for retry
        job.status = JobStatus.QUEUED
        job.progress = 0.0
        job.retry_count += 1
        job.error_message = None
        job.error_traceback = None
        job.started_at = None
        job.completed_at = None

        self.db.commit()
        self.db.refresh(job)

        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job if found, None otherwise
        """
        return self.db.query(Job).filter(Job.id == job_id).first()

    def list_jobs(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        experiment_type: Optional[str] = None,
        method: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[List[Job], int]:
        """
        List jobs with filtering, pagination, and sorting.

        Args:
            user_id: Filter by user ID
            org_id: Filter by organization ID
            status: Filter by job status
            experiment_type: Filter by experiment type
            method: Filter by prediction method
            page: Page number (1-indexed)
            page_size: Number of items per page
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'

        Returns:
            Tuple of (jobs list, total count)
        """
        query = self.db.query(Job)

        # Apply filters
        if user_id:
            query = query.filter(Job.user_id == user_id)
        if org_id:
            query = query.filter(Job.org_id == org_id)
        if status:
            query = query.filter(Job.status == status)
        if experiment_type:
            query = query.filter(Job.experiment_type == experiment_type)
        if method:
            query = query.filter(Job.method == method)

        # Get total count
        total = query.count()

        # Apply sorting
        sort_column = getattr(Job, sort_by, Job.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        offset = (page - 1) * page_size
        jobs = query.offset(offset).limit(page_size).all()

        return jobs, total

    def calculate_expiration(
        self, created_at: datetime, retention_days: int = 30
    ) -> datetime:
        """
        Calculate when a job should expire based on retention policy.

        Args:
            created_at: Job creation timestamp
            retention_days: Number of days to retain (default: 30)

        Returns:
            Expiration datetime
        """
        return created_at + timedelta(days=retention_days)

    def should_expire(self, job: Job) -> bool:
        """
        Check if a job should be expired and deleted.

        Args:
            job: Job to check

        Returns:
            True if job should be expired, False otherwise
        """
        if job.expires_at is None:
            return False
        return datetime.utcnow() >= job.expires_at

    def get_expired_jobs(self, limit: int = 100) -> List[Job]:
        """
        Get list of jobs that have expired and should be deleted.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of expired jobs
        """
        now = datetime.utcnow()
        return (
            self.db.query(Job)
            .filter(Job.expires_at <= now)
            .filter(Job.expires_at.isnot(None))
            .limit(limit)
            .all()
        )

    def cleanup_expired_jobs(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Delete expired jobs in batch.

        Args:
            batch_size: Number of jobs to process per batch

        Returns:
            Cleanup summary with counts and errors
        """
        expired_jobs = self.get_expired_jobs(limit=batch_size)

        summary = {
            "total_expired": len(expired_jobs),
            "successfully_deleted": 0,
            "failed": 0,
            "errors": [],
        }

        for job in expired_jobs:
            try:
                self.delete_job(job, force=True)
                summary["successfully_deleted"] += 1
            except Exception as e:
                summary["failed"] += 1
                summary["errors"].append({
                    "job_id": job.id,
                    "error": str(e),
                })

        return summary

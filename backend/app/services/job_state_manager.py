"""
Job State Manager - State Transitions and Progress Tracking
============================================================

Handles job state management following Single Responsibility Principle.

Extracted from God Object anti-pattern.

Responsibilities:
- State transitions with validation
- Progress tracking and estimation
- Stage management
- Timing and duration tracking

NOT responsible for:
- Job creation/deletion (see JobService)
- Access control (see JobAccessController)
- Business logic (see JobService)
"""

from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Job, JobStatus


class StageTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class JobStageDefinition:
    """
    Defines the standard pipeline stages.

    Each stage has a name, estimated duration, and validation criteria.
    """

    STAGES = [
        {"name": "Input Validation", "index": 0, "estimated_seconds": 5},
        {"name": "Ethics Check (SIDRCE)", "index": 1, "estimated_seconds": 10},
        {"name": "Semantic Routing", "index": 2, "estimated_seconds": 3},
        {"name": "Structure Prediction", "index": 3, "estimated_seconds": 300},
        {"name": "Quality Assessment", "index": 4, "estimated_seconds": 30},
        {"name": "MD Refinement (Optional)", "index": 5, "estimated_seconds": 600},
        {"name": "Report Generation", "index": 6, "estimated_seconds": 15},
    ]

    @classmethod
    def get_stage(cls, index: int) -> Optional[Dict[str, Any]]:
        """Get stage definition by index."""
        if 0 <= index < len(cls.STAGES):
            return cls.STAGES[index]
        return None

    @classmethod
    def calculate_total_time(cls, include_md_refinement: bool = False) -> int:
        """Calculate total estimated processing time."""
        total = sum(s["estimated_seconds"] for s in cls.STAGES)
        if not include_md_refinement:
            # Subtract MD refinement stage
            total -= cls.STAGES[5]["estimated_seconds"]
        return total


class JobStateManager:
    """Manages job state transitions and progress tracking."""

    # Valid state transitions
    VALID_TRANSITIONS = {
        JobStatus.QUEUED: [JobStatus.RUNNING, JobStatus.CANCELLED],
        JobStatus.RUNNING: [
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ],
        JobStatus.COMPLETED: [],  # Terminal state
        JobStatus.FAILED: [JobStatus.QUEUED],  # Can retry
        JobStatus.CANCELLED: [],  # Terminal state
    }

    def __init__(self, db: Session):
        """
        Initialize state manager with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def transition_to(
        self, job: Job, new_status: JobStatus, error_message: Optional[str] = None
    ) -> Job:
        """
        Transition job to new status with validation.

        Args:
            job: Job to transition
            new_status: Target status
            error_message: Optional error message for failed transitions

        Returns:
            Updated job

        Raises:
            StageTransitionError: If transition is invalid
        """
        # Validate transition
        if not self.can_transition(job.status, new_status):
            raise StageTransitionError(
                f"Invalid state transition from '{job.status}' to '{new_status}'. "
                f"Valid transitions: {self.VALID_TRANSITIONS.get(job.status, [])}"
            )

        # Update timestamps based on new status
        if new_status == JobStatus.RUNNING and job.started_at is None:
            job.started_at = datetime.utcnow()

        elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_at = datetime.utcnow()

            # Calculate processing time
            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                job.processing_time_seconds = int(duration)

            # Set progress to 100% for completed, 0% for failed/cancelled
            if new_status == JobStatus.COMPLETED:
                job.progress = 1.0
            else:
                job.progress = 0.0

        # Handle errors
        if new_status == JobStatus.FAILED:
            job.error_message = error_message or "Unknown error"

        # Update status
        job.status = new_status
        self.db.commit()
        self.db.refresh(job)

        return job

    def can_transition(
        self, current_status: JobStatus, new_status: JobStatus
    ) -> bool:
        """
        Check if a state transition is valid.

        Args:
            current_status: Current job status
            new_status: Target status

        Returns:
            True if transition is valid, False otherwise
        """
        valid_next_states = self.VALID_TRANSITIONS.get(current_status, [])
        return new_status in valid_next_states

    def start_job(self, job: Job) -> Job:
        """
        Start a queued job.

        Args:
            job: Job to start

        Returns:
            Updated job with RUNNING status
        """
        return self.transition_to(job, JobStatus.RUNNING)

    def complete_job(self, job: Job) -> Job:
        """
        Mark job as completed.

        Args:
            job: Job to complete

        Returns:
            Updated job with COMPLETED status
        """
        return self.transition_to(job, JobStatus.COMPLETED)

    def fail_job(self, job: Job, error_message: str, traceback: Optional[str] = None) -> Job:
        """
        Mark job as failed with error details.

        Args:
            job: Job to mark as failed
            error_message: Error message
            traceback: Optional error traceback

        Returns:
            Updated job with FAILED status
        """
        job.error_traceback = traceback
        return self.transition_to(job, JobStatus.FAILED, error_message=error_message)

    def update_progress(
        self,
        job: Job,
        progress: float,
        current_stage: Optional[str] = None,
        stage_index: Optional[int] = None,
    ) -> Job:
        """
        Update job progress and current stage.

        Args:
            job: Job to update
            progress: Progress as float (0.0 to 1.0)
            current_stage: Optional current stage name
            stage_index: Optional current stage index

        Returns:
            Updated job

        Raises:
            ValueError: If progress is out of bounds
        """
        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {progress}")

        job.progress = progress

        if current_stage is not None:
            job.current_stage = current_stage

        if stage_index is not None:
            if not 0 <= stage_index < job.total_stages:
                raise ValueError(
                    f"Stage index {stage_index} out of bounds (total: {job.total_stages})"
                )
            job.stage_index = stage_index

        self.db.commit()
        self.db.refresh(job)

        return job

    def advance_stage(self, job: Job, stage_name: Optional[str] = None) -> Job:
        """
        Advance to the next stage.

        Args:
            job: Job to advance
            stage_name: Optional custom stage name (uses default if not provided)

        Returns:
            Updated job
        """
        next_index = job.stage_index + 1

        if next_index >= job.total_stages:
            # Reached final stage, complete the job
            return self.complete_job(job)

        # Get stage definition
        stage = JobStageDefinition.get_stage(next_index)
        if stage and stage_name is None:
            stage_name = stage["name"]

        # Calculate progress
        progress = next_index / job.total_stages

        return self.update_progress(
            job,
            progress=progress,
            current_stage=stage_name or f"Stage {next_index + 1}",
            stage_index=next_index,
        )

    def estimate_remaining_time(self, job: Job) -> Optional[int]:
        """
        Estimate remaining processing time in seconds.

        Args:
            job: Job to estimate

        Returns:
            Estimated remaining seconds, or None if cannot estimate
        """
        if job.status not in [JobStatus.RUNNING, JobStatus.QUEUED]:
            return None

        if job.estimated_time_seconds is None:
            # Use default estimation from stage definitions
            total_time = JobStageDefinition.calculate_total_time(
                include_md_refinement=True  # Conservative estimate
            )
        else:
            total_time = job.estimated_time_seconds

        # Calculate remaining time based on progress
        if job.progress > 0:
            remaining = int(total_time * (1.0 - job.progress))
        else:
            remaining = total_time

        return remaining

    def calculate_eta(self, job: Job) -> Optional[datetime]:
        """
        Calculate estimated time of completion (ETA).

        Args:
            job: Job to calculate ETA for

        Returns:
            Estimated completion datetime, or None if cannot calculate
        """
        remaining_seconds = self.estimate_remaining_time(job)

        if remaining_seconds is None:
            return None

        if job.started_at:
            # Use actual start time
            from datetime import timedelta
            return datetime.utcnow() + timedelta(seconds=remaining_seconds)
        else:
            # Job not started yet, cannot calculate ETA
            return None

    def get_stage_progress_details(self, job: Job) -> Dict[str, Any]:
        """
        Get detailed progress information including stage breakdown.

        Args:
            job: Job to analyze

        Returns:
            Dictionary with detailed progress information
        """
        current_stage_info = JobStageDefinition.get_stage(job.stage_index)

        return {
            "job_id": job.id,
            "status": job.status.value,
            "overall_progress": job.progress,
            "current_stage": {
                "name": job.current_stage or "Unknown",
                "index": job.stage_index,
                "total_stages": job.total_stages,
                "definition": current_stage_info,
            },
            "timing": {
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "processing_time_seconds": job.processing_time_seconds,
                "estimated_remaining_seconds": self.estimate_remaining_time(job),
                "eta": self.calculate_eta(job).isoformat() if self.calculate_eta(job) else None,
            },
            "stages": JobStageDefinition.STAGES,
        }

"""
Job Access Controller - RBAC Access Control
============================================

Handles job access control following Single Responsibility Principle.

Extracted from God Object anti-pattern (backend/app/api/v1/job_management.py).

Responsibilities:
- Role-based access control (RBAC)
- Permission checks
- Query filtering based on roles
- Action authorization

NOT responsible for:
- Job lifecycle (see JobService)
- State management (see JobStateManager)
- User authentication (see AuthService)
"""

from sqlalchemy.orm import Session, Query
from fastapi import HTTPException, status

from app.db.models import Job, UserRole
from app.services.auth_service import TokenData


class AccessDeniedError(Exception):
    """Raised when access to a resource is denied."""
    pass


class InsufficientPermissionsError(Exception):
    """Raised when user lacks required permissions for an action."""
    pass


class JobAccessController:
    """Controls access to jobs based on RBAC rules."""

    def __init__(self, db: Session):
        """
        Initialize access controller with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def can_access_job(self, job: Job, user: TokenData) -> bool:
        """
        Check if user has access to a specific job.

        Access Rules:
        - Admin: Can access all jobs in their organization
        - Researcher: Can access only their own jobs
        - Viewer: Can access only their own jobs (read-only)

        Args:
            job: Job to check access for
            user: User token data

        Returns:
            True if user can access job, False otherwise
        """
        # Admin can access all jobs in their organization
        if user.role == UserRole.ADMIN.value:
            return job.org_id == user.org_id

        # Others can only access their own jobs
        return job.user_id == user.user_id

    def require_job_access(self, job: Job, user: TokenData) -> None:
        """
        Require user has access to job, raise exception if not.

        Args:
            job: Job to check access for
            user: User token data

        Raises:
            AccessDeniedError: If user cannot access the job
        """
        if not self.can_access_job(job, user):
            raise AccessDeniedError(
                f"Access denied to job '{job.id}'. "
                "You can only access your own jobs unless you are an admin."
            )

    def can_modify_job(self, job: Job, user: TokenData, action: str = "modify") -> bool:
        """
        Check if user can modify a job (cancel, delete, retry).

        Modification Rules:
        - Admin: Can modify any job in organization
        - Researcher: Can modify own jobs
        - Viewer: Cannot modify jobs (read-only)

        Args:
            job: Job to check modification rights for
            user: User token data
            action: Action being attempted (for error messages)

        Returns:
            True if user can modify job, False otherwise
        """
        # Viewers cannot modify jobs
        if user.role == UserRole.VIEWER.value:
            return False

        # Admins can modify all jobs in their organization
        if user.role == UserRole.ADMIN.value:
            return job.org_id == user.org_id

        # Researchers can modify their own jobs
        return job.user_id == user.user_id

    def require_modify_permission(
        self, job: Job, user: TokenData, action: str = "modify"
    ) -> None:
        """
        Require user can modify job, raise exception if not.

        Args:
            job: Job to check modification rights for
            user: User token data
            action: Action being attempted (for error messages)

        Raises:
            InsufficientPermissionsError: If user cannot modify the job
        """
        if not self.can_modify_job(job, user, action):
            if user.role == UserRole.VIEWER.value:
                raise InsufficientPermissionsError(
                    f"Viewers cannot {action} jobs. Your role is read-only."
                )
            else:
                raise InsufficientPermissionsError(
                    f"You do not have permission to {action} this job. "
                    "You can only modify your own jobs."
                )

    def can_delete_job(self, job: Job, user: TokenData) -> bool:
        """
        Check if user can delete a specific job.

        Delete Rules:
        - Admin: Can delete any job in organization (including running jobs)
        - Researcher: Can delete own jobs (only if completed/failed/cancelled)
        - Viewer: Cannot delete jobs

        Args:
            job: Job to check delete rights for
            user: User token data

        Returns:
            True if user can delete job, False otherwise
        """
        # Viewers cannot delete
        if user.role == UserRole.VIEWER.value:
            return False

        # Admins can delete any job in organization
        if user.role == UserRole.ADMIN.value:
            return job.org_id == user.org_id

        # Researchers can only delete their own completed/failed/cancelled jobs
        from app.db.models import JobStatus
        if job.user_id == user.user_id:
            return job.status in [
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            ]

        return False

    def require_delete_permission(self, job: Job, user: TokenData) -> None:
        """
        Require user can delete job, raise exception if not.

        Args:
            job: Job to check delete rights for
            user: User token data

        Raises:
            InsufficientPermissionsError: If user cannot delete the job
        """
        if not self.can_delete_job(job, user):
            from app.db.models import JobStatus

            if user.role == UserRole.VIEWER.value:
                raise InsufficientPermissionsError(
                    "Viewers cannot delete jobs. Your role is read-only."
                )
            elif job.user_id != user.user_id:
                raise InsufficientPermissionsError(
                    "You can only delete your own jobs."
                )
            elif job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                raise InsufficientPermissionsError(
                    f"Cannot delete job with status '{job.status}'. "
                    "Only completed, failed, or cancelled jobs can be deleted."
                )
            else:
                raise InsufficientPermissionsError(
                    "You do not have permission to delete this job."
                )

    def filter_by_access(self, query: Query, user: TokenData) -> Query:
        """
        Apply role-based filtering to a job query.

        Filter Rules:
        - Admin: See all jobs in organization
        - Researcher: See only own jobs
        - Viewer: See only own jobs

        Args:
            query: SQLAlchemy query to filter
            user: User token data

        Returns:
            Filtered query
        """
        if user.role == UserRole.ADMIN.value:
            # Admin sees all jobs in their organization
            return query.filter(Job.org_id == user.org_id)
        else:
            # Others see only their own jobs
            return query.filter(Job.user_id == user.user_id)

    def get_accessible_job(self, job_id: str, user: TokenData) -> Job:
        """
        Get job by ID with access control.

        Args:
            job_id: Job identifier
            user: User token data

        Returns:
            Job if found and accessible

        Raises:
            HTTPException: If job not found or access denied
        """
        job = self.db.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found"
            )

        try:
            self.require_job_access(job, user)
        except AccessDeniedError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )

        return job

    def check_organization_admin(self, user: TokenData, action: str = "perform this action") -> None:
        """
        Require user is an admin in their organization.

        Args:
            user: User token data
            action: Action description for error message

        Raises:
            InsufficientPermissionsError: If user is not an admin
        """
        if user.role != UserRole.ADMIN.value:
            raise InsufficientPermissionsError(
                f"Only organization admins can {action}. "
                f"Your current role is '{user.role}'."
            )

    def get_permission_summary(self, job: Job, user: TokenData) -> dict:
        """
        Get summary of user's permissions for a specific job.

        Args:
            job: Job to check permissions for
            user: User token data

        Returns:
            Dictionary with permission flags
        """
        return {
            "job_id": job.id,
            "user_id": user.user_id,
            "user_role": user.role,
            "permissions": {
                "can_view": self.can_access_job(job, user),
                "can_modify": self.can_modify_job(job, user),
                "can_cancel": self.can_modify_job(job, user, "cancel"),
                "can_delete": self.can_delete_job(job, user),
                "can_retry": self.can_modify_job(job, user, "retry"),
            },
            "access_reason": self._get_access_reason(job, user),
        }

    def _get_access_reason(self, job: Job, user: TokenData) -> str:
        """
        Get human-readable reason for access level.

        Args:
            job: Job to check
            user: User token data

        Returns:
            Access reason string
        """
        if user.role == UserRole.ADMIN.value and job.org_id == user.org_id:
            return "Organization admin access"
        elif job.user_id == user.user_id:
            return "Job owner"
        else:
            return "No access"

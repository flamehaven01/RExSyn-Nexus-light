"""
Job Management API - RBAC-based Data Access
============================================

User role-based access to jobs and results:
- Admin: All jobs in organization
- Researcher: Only own jobs
- Viewer: Read-only access to own jobs
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.db.database import get_db
from app.db.models import Job, Result, User, JobStatus, UserRole
from app.services.auth_service import get_current_user, TokenData, require_role

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class JobListItem(BaseModel):
    """Job item in list view."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    progress: float
    experiment_type: str
    method: str
    quality_grade: Optional[str]
    confidence: Optional[float]
    created_at: datetime
    processing_time_seconds: Optional[int]
    user_username: str  # For admin view

class JobDetailResponse(BaseModel):
    """Detailed job information."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    progress: float

    # Input
    sequence: str
    experiment_type: str
    method: str

    # Configuration
    ethics_config: dict
    prediction_config: dict

    # Processing info
    current_stage: Optional[str]
    stage_index: int
    estimated_time_seconds: Optional[int]
    processing_time_seconds: Optional[int]

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]

    # Result (if completed)
    result: Optional[dict]

class JobListResponse(BaseModel):
    """Paginated job list."""
    items: List[JobListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class SearchFilters(BaseModel):
    """Search filters for jobs."""
    status: Optional[str] = None
    experiment_type: Optional[str] = None
    method: Optional[str] = None
    quality_grade: Optional[str] = None
    min_confidence: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sequence_contains: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def check_job_access(job: Job, user: TokenData) -> bool:
    """
    Check if user has access to job based on role.

    - Admin: Access to all jobs in organization
    - Researcher/Viewer: Only own jobs
    """
    # Admin can access all jobs in their org
    if user.role == UserRole.ADMIN.value:
        return job.org_id == user.org_id

    # Others can only access their own jobs
    return job.user_id == user.user_id


def apply_role_filter(query, user: TokenData):
    """
    Apply role-based filter to query.

    - Admin: All jobs in organization
    - Researcher/Viewer: Only own jobs
    """
    if user.role == UserRole.ADMIN.value:
        # Admin sees all jobs in their organization
        return query.filter(Job.org_id == user.org_id)
    else:
        # Others see only their own jobs
        return query.filter(Job.user_id == user.user_id)


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    experiment_type: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|status|confidence)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List jobs with pagination and filtering.

    **Access Control:**
    - **Admin**: Sees all jobs in organization
    - **Researcher**: Sees only own jobs
    - **Viewer**: Sees only own jobs (read-only)

    **Filters:**
    - `status`: queued, running, completed, failed
    - `experiment_type`: protein_folding, drug_binding, etc.
    - `method`: alphafold3, esmfold, rosettafold
    - `sort_by`: created_at, status, confidence
    - `sort_order`: asc, desc
    """
    # Base query with role-based access
    query = db.query(Job)
    query = apply_role_filter(query, current_user)

    # Apply filters
    if status:
        query = query.filter(Job.status == status)
    if experiment_type:
        query = query.filter(Job.experiment_type == experiment_type)
    if method:
        query = query.filter(Job.method == method)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Job, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.offset(offset).limit(page_size).all()

    # Convert to response models
    items = []
    for job in jobs:
        # Get user info
        user = db.query(User).filter(User.id == job.user_id).first()

        # Get result if completed
        quality_grade = None
        confidence = None
        if job.result:
            quality_grade = job.result.quality_grade
            confidence = job.result.confidence

        items.append(JobListItem(
            id=job.id,
            status=job.status.value,
            progress=job.progress,
            experiment_type=job.experiment_type,
            method=job.method,
            quality_grade=quality_grade,
            confidence=confidence,
            created_at=job.created_at,
            processing_time_seconds=job.processing_time_seconds,
            user_username=user.username if user else "Unknown"
        ))

    total_pages = (total + page_size - 1) // page_size

    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/jobs/my")
async def list_my_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List current user's jobs only.

    Shortcut for viewing own jobs regardless of role.
    """
    query = db.query(Job).filter(Job.user_id == current_user.user_id)

    total = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(Job.created_at)).offset(offset).limit(page_size).all()

    items = []
    for job in jobs:
        quality_grade = None
        confidence = None
        if job.result:
            quality_grade = job.result.quality_grade
            confidence = job.result.confidence

        items.append(JobListItem(
            id=job.id,
            status=job.status.value,
            progress=job.progress,
            experiment_type=job.experiment_type,
            method=job.method,
            quality_grade=quality_grade,
            confidence=confidence,
            created_at=job.created_at,
            processing_time_seconds=job.processing_time_seconds,
            user_username=current_user.username
        ))

    total_pages = (total + page_size - 1) // page_size

    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/jobs/organization")
async def list_organization_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """
    List all jobs in organization.

    **Admin only** - View all researchers' jobs.
    """
    query = db.query(Job).filter(Job.org_id == current_user.org_id)

    total = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(Job.created_at)).offset(offset).limit(page_size).all()

    items = []
    for job in jobs:
        user = db.query(User).filter(User.id == job.user_id).first()

        quality_grade = None
        confidence = None
        if job.result:
            quality_grade = job.result.quality_grade
            confidence = job.result.confidence

        items.append(JobListItem(
            id=job.id,
            status=job.status.value,
            progress=job.progress,
            experiment_type=job.experiment_type,
            method=job.method,
            quality_grade=quality_grade,
            confidence=confidence,
            created_at=job.created_at,
            processing_time_seconds=job.processing_time_seconds,
            user_username=user.username if user else "Unknown"
        ))

    total_pages = (total + page_size - 1) // page_size

    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(
    job_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed job information.

    **Access Control:**
    - Admin: Any job in organization
    - Researcher/Viewer: Only own jobs
    """
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check access permission
    if not check_job_access(job, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own jobs."
        )

    # Get result if exists
    result_data = None
    if job.result:
        result_data = {
            "quality_grade": job.result.quality_grade,
            "confidence": job.result.confidence,
            "plddt_score": job.result.plddt_score,
            "saxs_chi2": job.result.saxs_chi2,
            "dockq_score": job.result.dockq_score,
            "ove_score": job.result.ove_score,
            "drift_status": job.result.drift_status,
            "pdb_file_path": job.result.pdb_file_path,
            "report_pdf_path": job.result.report_pdf_path,
        }

    return JobDetailResponse(
        id=job.id,
        status=job.status.value,
        progress=job.progress,
        sequence=job.sequence,
        experiment_type=job.experiment_type,
        method=job.method,
        ethics_config=job.ethics_config or {},
        prediction_config=job.prediction_config or {},
        current_stage=job.current_stage,
        stage_index=job.stage_index,
        estimated_time_seconds=job.estimated_time_seconds,
        processing_time_seconds=job.processing_time_seconds,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
        result=result_data
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a running job.

    **Access Control:**
    - Admin: Can cancel any job in organization
    - Researcher: Can only cancel own jobs
    - Viewer: Cannot cancel jobs
    """
    # Viewers cannot cancel jobs
    if current_user.role == UserRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot cancel jobs"
        )

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check access permission
    if not check_job_access(job, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if job can be cancelled
    if job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}"
        )

    # Cancel Celery task
    # TODO: Store celery task_id in Job model
    # revoke_task(job.celery_task_id, terminate=True)

    # Update job status
    job.status = JobStatus.CANCELLED
    db.commit()

    return {
        "message": "Job cancelled successfully",
        "job_id": job_id
    }


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a job and all associated data.

    **Access Control:**
    - Admin: Can delete any job in organization
    - Researcher: Can delete own jobs (only if completed/failed)
    - Viewer: Cannot delete jobs
    """
    # Viewers cannot delete jobs
    if current_user.role == UserRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot delete jobs"
        )

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check access permission
    if not check_job_access(job, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Researchers can only delete completed/failed jobs
    if current_user.role == UserRole.RESEARCHER.value:
        if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete completed, failed, or cancelled jobs"
            )

    # Delete files from storage
    try:
        from app.services.storage_service import delete_job_files
        delete_job_files(job_id)
    except Exception as e:
        # Log error but continue with deletion
        import logging
        logging.error(f"Failed to delete files for job {job_id}: {e}")

    # Delete database records (cascade will handle related records)
    from app.db.models import FileStorage, AuditLog, Result

    db.query(FileStorage).filter(FileStorage.job_id == job_id).delete()
    db.query(AuditLog).filter(AuditLog.job_id == job_id).delete()
    db.query(Result).filter(Result.job_id == job_id).delete()
    db.delete(job)
    db.commit()

    return {
        "message": "Job deleted successfully",
        "job_id": job_id
    }


@router.get("/jobs/search/advanced")
async def advanced_search(
    # Filters
    status: Optional[str] = Query(None),
    experiment_type: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    quality_grade: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    max_confidence: Optional[float] = Query(None, ge=0, le=1),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sequence_contains: Optional[str] = Query(None),

    # Pagination
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),

    # Auth
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Advanced search with multiple filters.

    **Filters:**
    - `status`: queued, running, completed, failed, cancelled
    - `experiment_type`: protein_folding, drug_binding, dna_structure, rna_structure, antibody_design
    - `method`: alphafold3, esmfold, rosettafold
    - `quality_grade`: S, A, B, C, D, F
    - `min_confidence`, `max_confidence`: 0.0 to 1.0
    - `date_from`, `date_to`: ISO datetime
    - `sequence_contains`: Search in sequence text

    **Access Control:**
    - Admin: Search all jobs in organization
    - Researcher/Viewer: Search only own jobs
    """
    # Base query with role-based access
    query = db.query(Job).join(Result, Job.id == Result.job_id, isouter=True)
    query = apply_role_filter(query, current_user)

    # Apply filters
    if status:
        query = query.filter(Job.status == status)

    if experiment_type:
        query = query.filter(Job.experiment_type == experiment_type)

    if method:
        query = query.filter(Job.method == method)

    if quality_grade:
        query = query.filter(Result.quality_grade == quality_grade)

    if min_confidence is not None:
        query = query.filter(Result.confidence >= min_confidence)

    if max_confidence is not None:
        query = query.filter(Result.confidence <= max_confidence)

    if date_from:
        query = query.filter(Job.created_at >= date_from)

    if date_to:
        query = query.filter(Job.created_at <= date_to)

    if sequence_contains:
        query = query.filter(Job.sequence.contains(sequence_contains))

    # Get total
    total = query.count()

    # Pagination
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(Job.created_at)).offset(offset).limit(page_size).all()

    # Convert to response
    items = []
    for job in jobs:
        user = db.query(User).filter(User.id == job.user_id).first()

        quality_grade = None
        confidence = None
        if job.result:
            quality_grade = job.result.quality_grade
            confidence = job.result.confidence

        items.append(JobListItem(
            id=job.id,
            status=job.status.value,
            progress=job.progress,
            experiment_type=job.experiment_type,
            method=job.method,
            quality_grade=quality_grade,
            confidence=confidence,
            created_at=job.created_at,
            processing_time_seconds=job.processing_time_seconds,
            user_username=user.username if user else "Unknown"
        ))

    total_pages = (total + page_size - 1) // page_size

    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

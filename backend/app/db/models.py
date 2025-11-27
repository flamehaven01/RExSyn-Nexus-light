"""
Database Models - RExSyn Nexus Production
==========================================

SQLAlchemy ORM models for all entities.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Enum
)
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
import enum
from app.db.database import Base


# ============================================================================
# Enums
# ============================================================================

class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class JobStatus(str, enum.Enum):
    """Job processing status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QualityGrade(str, enum.Enum):
    """Quality grades."""
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


# ============================================================================
# Models
# ============================================================================

class Organization(Base):
    """
    Organization for multi-tenancy.

    Each organization has isolated data and its own settings.
    """
    __tablename__ = "organizations"

    id = Column(String(50), primary_key=True)  # Fixed: UUIDs fit in 50 chars
    name = Column(Text, nullable=False)  # Changed from String(255): User-provided, no arbitrary limit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Settings
    is_active = Column(Boolean, default=True)
    max_jobs_per_day = Column(Integer, default=100)
    data_retention_days = Column(Integer, default=30)  # 기본 30일, 조정 가능

    # Storage quota (bytes)
    storage_quota = Column(Integer, default=100 * 1024 * 1024 * 1024)  # 100 GB
    storage_used = Column(Integer, default=0)

    # Relationships
    users = relationship("User", back_populates="organization")
    jobs = relationship("Job", back_populates="organization")


class User(Base):
    """
    User model for authentication and authorization.
    """
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)  # Fixed: UUIDs fit in 50 chars
    email = Column(String(320), unique=True, nullable=False, index=True)  # RFC 5321: max email = 320 chars
    username = Column(String(150), unique=True, nullable=False, index=True)  # Reasonable limit for usernames
    hashed_password = Column(String(255), nullable=False)  # Fixed: bcrypt/argon2 hashes fit in 255

    # Profile
    full_name = Column(Text)  # Changed from String(255): User-provided names can be long
    role = Column(Enum(UserRole), default=UserRole.RESEARCHER)

    # Organization
    org_id = Column(String(50), ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="users")

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    jobs = relationship("Job", back_populates="user")


class Job(Base):
    """
    Prediction job - tracks the entire prediction workflow.
    """
    __tablename__ = "jobs"

    id = Column(String(50), primary_key=True)  # e.g., "exp-2024-001"

    # Ownership
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="jobs")

    org_id = Column(String(50), ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="jobs")

    # Status
    # native_enum=False -> store as TEXT (SQLite compatible)
    # Store status as plain text for SQLite compatibility
    status = Column(String(50), default="queued", index=True)
    progress = Column(Float, default=0.0)  # 0.0 to 1.0

    # Input parameters
    sequence = Column(Text, nullable=False)
    experiment_type = Column(String(50), nullable=False)
    method = Column(String(50), nullable=False)  # alphafold3, esmfold, etc.

    # Configuration (stored as JSON)
    ethics_config = Column(JSON)
    prediction_config = Column(JSON)
    metadata_json = Column("metadata", JSON)

    # Processing info
    current_stage = Column(String(100))
    stage_index = Column(Integer, default=0)
    total_stages = Column(Integer, default=7)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Estimated and actual times
    estimated_time_seconds = Column(Integer)
    processing_time_seconds = Column(Integer)

    # Error info
    error_message = Column(Text)
    error_traceback = Column(Text)
    retry_count = Column(Integer, default=0)

    # Data retention (auto-delete after this date)
    expires_at = Column(DateTime(timezone=True), index=True)

    # Relationships
    result = relationship("Result", back_populates="job", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="job")
    files = relationship("FileStorage", back_populates="job")


Job.metadata = synonym("metadata_json")


class Result(Base):
    """
    Prediction result - stores final output and metrics.
    """
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey("jobs.id"), unique=True, nullable=False)
    job = relationship("Job", back_populates="result")

    # Quality metrics
    # Store as TEXT for SQLite compatibility
    # Store grade as text for SQLite compatibility
    quality_grade = Column(String(2))
    confidence = Column(Float)
    plddt_score = Column(Float)
    plddt_array = Column(JSON)  # Per-residue scores

    # Validation metrics
    saxs_chi2 = Column(Float)
    dockq_score = Column(Float)

    # PoseBusters checks (JSON object)
    posebuster_checks = Column(JSON)

    # Ethics certification
    ove_score = Column(Float)
    drift_status = Column(String(50))
    policy_compliance = Column(String(50))

    # Processing flags
    md_refinement_applied = Column(Boolean, default=False)

    # File references (S3/MinIO paths)
    pdb_file_path = Column(String(500))
    refined_pdb_file_path = Column(String(500))
    report_pdf_path = Column(String(500))
    audit_trail_path = Column(String(500))

    # Graph data (stored as JSON for quick access)
    graph_data = Column(JSON)  # {plddt: [], saxs: {}, md_trajectory: {}, ...}

    # Metrics for quality radar
    metrics = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditLog(Base):
    """
    SIDRCE audit trail - records every stage of the ethics pipeline.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey("jobs.id"), nullable=False, index=True)
    job = relationship("Job", back_populates="audit_logs")

    # Stage info
    stage_name = Column(String(100), nullable=False)
    stage_index = Column(Integer)

    # Status
    status = Column(String(50))  # started, completed, failed

    # Metrics and results
    metrics = Column(JSON)
    checks = Column(JSON)
    warnings = Column(JSON)

    # Ethics scores
    ove_score = Column(Float)
    drift_detected = Column(Boolean)
    policy_violations = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)

    # Logs
    log_messages = Column(JSON)  # Array of log entries

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FileStorage(Base):
    """
    File metadata for S3/MinIO storage.

    Tracks all files associated with jobs for cleanup and quota management.
    """
    __tablename__ = "file_storage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey("jobs.id"), nullable=False, index=True)
    job = relationship("Job", back_populates="files")

    # File info
    file_type = Column(String(50), nullable=False)  # Fixed: Controlled values (pdb, pdf, fasta, etc.)
    file_path = Column(Text, nullable=False)  # Changed from String(500): S3 paths can be very long
    file_name = Column(Text, nullable=False)  # Changed from String(255): User filenames can be long

    # Size and checksums
    file_size = Column(Integer)  # bytes
    md5_hash = Column(String(32))  # Fixed: MD5 hashes are exactly 32 hex chars
    sha256_hash = Column(String(64))  # Fixed: SHA256 hashes are exactly 64 hex chars

    # Metadata
    mime_type = Column(String(127))  # RFC 6838: MIME types max ~127 chars
    description = Column(Text)

    # Access control
    is_public = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)

    # Retention
    expires_at = Column(DateTime(timezone=True), index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True))


class SystemConfig(Base):
    """
    System-wide configuration key-value store.

    Allows runtime configuration without code changes.
    """
    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    description = Column(Text)

    # Metadata
    category = Column(String(50))  # retention, limits, features, etc.
    is_secret = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(50))  # user_id


# ============================================================================
# Helper functions - DEPRECATED
# ============================================================================
#
# NOTE: These functions have been moved to JobService for better separation
# of concerns (Single Responsibility Principle).
#
# Use instead:
#   from app.services.job_service import JobService
#   service = JobService(db)
#   service.calculate_expiration(created_at, retention_days)
#   service.should_expire(job)
#
# These functions are kept here temporarily for backward compatibility
# and will be removed in v0.5.0.
#

def calculate_job_expiration(created_at: datetime, retention_days: int = 30) -> datetime:
    """
    Calculate when a job should be deleted.

    DEPRECATED: Use JobService.calculate_expiration() instead.

    Default: 30 days from creation, but configurable per organization.
    """
    import warnings
    warnings.warn(
        "calculate_job_expiration() is deprecated. "
        "Use JobService.calculate_expiration() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return created_at + timedelta(days=retention_days)


def should_delete_job(job: Job) -> bool:
    """
    Check if a job should be deleted based on expiration.

    DEPRECATED: Use JobService.should_expire() instead.
    """
    import warnings
    warnings.warn(
        "should_delete_job() is deprecated. "
        "Use JobService.should_expire() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    if job.expires_at is None:
        return False
    return datetime.now(timezone.utc) >= job.expires_at

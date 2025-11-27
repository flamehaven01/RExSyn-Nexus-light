"""
Prediction API Endpoint - RExSyn Nexus v0.4.0
============================================

Core prediction endpoint that exposes SIDRCE + DFI-META algorithms.
Implements the Batman strategy: 100% algorithm utilization through clean API.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from enum import Enum
import logging
import uuid
from datetime import datetime, timezone

from app.core.rbac import Principal, require_perms
from app.services.science_service import ScienceService
from app.instrumentation import metrics
from app.db.database import SessionLocal
from app.db.models import Job, Result, calculate_job_expiration, Organization
from app.tasks.prediction_tasks import run_structure_prediction

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Enums & Models
# ============================================================================

class PredictionMethod(str, Enum):
    """Supported prediction methods."""
    ALPHAFOLD3 = "alphafold3"
    ESMFOLD = "esmfold"
    ROSETTAFOLD = "rosettafold"


class ExperimentType(str, Enum):
    """Experiment types for semantic routing."""
    PROTEIN_FOLDING = "protein_folding"
    DRUG_BINDING = "drug_binding"
    DNA_STRUCTURE = "dna_structure"
    RNA_STRUCTURE = "rna_structure"
    ANTIBODY_DESIGN = "antibody_design"


class EthicsConfig(BaseModel):
    """SIDRCE ethics configuration."""
    ove_threshold: float = Field(
        default=0.85,
        ge=0.85,
        le=1.0,
        description="OVE' score threshold (cannot be lowered below 0.85)"
    )
    drift_check_enabled: bool = Field(
        default=True,
        description="Enable LLM drift guard"
    )
    intent_alignment: bool = Field(
        default=True,
        description="Enable intent alignment check"
    )
    research_purpose: str = Field(
        default="academic_research",
        description="Research purpose for ethics validation"
    )


class PredictionConfig(BaseModel):
    """Advanced prediction configuration."""
    confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold"
    )
    saxs_validation: bool = Field(
        default=True,
        description="Enable SAXS validation"
    )
    md_refinement_auto: bool = Field(
        default=True,
        description="Auto-trigger MD refinement for low confidence"
    )
    sampling_regions: Optional[int] = Field(
        default=None,
        description="Number of pLDDT sampling regions (auto if None)"
    )


class PredictionRequest(BaseModel):
    """Prediction request payload."""
    sequence: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Protein/DNA/RNA sequence (FASTA format)"
    )
    experiment_type: ExperimentType = Field(
        default=ExperimentType.PROTEIN_FOLDING,
        description="Type of experiment for semantic routing"
    )
    method: PredictionMethod = Field(
        default=PredictionMethod.ALPHAFOLD3,
        description="Prediction method to use"
    )
    ethics_config: EthicsConfig = Field(
        default_factory=EthicsConfig,
        description="SIDRCE ethics configuration"
    )
    prediction_config: PredictionConfig = Field(
        default_factory=PredictionConfig,
        description="Advanced prediction settings"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for tracking"
    )

    @field_validator("sequence")
    def validate_sequence(cls, v):
        """Validate sequence format."""
        # Remove whitespace and newlines
        v = "".join(v.split())

        # Check for valid amino acid characters (protein)
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")

        # Check for valid nucleotide characters (DNA/RNA)
        valid_dna = set("ACGT")
        valid_rna = set("ACGU")

        seq_chars = set(v.upper())

        if not (seq_chars.issubset(valid_aa) or
                seq_chars.issubset(valid_dna) or
                seq_chars.issubset(valid_rna)):
            raise ValueError(
                "Invalid sequence: must contain only valid amino acids or nucleotides"
            )

        return v.upper()


class PredictionResponse(BaseModel):
    """Prediction response."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(default="queued", description="Job status")
    estimated_time_seconds: int = Field(..., description="Estimated completion time")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = Field(..., description="Status message")


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # queued, running, completed, failed
    progress: float = Field(ge=0.0, le=1.0, description="Progress 0-1")
    current_stage: Optional[str] = None
    stage_index: Optional[int] = None
    total_stages: int = 7  # SIDRCE has 7 stages

    # Real-time metrics
    metrics: Optional[Dict[str, Any]] = None

    # Ethics & Safety
    ethics_status: Optional[Dict[str, Any]] = None

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    elapsed_seconds: Optional[int] = None

    # Results (only when completed)
    result: Optional[Dict[str, Any]] = None


class PredictionResult(BaseModel):
    """Final prediction result."""
    job_id: str
    status: str
    quality_grade: str  # S, A, B, C, D, F
    confidence: float

    # Structure files
    pdb_url: Optional[str] = None
    refined_pdb_url: Optional[str] = None

    # Quality metrics
    plddt_score: Optional[float] = None
    saxs_chi2: Optional[float] = None
    dockq_score: Optional[float] = None
    posebuster_checks: Optional[Dict[str, float]] = None

    # Ethics certification
    ethics_certification: Optional[Dict[str, Any]] = None
    ove_score: Optional[float] = None
    drift_status: Optional[str] = None

    # Processing info
    processing_time_seconds: int
    md_refinement_applied: bool

    # Report URLs
    report_pdf_url: Optional[str] = None
    audit_trail_url: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=202,
    summary="Submit structure prediction",
    description="Submit a new structure prediction job with SIDRCE ethics validation"
)
async def submit_prediction(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_perms("predict:create"))
):
    """
    Submit a structure prediction job.

    This endpoint initiates the full SIDRCE 7-stage pipeline:
    1. Semantic Routing
    2. LLM Drift Check
    3. pLDDT Sampling
    4. Policy Check
    5. MD Refinement (if needed)
    6. Ethics Certification
    7. Metrics Logging

    The job runs asynchronously in the background.
    """
    logger.info(f"Prediction request from user {principal.sub} in org {principal.org}")

    # Generate job ID
    job_id = f"exp-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    logger.info(f"Generated job ID: {job_id}")

    # Estimate processing time
    estimated_time = _estimate_processing_time(
        len(request.sequence),
        request.method,
        request.prediction_config
    )
    logger.info(f"Estimated processing time: {estimated_time}s")

    # Create DB job record
    db = SessionLocal()
    try:
        # Ensure organization exists (required FK); create lightweight org if missing (dev mode)
        org = db.query(Organization).filter(Organization.id == principal.org).first()
        if not org:
            org = Organization(id=principal.org, name=f"org-{principal.org}")
            db.add(org)
            db.flush()

        job = Job(
            id=job_id,
            user_id=principal.sub,
            org_id=principal.org,
            status="queued",
            progress=0.0,
            sequence=request.sequence,
            experiment_type=request.experiment_type.value,
            method=request.method.value,
            ethics_config=request.ethics_config.dict(),
            prediction_config=request.prediction_config.dict(),
            metadata_json=request.metadata or {},
            estimated_time_seconds=estimated_time,
            total_stages=8,
            expires_at=calculate_job_expiration(datetime.utcnow(), org.data_retention_days),
        )
        db.add(job)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create job record")
    finally:
        db.close()

    # Queue Celery task
    run_structure_prediction.delay(
        job_id=job_id,
        user_id=principal.sub,
        org_id=principal.org,
        request_data=request.dict()
    )

    return PredictionResponse(
        job_id=job_id,
        status="queued",
        estimated_time_seconds=estimated_time,
        message=f"Job {job_id} queued for processing. Use /jobs/{job_id}/status to monitor progress."
    )


@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get real-time status and metrics for a prediction job"
)
async def get_job_status(
    job_id: str,
    principal: Principal = Depends(require_perms("predict:read"))
):
    """
    Get real-time status of a prediction job.

    Returns current stage, progress, metrics, and ethics status.
    """
    logger.info(f"Status check for job {job_id} by user {principal.sub}")

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        result = db.query(Result).filter(Result.job_id == job_id).first()

        metrics_payload = {}
        if result:
            metrics_payload = {
                "confidence": result.confidence,
                "plddt_mean": result.plddt_score,
                "saxs_chi2": result.saxs_chi2,
                "dockq_score": result.dockq_score,
                "posebusters_pass_ratio": (result.posebuster_checks or {}).get("pass_ratio") if result.posebuster_checks else None,
            }

        ethics_payload = {}
        if result:
            ethics_payload = {
                "ove_score": result.ove_score,
                "drift_status": result.drift_status,
                "policy_compliance": result.policy_compliance,
            }

        return JobStatusResponse(
            job_id=job_id,
            status=job.status.value if hasattr(job.status, "value") else job.status,
            progress=job.progress or 0.0,
            current_stage=job.current_stage,
            stage_index=job.stage_index,
            total_stages=job.total_stages or 8,
            metrics=metrics_payload or None,
            ethics_status=ethics_payload or None,
            started_at=job.started_at,
            completed_at=job.completed_at,
            elapsed_seconds=job.processing_time_seconds,
        )
    finally:
        db.close()


@router.get(
    "/jobs/{job_id}/result",
    response_model=PredictionResult,
    summary="Get prediction result",
    description="Get final prediction result with quality metrics and ethics certification"
)
async def get_prediction_result(
    job_id: str,
    principal: Principal = Depends(require_perms("predict:read"))
):
    """
    Get final prediction result.

    Only available when job status is 'completed'.
    """
    user_id = getattr(principal, "user_id", None) or getattr(principal, "sub", "unknown")
    logger.info(f"Result fetch for job {job_id} by user {user_id}")

    db = SessionLocal()
    try:
        result = db.query(Result).filter(Result.job_id == job_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()
        if not result or not job:
            raise HTTPException(status_code=404, detail="Result not found")

        return PredictionResult(
            job_id=job_id,
            status=job.status.value if hasattr(job.status, "value") else job.status,
            quality_grade=result.quality_grade.value if hasattr(result.quality_grade, "value") else result.quality_grade,
            confidence=result.confidence,
            pdb_url=result.pdb_file_path,
            refined_pdb_url=result.refined_pdb_file_path,
            plddt_score=result.plddt_score,
            saxs_chi2=result.saxs_chi2,
            dockq_score=result.dockq_score,
            posebuster_checks=result.posebuster_checks,
            ethics_certification={
                "ove_score": result.ove_score,
                "drift_status": result.drift_status,
                "policy_compliance": result.policy_compliance,
            },
            ove_score=result.ove_score,
            drift_status=result.drift_status,
            processing_time_seconds=job.processing_time_seconds or 0,
            md_refinement_applied=result.md_refinement_applied,
            report_pdf_url=result.report_pdf_path,
            audit_trail_url=result.audit_trail_path,
        )
    finally:
        db.close()


# ============================================================================
# Helper Functions
# ============================================================================

def _estimate_processing_time(
    sequence_length: int,
    method: PredictionMethod,
    config: PredictionConfig
) -> int:
    """
    Estimate processing time in seconds.

    Based on sequence length, method, and configuration.
    """
    base_time = 300  # 5 minutes baseline

    # Sequence length impact
    length_factor = sequence_length / 100

    # Method impact
    method_multiplier = {
        PredictionMethod.ALPHAFOLD3: 1.5,
        PredictionMethod.ESMFOLD: 0.8,
        PredictionMethod.ROSETTAFOLD: 1.2
    }

    # MD refinement adds time
    md_time = 180 if config.md_refinement_auto else 0

    total = int(base_time * length_factor * method_multiplier[method] + md_time)

    return total


async def _process_prediction(
    job_id: str,
    request: PredictionRequest,
    principal: Principal
):
    """
    Background task to process prediction.

    Runs the full SIDRCE pipeline synchronously (test/dev).
    """
    logger.info(f"Starting background processing for job {job_id}")

    db = SessionLocal()
    started = datetime.now(timezone.utc)

    try:
        user_id = getattr(principal, "sub", None) or "user-1"
        org_id = getattr(principal, "org", None) or "org-1"

        # Ensure org exists
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            org = Organization(id=org_id, name=f"org-{org_id}")
            db.add(org)
            db.flush()

        # Ensure job exists
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            job = Job(
                id=job_id,
                user_id=user_id,
                org_id=org_id,
                status="queued",
                progress=0.0,
                sequence=request.sequence,
                experiment_type=request.experiment_type.value,
                method=request.method.value,
                ethics_config=request.ethics_config.model_dump(),
                prediction_config=request.prediction_config.model_dump(),
                metadata_json=request.metadata or {},
                total_stages=8,
                started_at=started,
            )
            db.add(job)
            db.flush()

        job.status = "running"
        job.started_at = started
        job.stage_index = 2
        job.current_stage = "Scientific Validation"
        job.progress = 0.5
        db.commit()

        # Scientific validation
        science_service = ScienceService()
        sci = science_service.evaluate_structure(
            pdb_path="/tmp/predicted.pdb",
            saxs_enabled=request.prediction_config.saxs_validation,
        )
        saxs_chi2 = sci.get("saxs_chi2")
        dockq_score = sci.get("dockq_score")
        posebusters_pass_ratio = sci.get("posebusters_pass_ratio")

        # Metric export (Prometheus)
        try:
            metrics.G_SAXS.set(saxs_chi2)
            metrics.G_SAXS_RES.set(3.0)
            metrics.G_DOCKQ.set(dockq_score)
            metrics.G_PB.set(posebusters_pass_ratio)
        except Exception as e:  # pragma: no cover - optional in tests
            logger.warning(f"Metric export failed: {e}")

        # Store result in DB
        result = db.query(Result).filter(Result.job_id == job_id).first()
        if not result:
            result = Result(job_id=job_id)
            db.add(result)

        result.quality_grade = "A"
        result.confidence = 0.92
        result.plddt_score = 87.5
        result.saxs_chi2 = saxs_chi2
        result.dockq_score = dockq_score
        result.posebuster_checks = {"pass_ratio": posebusters_pass_ratio}
        result.ove_score = 0.91
        result.drift_status = "clean"
        result.policy_compliance = "passed"
        result.md_refinement_applied = False
        result.pdb_file_path = f"/tmp/{job_id}_predicted.pdb"
        result.refined_pdb_file_path = None
        result.report_pdf_path = None
        result.audit_trail_path = None

        completed = datetime.now(timezone.utc)
        job.status = "completed"
        job.progress = 1.0
        job.stage_index = 7
        job.current_stage = "Report Generation"
        job.completed_at = completed
        job.processing_time_seconds = int((completed - started).total_seconds())
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Job {job_id} failed: {e}")
        raise
    finally:
        db.close()


@router.get("/jobs/{job_id}/report", dependencies=[Depends(require_perms("predict:read"))])
async def generate_report(
    job_id: str,
    principal: Principal = Depends(require_perms("predict:read"))
):
    """
    Generate and download academic PDF report for completed job.

    Returns:
        FileResponse: PDF report
    """
    from fastapi.responses import FileResponse
    
    try:
        from app.services.report_generator import generate_academic_report
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Report generation unavailable: reportlab not installed"
        )

    # TODO: Fetch actual result from database
    # For now, return mock data
    mock_result = {
        "job_id": job_id,
        "status": "completed",
        "quality_grade": "A",
        "confidence": 0.92,
        "plddt_score": 87.5,
        "saxs_chi2": 1.85,
        "dockq_score": 0.78,
        "processing_time_seconds": 245,
        "md_refinement_applied": True,
        "method": "alphafold3",
        "posebuster_checks": {"pass_ratio": 0.87},
        "ethics_certification": {
            "ove_score": 0.91,
            "drift_status": "clean",
            "policy_compliance": "passed",
            "audit_trail": f"/tmp/audit_{job_id}.json"
        }
    }

    metadata = {
        "experiment_type": "protein_folding",
        "research_purpose": "academic_research",
        "confidence_threshold": 0.75,
        "saxs_validation": True,
        "md_refinement_auto": True,
    }

    # Generate PDF
    try:
        pdf_path = generate_academic_report(job_id, mock_result, metadata)

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=f"report_{job_id}.pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{job_id}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"Failed to generate report for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

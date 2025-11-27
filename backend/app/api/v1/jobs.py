from fastapi import APIRouter, Depends, HTTPException
from app.core.rbac import Principal, require_perms
from app.services.pii_service import PIIService

router = APIRouter()

@router.delete("/jobs/{job_id}/pii", dependencies=[Depends(require_perms("pii:delete"))])
async def delete_pii(job_id: str, principal: Principal = Depends(require_perms("pii:delete"))):
    try:
        with PIIService() as svc:
            result = svc.cascade_delete(job_id, principal.org)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "job_id": job_id,
        "deleted_artifacts": result["artifact_count"],
        "deleted_mlflow_run": result["mlflow_deleted"],
        "deleted_minio_objects": result["minio_deleted"],
        "audit_hash": result["audit_hash"]
    }

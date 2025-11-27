"""
WebSocket Endpoint for Real-time Job Updates
=============================================

Provides real-time streaming of job status, metrics, and safety alerts.
Batman strategy: Instant feedback loop between brain (algorithm) and body (UI).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging
import json
import asyncio
from datetime import datetime
from fastapi import Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from app.services.auth_service import decode_token, TokenData
from app.db.database import get_db
from app.db.models import Job


logger = logging.getLogger(__name__)


router = APIRouter()


async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(...)
) -> TokenData:
    """
    Authenticate WebSocket connection via query parameter.
    """
    token_data = decode_token(token)
    if token_data is None:
        # WebSocket close codes: 1008 = Policy Violation
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    return token_data



class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Implements pub/sub pattern: jobs publish updates, clients subscribe to specific jobs.
    """

    def __init__(self):
        # job_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept and track a new WebSocket connection."""
        await websocket.accept()

        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()

        self.active_connections[job_id].add(websocket)
        logger.info(f"Client connected to job {job_id}. Total connections: {len(self.active_connections[job_id])}")

    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove a WebSocket connection."""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)

            # Clean up empty sets
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

            logger.info(f"Client disconnected from job {job_id}")

    async def broadcast_to_job(self, job_id: str, message: dict):
        """
        Broadcast a message to all clients watching a specific job.

        Args:
            job_id: Job identifier
            message: Message payload (will be JSON serialized)
        """
        if job_id not in self.active_connections:
            return

        # Add timestamp
        message["timestamp"] = datetime.utcnow().isoformat()

        # Serialize message
        message_json = json.dumps(message)

        # Send to all connected clients
        disconnected = set()
        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, job_id)

    async def send_status_update(
        self,
        job_id: str,
        status: str,
        progress: float,
        stage: str,
        metrics: dict = None,
        ethics_status: dict = None
    ):
        """Send a status update to all clients watching this job."""
        message = {
            "type": "status_update",
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "stage": stage,
            "metrics": metrics or {},
            "ethics_status": ethics_status or {}
        }
        await self.broadcast_to_job(job_id, message)

    async def send_alert(self, job_id: str, level: str, message: str):
        """Send a safety alert."""
        alert = {
            "type": "alert",
            "job_id": job_id,
            "level": level,  # info, warning, error
            "message": message
        }
        await self.broadcast_to_job(job_id, alert)

    async def send_log(self, job_id: str, log_entry: str):
        """Send a log entry to activity feed."""
        log_message = {
            "type": "log",
            "job_id": job_id,
            "entry": log_entry
        }
        await self.broadcast_to_job(job_id, log_message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: str,
    user: TokenData = Depends(get_current_user_ws),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time job updates.

    Usage:
        ws = new WebSocket("ws://localhost:8000/api/v1/ws/jobs/exp-2024-001");
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Update:", data);
        };

    Message Types:
        - status_update: Job status, progress, metrics
        - alert: Safety alerts (info/warning/error)
        - log: Activity log entries
        - completed: Job finished
        - error: Job failed
    """
    logger.info(f"WebSocket connection requested for job {job_id} by user {user.username}")

    # Verify Job Ownership / Tenant Isolation
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Tenant Check: User's Org ID must match Job's Org ID
    if job.org_id != user.org_id:
        logger.warning(f"Tenant violation: User {user.username} ({user.org_id}) tried to access job {job_id} ({job.org_id})")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, job_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "message": f"Connected to job {job_id}. You will receive real-time updates."
        })

        # Keep connection alive and handle client messages
        while True:
            # Wait for client messages (ping/pong, subscriptions, etc.)
            data = await websocket.receive_text()

            # Echo back for debugging (optional)
            logger.debug(f"Received from client: {data}")

            # Client can send commands (future enhancement)
            # For now, just acknowledge
            await websocket.send_json({
                "type": "ack",
                "received": data
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
        logger.info(f"Client disconnected from job {job_id}")

    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        manager.disconnect(websocket, job_id)


# ============================================================================
# Helper Functions for Background Tasks
# ============================================================================

async def publish_job_update(
    job_id: str,
    status: str,
    progress: float,
    stage: str,
    metrics: dict = None,
    ethics_status: dict = None
):
    """
    Publish a job update to all connected clients.

    Called from background tasks during job processing.
    """
    await manager.send_status_update(
        job_id=job_id,
        status=status,
        progress=progress,
        stage=stage,
        metrics=metrics,
        ethics_status=ethics_status
    )


async def publish_alert(job_id: str, level: str, message: str):
    """Publish a safety alert."""
    await manager.send_alert(job_id, level, message)


async def publish_log(job_id: str, log_entry: str):
    """Publish a log entry."""
    await manager.send_log(job_id, log_entry)


# ============================================================================
# Example: Simulated Job Progress (for testing)
# ============================================================================

async def simulate_job_progress(job_id: str):
    """
    Simulate a job with real-time updates.

    This is for testing/demo purposes.
    In production, the actual prediction pipeline will call publish_job_update().
    """
    stages = [
        ("semantic_routing", "Semantic Routing"),
        ("drift_check", "LLM Drift Check"),
        ("sampling", "pLDDT Sampling"),
        ("prediction", "Structure Prediction"),
        ("md_refinement", "MD Refinement"),
        ("certification", "Ethics Certification"),
        ("reporting", "Report Generation")
    ]

    for idx, (stage_key, stage_name) in enumerate(stages):
        progress = (idx + 1) / len(stages)

        # Simulate metrics improving over time
        metrics = {
            "confidence": min(0.95, 0.6 + progress * 0.35),
            "plddt_mean": min(95.0, 70.0 + progress * 25.0),
            "saxs_chi2": max(1.2, 3.0 - progress * 1.8)
        }

        ethics_status = {
            "ove_score": min(0.98, 0.85 + progress * 0.13),
            "drift_detected": False,
            "policy_violations": 0
        }

        await publish_job_update(
            job_id=job_id,
            status="running",
            progress=progress,
            stage=stage_key,
            metrics=metrics,
            ethics_status=ethics_status
        )

        await publish_log(job_id, f"✅ {stage_name} completed")

        # Simulate processing time
        await asyncio.sleep(2)

    # Final completion
    await publish_job_update(
        job_id=job_id,
        status="completed",
        progress=1.0,
        stage="completed",
        metrics={"confidence": 0.968, "quality_grade": "S"},
        ethics_status={"ove_score": 0.95, "drift_detected": False}
    )

    await publish_log(job_id, "🎉 Prediction completed successfully!")

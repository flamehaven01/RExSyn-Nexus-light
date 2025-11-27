"""
Digital Empathy API
===================

Collects and analyzes user pain metrics for continuous UX improvement.

Pain Metrics:
- Rage-Click Score: Repeated frustration clicks
- Hesitation Rate: Time delay before input
- Workflow Abandonment: Incomplete task flows
- Time-to-Value: Login to first result
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import logging

from app.db.session import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/empathy", tags=["empathy"])


# ============================================================================
# Models
# ============================================================================

class UserInteractionEvent(BaseModel):
    """Single user interaction event."""
    type: Literal["click", "input", "focus", "blur", "navigation", "error"]
    timestamp: int  # Unix timestamp in ms
    element: str
    element_id: Optional[str] = None
    value: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PainMetrics(BaseModel):
    """Quantified user pain metrics."""
    rage_click_score: float = Field(..., ge=0, le=100, description="0-100, higher = more frustration")
    hesitation_rate: float = Field(..., ge=0, description="Average ms delay before typing")
    abandonment_rate: float = Field(..., ge=0, le=100, description="% of incomplete workflows")
    time_to_value: Optional[int] = Field(None, description="ms from login to first result")
    error_encounters: int = Field(..., ge=0, description="Count of errors seen")


class EmpathyEventPayload(BaseModel):
    """Batch of user events with computed metrics."""
    events: List[UserInteractionEvent]
    metrics: PainMetrics
    session_id: str
    timestamp: int
    user_id: Optional[str] = None


class EmpathyGateDecision(BaseModel):
    """Decision from empathy gate for deployment blocking."""
    should_block: bool
    reason: Optional[str] = None
    metrics: PainMetrics
    thresholds: Dict[str, float]


# ============================================================================
# Thresholds for Empathy Gate
# ============================================================================

EMPATHY_GATE_THRESHOLDS = {
    "rage_click_score": 20.0,      # Block if > 20
    "hesitation_rate": 5000.0,     # Block if > 5s average
    "abandonment_rate": 30.0,      # Block if > 30%
    "error_encounters": 5,         # Block if > 5 errors
}


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/events", status_code=201)
async def collect_empathy_events(
    payload: EmpathyEventPayload,
    db: Session = Depends(get_db),
):
    """
    Collect user interaction events and pain metrics.

    This endpoint is called by the frontend empathy engine
    to send batches of user interaction data.
    """
    logger.info(f"📊 Empathy events received: session={payload.session_id}")

    # Log metrics for analysis
    metrics = payload.metrics
    logger.info(
        f"Pain Metrics - "
        f"RageClick: {metrics.rage_click_score:.1f}, "
        f"Hesitation: {metrics.hesitation_rate:.0f}ms, "
        f"Abandonment: {metrics.abandonment_rate:.1f}%, "
        f"Errors: {metrics.error_encounters}"
    )

    # Check for critical pain indicators
    if metrics.rage_click_score > 30:
        logger.warning(f"🔥 High rage-click score detected: {metrics.rage_click_score}")

    if metrics.abandonment_rate > 50:
        logger.warning(f"🚪 High abandonment rate: {metrics.abandonment_rate}%")

    if metrics.error_encounters > 10:
        logger.error(f"❌ Excessive errors encountered: {metrics.error_encounters}")

    # TODO: Store in database for historical analysis
    # For now, just log and acknowledge

    return {
        "status": "received",
        "session_id": payload.session_id,
        "event_count": len(payload.events),
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/gate/check", response_model=EmpathyGateDecision)
async def check_empathy_gate(
    metrics: PainMetrics,
):
    """
    Check if deployment should be blocked based on pain metrics.

    This is called by CI/CD pipeline to validate that new
    frontend builds don't degrade user experience.

    **Empathy Gate Thresholds:**
    - Rage-Click Score: ≤20
    - Hesitation Rate: ≤5000ms (5s)
    - Abandonment Rate: ≤30%
    - Error Encounters: ≤5
    """
    violations = []

    if metrics.rage_click_score > EMPATHY_GATE_THRESHOLDS["rage_click_score"]:
        violations.append(
            f"Rage-click score {metrics.rage_click_score:.1f} exceeds threshold "
            f"{EMPATHY_GATE_THRESHOLDS['rage_click_score']}"
        )

    if metrics.hesitation_rate > EMPATHY_GATE_THRESHOLDS["hesitation_rate"]:
        violations.append(
            f"Hesitation rate {metrics.hesitation_rate:.0f}ms exceeds threshold "
            f"{EMPATHY_GATE_THRESHOLDS['hesitation_rate']:.0f}ms"
        )

    if metrics.abandonment_rate > EMPATHY_GATE_THRESHOLDS["abandonment_rate"]:
        violations.append(
            f"Abandonment rate {metrics.abandonment_rate:.1f}% exceeds threshold "
            f"{EMPATHY_GATE_THRESHOLDS['abandonment_rate']}%"
        )

    if metrics.error_encounters > EMPATHY_GATE_THRESHOLDS["error_encounters"]:
        violations.append(
            f"Error encounters {metrics.error_encounters} exceeds threshold "
            f"{EMPATHY_GATE_THRESHOLDS['error_encounters']}"
        )

    should_block = len(violations) > 0
    reason = "; ".join(violations) if should_block else None

    if should_block:
        logger.error(f"🚫 Empathy gate BLOCKED deployment: {reason}")
    else:
        logger.info("✅ Empathy gate PASSED")

    return EmpathyGateDecision(
        should_block=should_block,
        reason=reason,
        metrics=metrics,
        thresholds=EMPATHY_GATE_THRESHOLDS,
    )


@router.get("/metrics/summary")
async def get_empathy_metrics_summary(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    days: int = 7,
):
    """
    Get summary of empathy metrics over time.

    Useful for dashboards and historical analysis.
    """
    # TODO: Query database for historical metrics
    # For now, return mock data

    return {
        "summary": {
            "avg_rage_click_score": 5.2,
            "avg_hesitation_rate": 2100,
            "avg_abandonment_rate": 12.5,
            "avg_time_to_value": 45000,
            "total_sessions": 150,
            "blocked_deployments": 2,
        },
        "period": f"Last {days} days",
        "filters": {
            "session_id": session_id,
            "user_id": user_id,
        },
    }


@router.get("/health")
async def empathy_health():
    """Health check for empathy tracking system."""
    return {
        "status": "healthy",
        "empathy_gate_enabled": True,
        "thresholds": EMPATHY_GATE_THRESHOLDS,
    }


# ============================================================================
# Helper: Analyze Specific Pain Patterns
# ============================================================================

def analyze_pain_patterns(events: List[UserInteractionEvent]) -> Dict[str, Any]:
    """
    Deep analysis of user pain patterns from event stream.

    Returns:
        Dictionary with identified pain points and recommendations.
    """
    analysis = {
        "rage_click_elements": [],
        "high_hesitation_fields": [],
        "abandoned_workflows": [],
        "error_prone_actions": [],
        "recommendations": [],
    }

    # Track element-level issues
    element_clicks: Dict[str, int] = {}
    element_errors: Dict[str, int] = {}

    for event in events:
        if event.type == "click":
            element_clicks[event.element] = element_clicks.get(event.element, 0) + 1
        elif event.type == "error":
            element_errors[event.element] = element_errors.get(event.element, 0) + 1

    # Identify rage-click hotspots
    for element, count in element_clicks.items():
        if count >= 3:
            analysis["rage_click_elements"].append({
                "element": element,
                "click_count": count,
            })

    # Identify error-prone elements
    for element, count in element_errors.items():
        if count >= 2:
            analysis["error_prone_actions"].append({
                "element": element,
                "error_count": count,
            })

    # Generate recommendations
    if analysis["rage_click_elements"]:
        analysis["recommendations"].append(
            "Consider improving clickability/responsiveness of frequently rage-clicked elements"
        )

    if analysis["error_prone_actions"]:
        analysis["recommendations"].append(
            "Add better error handling and user guidance for error-prone actions"
        )

    return analysis

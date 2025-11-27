"""
API v1 Router - RExSyn Nexus v0.5.0
===================================

Central router for all v1 API endpoints.
Batman strategy: Clean API that exposes 100% of algorithm power.
"""

from fastapi import APIRouter
from app.api.v1 import predict, jobs, job_management, websocket, empathy

api_router = APIRouter()

# Prediction endpoints (core functionality)
api_router.include_router(
    predict.router,
    tags=["Prediction"]
)

# Job management endpoints (RBAC-based)
api_router.include_router(
    job_management.router,
    tags=["Job Management"]
)

# Legacy PII deletion endpoint
api_router.include_router(
    jobs.router,
    tags=["Jobs (Legacy)"]
)

# WebSocket for real-time updates
api_router.include_router(
    websocket.router,
    tags=["Real-time"]
)

# Digital Empathy Engine - User experience tracking
api_router.include_router(
    empathy.router,
    tags=["User Experience"]
)

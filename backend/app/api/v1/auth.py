"""
Authentication API Endpoints
=============================

Login, registration, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.db.database import get_db
from app.db.models import User, Organization, UserRole
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_token_pair,
    decode_token,
    get_current_user,
    TokenData,
    TokenPair,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    organization_name: str = Field(default="Default Organization")


class LoginRequest(BaseModel):
    """User login request."""
    username_or_email: str
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user and organization.

    Creates both user and organization (for self-service signup).
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    # Create organization
    org_id = f"org-{uuid.uuid4().hex[:12]}"
    organization = Organization(
        id=org_id,
        name=request.organization_name,
        is_active=True,
        data_retention_days=30,  # Default 30 days
    )
    db.add(organization)

    # Hash password
    hashed_password = hash_password(request.password)

    # Create user
    user_id = f"user-{uuid.uuid4().hex[:12]}"
    user = User(
        id=user_id,
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        role=UserRole.RESEARCHER,  # Default role
        org_id=org_id,
        is_active=True,
        is_verified=False,  # Email verification can be added later
    )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
        db.refresh(organization)

        logger.info(f"New user registered: {user.username} ({user.email})")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to register user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    # Generate tokens
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "org_id": user.org_id,
    }

    tokens = create_token_pair(user_data)

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": user.org_id,
        }
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    Accepts either username or email for login.
    """
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == request.username_or_email) |
        (User.email == request.username_or_email)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login time
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Generate tokens
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "org_id": user.org_id,
    }

    tokens = create_token_pair(user_data)

    logger.info(f"User logged in: {user.username}")

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": user.org_id,
        }
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.

    The refresh token should have longer expiration than access token.
    """
    # Decode refresh token
    token_data = decode_token(request.refresh_token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate new token pair
    user_data = {
        "user_id": token_data.user_id,
        "username": token_data.username,
        "email": token_data.email,
        "role": token_data.role,
        "org_id": token_data.org_id,
    }

    tokens = create_token_pair(user_data)

    logger.info(f"Token refreshed for user: {token_data.username}")

    return tokens


@router.get("/me")
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's information.

    Requires valid JWT token.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "org_id": user.org_id,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user's password.

    Requires current password for verification.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    user.hashed_password = hash_password(request.new_password)
    db.commit()

    logger.info(f"Password changed for user: {user.username}")

    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_user)):
    """
    Logout user.

    Note: With JWT, actual logout is handled client-side by discarding tokens.
    This endpoint is here for consistency and can be used for logging.
    """
    logger.info(f"User logged out: {current_user.username}")

    return {"message": "Logged out successfully"}

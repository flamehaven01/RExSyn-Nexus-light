"""
Authentication Service - JWT & Password Hashing
================================================

Handles user authentication, JWT tokens, and password management.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is not set. Fail Closed.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days


# ============================================================================
# Models
# ============================================================================

class TokenData(BaseModel):
    """Data stored in JWT token."""
    user_id: str
    username: str
    email: str
    role: str
    org_id: str


class TokenPair(BaseModel):
    """Access + Refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ============================================================================
# Password Functions
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token Functions
# ============================================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time (default: 30 days)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_pair(user_data: dict) -> TokenPair:
    """
    Create access + refresh token pair.

    Args:
        user_data: User data to encode (user_id, username, email, role, org_id)

    Returns:
        TokenPair with both tokens
    """
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(user_data)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
    )


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Validate required fields
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        email: str = payload.get("email")
        role: str = payload.get("role")
        org_id: str = payload.get("org_id")

        if not all([user_id, username, email, role, org_id]):
            return None

        return TokenData(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            org_id=org_id,
        )

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def verify_token(token: str) -> bool:
    """
    Verify if a token is valid.

    Args:
        token: JWT token string

    Returns:
        True if valid, False otherwise
    """
    return decode_token(token) is not None


# ============================================================================
# Authentication Helpers
# ============================================================================

def authenticate_user(username_or_email: str, password: str, db_user) -> Optional[dict]:
    """
    Authenticate a user with username/email and password.

    Args:
        username_or_email: Username or email
        password: Plain text password
        db_user: User object from database

    Returns:
        User data dict if authenticated, None otherwise
    """
    if not db_user:
        return None

    if not verify_password(password, db_user.hashed_password):
        return None

    if not db_user.is_active:
        logger.warning(f"Inactive user attempted login: {db_user.username}")
        return None

    return {
        "user_id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role,
        "org_id": db_user.org_id,
    }


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    FastAPI dependency to get current authenticated user from JWT.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    token = credentials.credentials

    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Get current active user (additional check can be added here).
    """
    # Additional checks can be added here (e.g., query DB to verify user is still active)
    return current_user


def require_role(allowed_roles: list[str]):
    """
    Dependency factory to require specific roles.

    Usage:
        @app.post("/admin")
        async def admin_route(user: TokenData = Depends(require_role(["admin"]))):
            ...
    """
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}"
            )
        return current_user

    return role_checker

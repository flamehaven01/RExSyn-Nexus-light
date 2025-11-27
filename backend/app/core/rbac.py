from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import base64

import httpx
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk

from .settings import settings

security = HTTPBearer()


class Principal:
    def __init__(self, sub: str, org: str, roles: List[str], perms: List[str]):
        self.sub = sub
        self.org = org
        self.roles = roles
        self.perms = perms


_JWKS_CACHE: Optional[Dict] = None
_JWKS_CACHE_EXPIRY: Optional[datetime] = None


def _local_jwks() -> Dict:
    key_bytes = settings.SECRET_KEY.encode()
    k = base64.urlsafe_b64encode(key_bytes).rstrip(b"=").decode()
    return {
        "keys": [
            {
                "kty": "oct",
                "k": k,
                "alg": "HS256",
                "kid": "local",
            }
        ]
    }


def fetch_jwks() -> Dict:
    """
    Fetch JWKS over HTTPS and cache the response for the configured TTL.
    """
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRY

    now = datetime.now(timezone.utc)

    if settings.JWKS_URL in {"", "local"}:
        return _local_jwks()
    if _JWKS_CACHE and _JWKS_CACHE_EXPIRY and now < _JWKS_CACHE_EXPIRY:
        return _JWKS_CACHE

    if settings.JWKS_URL.startswith("http://"):
        raise HTTPException(
            status_code=500,
            detail="JWKS endpoint must use HTTPS. Set RSN_JWKS_URL to an HTTPS URL.",
        )

    try:
        response = httpx.get(settings.JWKS_URL, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        _JWKS_CACHE = data
        _JWKS_CACHE_EXPIRY = now + timedelta(seconds=settings.JWKS_CACHE_SECONDS)
        return data
    except Exception as e:
        if _JWKS_CACHE:
            # serve stale but log
            return _JWKS_CACHE
        raise HTTPException(status_code=401, detail=f"JWKS fetch failed: {e}")

async def get_principal(
    creds: HTTPAuthorizationCredentials = Security(security)
) -> Principal:
    token = creds.credentials

    try:
        jwks = fetch_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Find matching key
        key = None
        if kid:
            key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        else:
            key = jwks["keys"][0] if jwks.get("keys") else None
        if not key:
            raise HTTPException(status_code=401, detail="Invalid token: kid not found")

        if key.get("kty") == "oct":
            k = key.get("k", "")
            padding = "=" * (-len(k) % 4)
            secret = base64.urlsafe_b64decode(k + padding)
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience=settings.JWT_AUD,
            )
        else:
            public_key = jwk.construct(key)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=settings.JWT_AUD,
            )

        return Principal(
            sub=payload.get("sub", "unknown"),
            org=payload.get("org", "default"),
            roles=payload.get("roles", []),
            perms=payload.get("perms", [])
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {e}")

def require_roles(*required: str):
    async def _dep(principal: Principal = Depends(get_principal)):
        if not set(required).intersection(set(principal.roles)):
            raise HTTPException(status_code=403, detail="Forbidden: role required")
        return principal
    return _dep

def require_perms(*required: str):
    async def _dep(principal: Principal = Depends(get_principal)):
        if not set(required).issubset(set(principal.perms)):
            raise HTTPException(status_code=403, detail="Forbidden: permission required")
        return principal
    return _dep

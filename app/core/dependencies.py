from typing import Annotated
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import decode_access_token
from app.db.main import get_session
from app.db.redis import is_token_in_blocklist, add_jti_to_blocklist


class TokenBearer(HTTPBearer):
    """Base class — validates token signature and blocklist."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(
        self,
        request: Request,
        session: AsyncSession = Depends(get_session),
    ) -> dict:
        creds: HTTPAuthorizationCredentials = await super().__call__(request)
        
        token = creds.credentials

        # 1. Decode and validate signature / expiry
        token_data = decode_access_token(token)
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
            )

        # 2. Check Redis blocklist
        jti = token_data.get("jti")
        if jti and await is_token_in_blocklist(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_REVOKED", "message": "Token has been revoked"},
            )

        # 3. Delegate type-specific checks to subclasses
        self.verify_token_data(token_data)

        # Store on request state for easy access in route handlers
        request.state.token_data = token_data

        return token_data

    def verify_token_data(self, token_data: dict) -> None:
        raise NotImplementedError("Subclasses must implement verify_token_data()")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data.get("refresh") is True:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Use an access token, not a refresh token"},
            )


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if not token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_REFRESH_TOKEN", "message": "Use a refresh token"},
            )


# ── Services injected via Depends — not instantiated manually ──────────

def get_session_dep(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── get_current_user ──────────────────────────────────────────────────────────

async def get_current_user(
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    """Returns the full User object for the authenticated request."""
    from app.features.auth.services import AuthServices  # avoid circular import
    user_id = token_data["user"]["id"]
    user = await AuthServices().get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "User not found"},
        )
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


# ── logout helper — dynamic TTL ───────────────────────────────────────────────

async def revoke_token(token_data: dict) -> None:
    """
    Add the token JTI to the Redis blocklist with dynamic TTL.
    Fix 7: TTL = remaining lifetime of the token, not a fixed value.
    """
    jti = token_data.get("jti")
    exp = token_data.get("exp")
    if jti and exp:
        ttl = exp - int(datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            await add_jti_to_blocklist(jti, ttl=ttl)

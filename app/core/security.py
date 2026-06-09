import uuid
import logging
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import Config

password_hash = PasswordHash.recommended()


# ── Password ──────────────────────────────────────────────────────────────────

def generate_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(
    user_data: dict,
    expires_delta: timedelta | None = None,
    refresh: bool = False,
) -> str:
    """Create a signed JWT access (or refresh) token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "user": user_data,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "refresh": refresh,
    }

    return jwt.encode(
        payload=payload,
        key=Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    """Decode a JWT token. Returns None if invalid or expired."""
    try:
        return jwt.decode(
            jwt=token,
            key=Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as e:
        logging.exception(e)
        return None

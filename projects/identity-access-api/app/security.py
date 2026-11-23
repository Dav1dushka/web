from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
try:
    from pwdlib import PasswordHash
    password_hasher = PasswordHash.recommended()
except ImportError:  # Local fallback when pwdlib is unavailable in the build environment.
    from argon2 import PasswordHasher

    class _Argon2Compat:
        _hasher = PasswordHasher()

        def hash(self, password: str) -> str:
            return self._hasher.hash(password)

        def verify(self, password: str, encoded_hash: str) -> bool:
            return self._hasher.verify(encoded_hash, password)

    password_hasher = _Argon2Compat()
from .config import get_settings



def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hasher.verify(password, encoded_hash)
    except Exception:
        return False


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def db_utc_now() -> datetime:
    # Keep timestamps timezone-aware for PostgreSQL; SQLite stores them as naive UTC.
    return utc_now()


def hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def create_token(*, subject: int, token_type: str, expires_delta: timedelta, jti: str, family_id: str | None = None) -> str:
    settings = get_settings()
    now = utc_now()
    payload = {
        "sub": str(subject), "type": token_type, "jti": jti,
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
        "iat": now, "nbf": now, "exp": now + expires_delta,
    }
    if family_id is not None:
        payload["family"] = family_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> dict:
    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub", "type", "jti"]},
    )
    if payload.get("type") != expected_type:
        raise InvalidTokenError("Unexpected token type")
    if expected_type == "refresh" and not payload.get("family"):
        raise InvalidTokenError("Missing refresh-token family")
    return payload


def new_jti() -> str:
    return str(uuid.uuid4())

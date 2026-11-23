from __future__ import annotations

from datetime import timedelta
from uuid import uuid4
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import AuditEvent, RefreshSession, User
from .security import create_token, db_utc_now, decode_token, hash_jti, new_jti

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def auth_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def issue_token_pair(db: Session, user: User, family_id: str | None = None) -> dict:
    settings = get_settings()
    family_id = family_id or str(uuid4())
    access_jti, refresh_jti = new_jti(), new_jti()
    access_token = create_token(subject=user.id, token_type="access", expires_delta=timedelta(minutes=settings.access_token_minutes), jti=access_jti)
    refresh_token = create_token(subject=user.id, token_type="refresh", expires_delta=timedelta(days=settings.refresh_token_days), jti=refresh_jti, family_id=family_id)
    db.add(RefreshSession(user_id=user.id, jti_hash=hash_jti(refresh_jti), family_id=family_id, expires_at=db_utc_now() + timedelta(days=settings.refresh_token_days)))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": settings.access_token_minutes * 60}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token, "access")
        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise auth_error()
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise auth_error("User account is unavailable.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required.")
    return current_user

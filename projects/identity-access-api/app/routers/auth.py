from __future__ import annotations

from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..auth import auth_error, get_current_user, issue_token_pair
from ..database import get_db
from ..models import AuditEvent, RefreshSession, User
from ..schemas import Message, RefreshRequest, TokenPair, UserCreate, UserRead
from ..security import db_utc_now, decode_token, hash_jti, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
# Known Argon2 hash for a dummy verification path on unknown email addresses.
_DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$wagCPXjifgvUFBzq4hqe3w$CYaIb8sB+wtD+Vu/P4uod1+Qof8h+1g7bbDlBID48Rc"


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role="user", is_active=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    db.refresh(user)
    return user


@router.post("/token", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(form.password, _DUMMY_HASH)
        raise auth_error("Incorrect email or password.")
    if not verify_password(form.password, user.password_hash):
        raise auth_error("Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")
    result = issue_token_pair(db, user)
    db.add(AuditEvent(actor_user_id=user.id, action="auth.login", target_user_id=user.id))
    db.commit()
    return result


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token, "refresh")
        user_id, jti, family_id = int(data["sub"]), data["jti"], data["family"]
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise auth_error("Invalid refresh token.")
    record = db.scalar(select(RefreshSession).where(RefreshSession.jti_hash == hash_jti(jti)))
    now = db_utc_now()
    if record is None or record.user_id != user_id or record.family_id != family_id:
        raise auth_error("Refresh session not found.")
    if record.revoked_at is not None:
        # Reuse of a rotated token revokes the remaining refresh sessions in its family.
        db.execute(update(RefreshSession).where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now))
        db.commit()
        raise auth_error("Refresh token reuse detected. Sign in again.")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise auth_error("Refresh token has expired.")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise auth_error("User account is unavailable.")
    record.revoked_at = now
    result = issue_token_pair(db, user, family_id=family_id)
    db.add(AuditEvent(actor_user_id=user.id, action="auth.refresh", target_user_id=user.id))
    db.commit()
    return result


@router.post("/logout", response_model=Message)
def logout(payload: RefreshRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token, "refresh")
        user_id, jti = int(data["sub"]), data["jti"]
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise auth_error("Invalid refresh token.")
    if user_id != current_user.id:
        raise auth_error("Refresh token does not belong to the current user.")
    record = db.scalar(select(RefreshSession).where(RefreshSession.jti_hash == hash_jti(jti)))
    if record and record.revoked_at is None:
        record.revoked_at = db_utc_now()
        db.add(AuditEvent(actor_user_id=current_user.id, action="auth.logout", target_user_id=current_user.id))
        db.commit()
    return {"message": "Refresh session revoked."}

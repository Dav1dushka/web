from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..auth import require_admin
from ..database import get_db
from ..models import AuditEvent, User
from ..schemas import ActiveUpdate, RoleUpdate, UserRead

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=list[UserRead])
def list_users(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id).offset(skip).limit(limit)).all()


@router.patch("/users/{user_id}/role", response_model=UserRead)
def update_role(user_id: int, payload: RoleUpdate, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == actor.id and payload.role != "admin":
        raise HTTPException(status_code=409, detail="You cannot remove your own administrator role.")
    if target.role == "admin" and payload.role == "user":
        admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == "admin"))
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="The last administrator cannot be demoted.")
    old_role = target.role
    target.role = payload.role
    db.add(AuditEvent(actor_user_id=actor.id, action="admin.role_changed", target_user_id=target.id, details=f"{old_role}->{payload.role}"))
    db.commit()
    db.refresh(target)
    return target


@router.patch("/users/{user_id}/status", response_model=UserRead)
def update_status(user_id: int, payload: ActiveUpdate, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == actor.id and not payload.is_active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account.")
    target.is_active = payload.is_active
    if not payload.is_active:
        for session_record in target.refresh_sessions:
            if session_record.revoked_at is None:
                session_record.revoked_at = datetime.now(timezone.utc)
    db.add(AuditEvent(actor_user_id=actor.id, action="admin.user_status_changed", target_user_id=target.id, details=f"is_active={payload.is_active}"))
    db.commit()
    db.refresh(target)
    return target


@router.get("/audit", response_model=list[dict])
def audit_log(limit: int = Query(50, ge=1, le=200), _: User = Depends(require_admin), db: Session = Depends(get_db)):
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)).all()
    return [{"id": e.id, "actor_user_id": e.actor_user_id, "action": e.action, "target_user_id": e.target_user_id, "details": e.details, "created_at": e.created_at} for e in events]

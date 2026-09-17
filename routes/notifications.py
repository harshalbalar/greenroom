"""Notification routes — list, count unread, mark read."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, User, Notification, utcnow
from auth_core import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str
    data: dict = {}
    is_read: bool
    created_at: datetime | None = None


class UnreadCountResponse(BaseModel):
    count: int


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notifications for the current user, newest first."""
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifs = query.order_by(Notification.created_at.desc()).limit(limit).all()

    return [
        NotificationResponse(
            id=n.id,
            type=n.type,
            title=n.title,
            body=n.body,
            data=n.data or {},
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in notifs
    ]


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the number of unread notifications."""
    count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False,
    ).count()
    return UnreadCountResponse(count=count)


@router.post("/{notif_id}/read")
def mark_read(
    notif_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"status": "ok"}


@router.post("/read-all")
def mark_all_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"status": "ok"}

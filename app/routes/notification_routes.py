"""
Notification routes for real-time and email notifications.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.utils.dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[schemas.NotificationRead])
def get_notifications(
    is_read: Optional[bool] = Query(default=None),
    notification_type: Optional[str] = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get notifications for the current user.
    """
    # Determine user_id and user_type based on role
    user_id = current_user.candidate_id or current_user.recruiter_id
    user_type = current_user.role
    
    query = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.user_type == user_type,
    )
    
    # Apply filters
    if is_read is not None:
        query = query.filter(models.Notification.is_read == is_read)
    if notification_type:
        query = query.filter(models.Notification.notification_type == notification_type)
    
    # Order by most recent
    query = query.order_by(models.Notification.created_at.desc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    notifications = query.offset(offset).limit(page_size).all()
    
    return [
        schemas.NotificationRead(
            notification_id=n.notification_id,
            user_id=n.user_id,
            user_type=n.user_type,
            title=n.title,
            message=n.message,
            notification_type=n.notification_type,
            related_type=n.related_type,
            related_id=n.related_id,
            is_read=n.is_read,
            created_at=n.created_at,
            read_at=n.read_at,
        )
        for n in notifications
    ]


@router.get("/unread-count")
def get_unread_count(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get count of unread notifications.
    """
    user_id = current_user.candidate_id or current_user.recruiter_id
    user_type = current_user.role
    
    count = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.user_type == user_type,
        models.Notification.is_read == False,
    ).count()
    
    return {"unread_count": count}


@router.post("/mark-as-read")
def mark_notifications_as_read(
    payload: schemas.NotificationMarkAsRead,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark specific notifications as read.
    """
    user_id = current_user.candidate_id or current_user.recruiter_id
    user_type = current_user.role
    
    # Update notifications
    db.query(models.Notification).filter(
        models.Notification.notification_id.in_(payload.notification_ids),
        models.Notification.user_id == user_id,
        models.Notification.user_type == user_type,
    ).update({
        "is_read": True,
        "read_at": datetime.now(),
    }, synchronize_session=False)
    
    db.commit()
    
    return {"message": f"Marked {len(payload.notification_ids)} notifications as read"}


@router.post("/mark-all-as-read")
def mark_all_as_read(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark all notifications as read.
    """
    user_id = current_user.candidate_id or current_user.recruiter_id
    user_type = current_user.role
    
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.user_type == user_type,
        models.Notification.is_read == False,
    ).update({
        "is_read": True,
        "read_at": datetime.now(),
    }, synchronize_session=False)
    
    db.commit()
    
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a specific notification.
    """
    user_id = current_user.candidate_id or current_user.recruiter_id
    user_type = current_user.role
    
    notification = db.query(models.Notification).filter(
        models.Notification.notification_id == notification_id,
        models.Notification.user_id == user_id,
        models.Notification.user_type == user_type,
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()


@router.delete("/clear-all")
def clear_all_notifications(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete all notifications for the current user.
    """
    user_id = current_user.candidate_id or current_user.recruiter_id
    user_type = current_user.role
    
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.user_type == user_type,
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return {"message": "All notifications cleared"}


@router.get("/{notification_id}", response_model=schemas.NotificationRead)
def get_notification(
    notification_id: int,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific notification by ID.
    """
    user_id = current_user.candidate_id or current_user.recruiter_id
    user_type = current_user.role
    
    notification = db.query(models.Notification).filter(
        models.Notification.notification_id == notification_id,
        models.Notification.user_id == user_id,
        models.Notification.user_type == user_type,
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Mark as read if not already
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now()
        db.commit()
    
    return schemas.NotificationRead(
        notification_id=notification.notification_id,
        user_id=notification.user_id,
        user_type=notification.user_type,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        related_type=notification.related_type,
        related_id=notification.related_id,
        is_read=notification.is_read,
        created_at=notification.created_at,
        read_at=notification.read_at,
    )

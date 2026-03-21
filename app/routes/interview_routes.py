"""
Advanced interview routes with feedback and scheduling features.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.utils.dependencies import get_current_user, get_db, require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("", response_model=schemas.InterviewRead, status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: schemas.InterviewCreate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """
    Schedule an interview for an application.
    Sends email invitation to candidate.
    """
    # Validate application
    application = (
        db.query(models.Application)
        .options(
            joinedload(models.Application.job),
            joinedload(models.Application.candidate)
        )
        .filter(models.Application.application_id == payload.application_id)
        .first()
    )
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if not application.job or application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(
            status_code=403,
            detail="Not allowed to schedule interview for this application"
        )
    
    # Validate scheduled time is in the future
    if payload.scheduled_at <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Interview must be scheduled in the future"
        )
    
    # Validate end time if provided
    if payload.end_time and payload.end_time <= payload.scheduled_at:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )
    
    # Create interview
    interview = models.Interview(
        application_id=payload.application_id,
        scheduled_at=payload.scheduled_at,
        end_time=payload.end_time,
        interview_type=payload.interview_type,
        status="Scheduled",
        interviewer_name=payload.interviewer_name,
        interviewer_email=payload.interviewer_email,
        interview_link=payload.interview_link,
        location_address=payload.location_address,
        interview_notes=payload.interview_notes,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    
    logger.info(f"Interview scheduled: {interview.interview_id} for application {payload.application_id}")
    
    # TODO: Send email invitation to candidate and interviewer
    
    return schemas.InterviewRead(
        interview_id=interview.interview_id,
        application_id=interview.application_id,
        scheduled_at=interview.scheduled_at,
        end_time=interview.end_time,
        interview_type=interview.interview_type,
        status=interview.status,
        interview_link=interview.interview_link,
        location_address=interview.location_address,
        interviewer_name=interview.interviewer_name,
        interviewer_email=interview.interviewer_email,
        interview_notes=interview.interview_notes,
        created_at=interview.created_at,
        candidate_name=application.candidate.full_name if application.candidate else None,
        candidate_email=application.candidate.email if application.candidate else None,
        job_title=application.job.title if application.job else None,
    )


@router.get("", response_model=list[schemas.InterviewRead])
def get_interviews(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    interview_type: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get interviews - role-based access.
    - Recruiters: See interviews for their jobs
    - Candidates: See their own interviews
    """
    query = db.query(models.Interview).join(
        models.Application
    ).join(models.Job)
    
    if current_user.role == "recruiter":
        query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
    else:
        query = query.filter(models.Application.candidate_id == current_user.candidate_id)
    
    # Apply filters
    if status_filter:
        query = query.filter(models.Interview.status == status_filter)
    if interview_type:
        query = query.filter(models.Interview.interview_type == interview_type)
    if start_date:
        query = query.filter(models.Interview.scheduled_at >= start_date)
    if end_date:
        query = query.filter(models.Interview.scheduled_at <= end_date)
    
    # Order by scheduled date
    query = query.order_by(models.Interview.scheduled_at.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    interviews = query.offset(offset).limit(page_size).all()
    
    result = []
    for interview in interviews:
        result.append(
            schemas.InterviewRead(
                interview_id=interview.interview_id,
                application_id=interview.application_id,
                scheduled_at=interview.scheduled_at,
                end_time=interview.end_time,
                interview_type=interview.interview_type,
                status=interview.status,
                interview_link=interview.interview_link,
                location_address=interview.location_address,
                interviewer_name=interview.interviewer_name,
                interviewer_email=interview.interviewer_email,
                interview_notes=interview.interview_notes,
                feedback=interview.feedback,
                interview_score=interview.interview_score,
                recommendation=interview.recommendation,
                technical_score=interview.technical_score,
                communication_score=interview.communication_score,
                cultural_fit_score=interview.cultural_fit_score,
                problem_solving_score=interview.problem_solving_score,
                created_at=interview.created_at,
                updated_at=interview.updated_at,
                candidate_name=interview.application.candidate.full_name if interview.application and interview.application.candidate else None,
                candidate_email=interview.application.candidate.email if interview.application and interview.application.candidate else None,
                job_title=interview.application.job.title if interview.application and interview.application.job else None,
            )
        )
    
    return result


@router.get("/{interview_id}", response_model=schemas.InterviewRead)
def get_interview(
    interview_id: int,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific interview by ID."""
    interview = db.query(models.Interview).options(
        joinedload(models.Interview.application).joinedload(models.Application.candidate),
        joinedload(models.Interview.application).joinedload(models.Application.job)
    ).filter(models.Interview.interview_id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Check permissions
    if current_user.role == "recruiter":
        if not interview.application or not interview.application.job or \
           interview.application.job.recruiter_id != current_user.recruiter_id:
            raise HTTPException(status_code=403, detail="Not allowed to view this interview")
    else:
        if not interview.application or \
           interview.application.candidate_id != current_user.candidate_id:
            raise HTTPException(status_code=403, detail="Not allowed to view this interview")
    
    return schemas.InterviewRead(
        interview_id=interview.interview_id,
        application_id=interview.application_id,
        scheduled_at=interview.scheduled_at,
        end_time=interview.end_time,
        interview_type=interview.interview_type,
        status=interview.status,
        interview_link=interview.interview_link,
        location_address=interview.location_address,
        interviewer_name=interview.interviewer_name,
        interviewer_email=interview.interviewer_email,
        interview_notes=interview.interview_notes,
        feedback=interview.feedback,
        interview_score=interview.interview_score,
        recommendation=interview.recommendation,
        technical_score=interview.technical_score,
        communication_score=interview.communication_score,
        cultural_fit_score=interview.cultural_fit_score,
        problem_solving_score=interview.problem_solving_score,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        candidate_name=interview.application.candidate.full_name if interview.application and interview.application.candidate else None,
        candidate_email=interview.application.candidate.email if interview.application and interview.application.candidate else None,
        job_title=interview.application.job.title if interview.application and interview.application.job else None,
    )


@router.put("/{interview_id}", response_model=schemas.InterviewRead)
def update_interview(
    interview_id: int,
    payload: schemas.InterviewUpdate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """
    Update interview details (recruiter only).
    Sends notification on rescheduling.
    """
    interview = db.query(models.Interview).options(
        joinedload(models.Interview.application).joinedload(models.Application.job)
    ).filter(models.Interview.interview_id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    if not interview.application or not interview.application.job or \
       interview.application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to update this interview")
    
    # Check if rescheduling
    is_rescheduling = payload.scheduled_at and payload.scheduled_at != interview.scheduled_at
    
    # Update fields
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(interview, field, value)
    
    db.commit()
    db.refresh(interview)
    
    logger.info(f"Interview {interview_id} updated by recruiter {current_user.recruiter_id}")
    
    # TODO: Send notification if rescheduled
    
    return schemas.InterviewRead(
        interview_id=interview.interview_id,
        application_id=interview.application_id,
        scheduled_at=interview.scheduled_at,
        end_time=interview.end_time,
        interview_type=interview.interview_type,
        status=interview.status,
        interview_link=interview.interview_link,
        location_address=interview.location_address,
        interviewer_name=interview.interviewer_name,
        interviewer_email=interview.interviewer_email,
        interview_notes=interview.interview_notes,
        feedback=interview.feedback,
        interview_score=interview.interview_score,
        recommendation=interview.recommendation,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        candidate_name=interview.application.candidate.full_name if interview.application and interview.application.candidate else None,
        candidate_email=interview.application.candidate.email if interview.application and interview.application.candidate else None,
        job_title=interview.application.job.title if interview.application and interview.application.job else None,
    )


@router.post("/{interview_id}/feedback", response_model=schemas.InterviewRead)
def submit_interview_feedback(
    interview_id: int,
    payload: schemas.InterviewFeedbackSubmit,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """
    Submit detailed interview feedback and scoring.
    """
    interview = db.query(models.Interview).options(
        joinedload(models.Interview.application).joinedload(models.Application.job)
    ).filter(models.Interview.interview_id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    if not interview.application or not interview.application.job or \
       interview.application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to submit feedback for this interview")
    
    # Update feedback
    interview.feedback = payload.feedback
    interview.interview_score = payload.interview_score
    interview.recommendation = payload.recommendation
    interview.technical_score = payload.technical_score
    interview.communication_score = payload.communication_score
    interview.cultural_fit_score = payload.cultural_fit_score
    interview.problem_solving_score = payload.problem_solving_score
    interview.status = "Completed"
    
    db.commit()
    db.refresh(interview)
    
    logger.info(f"Feedback submitted for interview {interview_id} by recruiter {current_user.recruiter_id}")
    
    # TODO: Send notification to candidate about feedback completion
    
    return schemas.InterviewRead(
        interview_id=interview.interview_id,
        application_id=interview.application_id,
        scheduled_at=interview.scheduled_at,
        end_time=interview.end_time,
        interview_type=interview.interview_type,
        status=interview.status,
        interview_link=interview.interview_link,
        location_address=interview.location_address,
        interviewer_name=interview.interviewer_name,
        interviewer_email=interview.interviewer_email,
        interview_notes=interview.interview_notes,
        feedback=interview.feedback,
        interview_score=interview.interview_score,
        recommendation=interview.recommendation,
        technical_score=interview.technical_score,
        communication_score=interview.communication_score,
        cultural_fit_score=interview.cultural_fit_score,
        problem_solving_score=interview.problem_solving_score,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        candidate_name=interview.application.candidate.full_name if interview.application and interview.application.candidate else None,
        candidate_email=interview.application.candidate.email if interview.application and interview.application.candidate else None,
        job_title=interview.application.job.title if interview.application and interview.application.job else None,
    )


@router.post("/{interview_id}/reschedule")
def reschedule_interview(
    interview_id: int,
    new_time: datetime,
    reason: Optional[str] = None,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reschedule an interview with optional reason.
    Sends notification to all parties.
    """
    interview = db.query(models.Interview).options(
        joinedload(models.Interview.application)
    ).filter(models.Interview.interview_id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Check permissions (both recruiter and candidate can request reschedule)
    can_reschedule = False
    if current_user.role == "recruiter" and interview.application and interview.application.job:
        if interview.application.job.recruiter_id == current_user.recruiter_id:
            can_reschedule = True
    elif current_user.role == "candidate" and interview.application:
        if interview.application.candidate_id == current_user.candidate_id:
            can_reschedule = True
    
    if not can_reschedule:
        raise HTTPException(status_code=403, detail="Not allowed to reschedule this interview")
    
    # Validate new time
    if new_time <= datetime.now():
        raise HTTPException(status_code=400, detail="New time must be in the future")
    
    old_time = interview.scheduled_at
    interview.scheduled_at = new_time
    db.commit()
    
    logger.info(f"Interview {interview_id} rescheduled from {old_time} to {new_time}")
    
    # TODO: Send reschedule notification to all parties
    
    return {
        "message": "Interview rescheduled successfully",
        "old_time": str(old_time),
        "new_time": str(new_time),
        "reason": reason,
    }


@router.post("/{interview_id}/cancel")
def cancel_interview(
    interview_id: int,
    reason: Optional[str] = None,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel an interview.
    """
    interview = db.query(models.Interview).options(
        joinedload(models.Interview.application).joinedload(models.Application.job)
    ).filter(models.Interview.interview_id == interview_id).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Only recruiter can cancel
    if current_user.role != "recruiter" or not interview.application or not interview.application.job or \
       interview.application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to cancel this interview")
    
    interview.status = "Cancelled"
    if reason:
        interview.interview_notes = f"{interview.interview_notes or ''}\n\nCancellation reason: {reason}"
    
    db.commit()
    
    logger.info(f"Interview {interview_id} cancelled by recruiter {current_user.recruiter_id}")
    
    # TODO: Send cancellation notification
    
    return {"message": "Interview cancelled successfully", "reason": reason}


@router.get("/stats/summary")
def get_interview_stats(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get interview statistics summary.
    """
    query = db.query(models.Interview).join(models.Application).join(models.Job)
    
    if current_user.role == "recruiter":
        query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
    else:
        query = query.filter(models.Application.candidate_id == current_user.candidate_id)
    
    total = query.count()
    scheduled = query.filter(models.Interview.status == "Scheduled").count()
    completed = query.filter(models.Interview.status == "Completed").count()
    cancelled = query.filter(models.Interview.status == "Cancelled").count()
    no_show = query.filter(models.Interview.status == "No-Show").count()
    
    # Upcoming interviews
    upcoming = query.filter(
        models.Interview.status == "Scheduled",
        models.Interview.scheduled_at >= datetime.now()
    ).order_by(models.Interview.scheduled_at.asc()).limit(5).all()
    
    return {
        "total": total,
        "scheduled": scheduled,
        "completed": completed,
        "cancelled": cancelled,
        "no_show": no_show,
        "completion_rate": round((completed / total * 100) if total > 0 else 0, 2),
        "upcoming_interviews": [
            {
                "interview_id": i.interview_id,
                "scheduled_at": str(i.scheduled_at),
                "interview_type": i.interview_type,
                "candidate_name": i.application.candidate.full_name if i.application and i.application.candidate else None,
                "job_title": i.application.job.title if i.application and i.application.job else None,
            }
            for i in upcoming
        ],
    }

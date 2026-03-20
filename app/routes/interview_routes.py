from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.utils.dependencies import get_current_user, get_db, require_role

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("", response_model=schemas.InterviewRead, status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: schemas.InterviewCreate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    application = (
        db.query(models.Application)
        .join(models.Job)
        .filter(models.Application.application_id == payload.application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to schedule interview for this application")

    interview = models.Interview(
        application_id=payload.application_id,
        scheduled_at=payload.scheduled_at,
        interview_type=payload.interview_type,
        status=payload.status,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


@router.get("", response_model=list[schemas.InterviewRead])
def get_interviews(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Interview).join(models.Application).join(models.Job)
    if current_user.role == "recruiter":
        query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
    else:
        query = query.filter(models.Application.candidate_id == current_user.candidate_id)
    return query.order_by(models.Interview.scheduled_at.asc()).all()


@router.put("/{id}", response_model=schemas.InterviewRead)
def update_interview(
    id: int,
    payload: schemas.InterviewUpdate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    interview = db.query(models.Interview).filter(models.Interview.interview_id == id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if interview.application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to update this interview")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(interview, field, value)
    db.commit()
    db.refresh(interview)
    return interview


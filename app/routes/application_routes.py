from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.utils.dependencies import get_current_user, get_db, require_role

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("", response_model=schemas.ApplicationRead, status_code=status.HTTP_201_CREATED)
def apply_job(
    payload: schemas.ApplicationCreate,
    current_user: models.UserCredential = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.job_id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "Open":
        raise HTTPException(status_code=400, detail="Applications are closed for this job")

    existing = (
        db.query(models.Application)
        .filter(
            models.Application.job_id == payload.job_id,
            models.Application.candidate_id == current_user.candidate_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already applied for this job")

    application = models.Application(
        job_id=payload.job_id,
        candidate_id=current_user.candidate_id,
        status="Applied",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return schemas.ApplicationRead(
        **application.__dict__,
        job_title=job.title,
    )


@router.get("", response_model=list[schemas.ApplicationRead])
def get_applications(
    job_id: int | None = Query(default=None),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "recruiter":
        query = db.query(models.Application).join(models.Job).filter(
            models.Job.recruiter_id == current_user.recruiter_id
        )
        if job_id:
            query = query.filter(models.Application.job_id == job_id)
        applications = query.order_by(models.Application.created_at.desc()).all()
    else:
        applications = (
            db.query(models.Application)
            .filter(models.Application.candidate_id == current_user.candidate_id)
            .order_by(models.Application.created_at.desc())
            .all()
        )

    response = []
    for app in applications:
        response.append(
            schemas.ApplicationRead(
                application_id=app.application_id,
                job_id=app.job_id,
                candidate_id=app.candidate_id,
                status=app.status,
                created_at=app.created_at,
                job_title=app.job.title if app.job else None,
                candidate_name=app.candidate.full_name if app.candidate else None,
            )
        )
    return response


@router.put("/{id}/status", response_model=schemas.ApplicationRead)
def update_application_status(
    id: int,
    payload: schemas.ApplicationStatusUpdate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    application = db.query(models.Application).filter(models.Application.application_id == id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to manage this application")

    application.status = payload.status
    db.commit()
    db.refresh(application)
    return schemas.ApplicationRead(
        application_id=application.application_id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        status=application.status,
        created_at=application.created_at,
        job_title=application.job.title if application.job else None,
        candidate_name=application.candidate.full_name if application.candidate else None,
    )


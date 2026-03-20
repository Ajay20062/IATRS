from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.utils.dependencies import get_current_user, get_db, require_role

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[schemas.JobRead])
def get_jobs(
    search: str | None = Query(default=None),
    location: str | None = Query(default=None),
    department: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Job)
    if search:
        like_term = f"%{search}%"
        query = query.filter(models.Job.title.ilike(like_term))
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if department:
        query = query.filter(models.Job.department.ilike(f"%{department}%"))
    if status_filter:
        query = query.filter(models.Job.status == status_filter)
    return query.order_by(models.Job.created_at.desc()).all()


@router.post("", response_model=schemas.JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: schemas.JobCreate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    job = models.Job(
        recruiter_id=current_user.recruiter_id,
        title=payload.title,
        department=payload.department,
        location=payload.location,
        status=payload.status,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{id}", response_model=schemas.JobRead)
def update_job(
    id: int,
    payload: schemas.JobUpdate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.job_id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to update this job")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    id: int,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.job_id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this job")

    db.delete(job)
    db.commit()


from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.utils.dependencies import get_db

router = APIRouter(prefix="/stats", tags=["System"])


@router.get("/schema")
def schema_stats(db: Session = Depends(get_db)):
    recruiters = db.query(func.count(models.Recruiter.recruiter_id)).scalar() or 0
    jobs = db.query(func.count(models.Job.job_id)).scalar() or 0
    candidates = db.query(func.count(models.Candidate.candidate_id)).scalar() or 0
    applications = db.query(func.count(models.Application.application_id)).scalar() or 0
    interviews = db.query(func.count(models.Interview.interview_id)).scalar() or 0

    return {
        "recruiters": recruiters,
        "jobs": jobs,
        "candidates": candidates,
        "applications": applications,
        "interviews": interviews,
        "total_records": recruiters + jobs + candidates + applications + interviews,
    }


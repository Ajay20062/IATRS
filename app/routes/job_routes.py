"""
Advanced job routes with AI-powered features.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.utils.ai_resume_parser import calculate_job_candidate_match, rank_candidates, parse_resume
from app.utils.dependencies import get_current_user, get_db, require_role
from app.utils.analytics import get_dashboard_analytics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[schemas.JobRead])
def get_jobs(
    search: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    department: Optional[str] = Query(default=None),
    work_mode: Optional[str] = Query(default=None),
    min_salary: Optional[int] = Query(default=None),
    max_salary: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: Optional[models.UserCredential] = Depends(get_current_user),
):
    """
    Get all jobs with advanced filtering, pagination, and sorting.
    Public endpoint - no authentication required for browsing jobs.
    """
    query = db.query(models.Job).options(
        joinedload(models.Job.recruiter)
    )
    
    # Apply filters
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            (models.Job.title.ilike(like_term)) |
            (models.Job.description.ilike(like_term)) |
            (models.Job.requirements.ilike(like_term))
        )
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if department:
        query = query.filter(models.Job.department.ilike(f"%{department}%"))
    if work_mode:
        query = query.filter(models.Job.work_mode == work_mode)
    if min_salary:
        query = query.filter(
            (models.Job.max_salary >= min_salary) | (models.Job.max_salary == None)
        )
    if max_salary:
        query = query.filter(
            (models.Job.min_salary <= max_salary) | (models.Job.min_salary == None)
        )
    if status_filter:
        query = query.filter(models.Job.status == status_filter)
    else:
        # Default to showing only open jobs for public users
        if not current_user or current_user.role != "recruiter":
            query = query.filter(models.Job.status == "Open")
    
    # Apply sorting
    sort_column = getattr(models.Job, sort_by, models.Job.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.offset(offset).limit(page_size).all()
    
    # Format response
    result = []
    for job in jobs:
        job_data = schemas.JobRead(
            job_id=job.job_id,
            recruiter_id=job.recruiter_id,
            title=job.title,
            description=job.description,
            requirements=job.requirements,
            department=job.department,
            location=job.location,
            work_mode=job.work_mode,
            min_salary=job.min_salary,
            max_salary=job.max_salary,
            salary_currency=job.salary_currency,
            salary_period=job.salary_period,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            min_experience_years=job.min_experience_years,
            max_experience_years=job.max_experience_years,
            education_level=job.education_level,
            status=job.status,
            is_featured=job.is_featured,
            is_remote_friendly=job.is_remote_friendly,
            views_count=job.views_count,
            applications_count=job.applications_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
            expires_at=job.expires_at,
            recruiter_name=job.recruiter.full_name if job.recruiter else None,
            recruiter_company=job.recruiter.company if job.recruiter else None,
        )
        result.append(job_data)
    
    return result


@router.get("/{job_id}", response_model=schemas.JobRead)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[models.UserCredential] = Depends(get_current_user),
):
    """Get a specific job by ID."""
    job = db.query(models.Job).options(
        joinedload(models.Job.recruiter)
    ).filter(models.Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Increment view count
    job.views_count += 1
    db.commit()
    
    return schemas.JobRead(
        job_id=job.job_id,
        recruiter_id=job.recruiter_id,
        title=job.title,
        description=job.description,
        requirements=job.requirements,
        department=job.department,
        location=job.location,
        work_mode=job.work_mode,
        min_salary=job.min_salary,
        max_salary=job.max_salary,
        salary_currency=job.salary_currency,
        salary_period=job.salary_period,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        min_experience_years=job.min_experience_years,
        max_experience_years=job.max_experience_years,
        education_level=job.education_level,
        status=job.status,
        is_featured=job.is_featured,
        is_remote_friendly=job.is_remote_friendly,
        views_count=job.views_count,
        applications_count=job.applications_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        expires_at=job.expires_at,
        recruiter_name=job.recruiter.full_name if job.recruiter else None,
        recruiter_company=job.recruiter.company if job.recruiter else None,
    )


@router.post("", response_model=schemas.JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: schemas.JobCreate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Create a new job posting with advanced fields."""
    job = models.Job(
        recruiter_id=current_user.recruiter_id,
        title=payload.title,
        description=payload.description,
        requirements=payload.requirements,
        department=payload.department,
        location=payload.location,
        work_mode=payload.work_mode,
        min_salary=payload.min_salary,
        max_salary=payload.max_salary,
        salary_currency=payload.salary_currency,
        salary_period=payload.salary_period,
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
        min_experience_years=payload.min_experience_years,
        max_experience_years=payload.max_experience_years,
        education_level=payload.education_level,
        status=payload.status,
        is_featured=payload.is_featured,
        expires_at=payload.expires_at,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    logger.info(f"Job created: {job.job_id} by recruiter {current_user.recruiter_id}")
    
    return schemas.JobRead(
        job_id=job.job_id,
        recruiter_id=job.recruiter_id,
        title=job.title,
        description=job.description,
        requirements=job.requirements,
        department=job.department,
        location=job.location,
        work_mode=job.work_mode,
        min_salary=job.min_salary,
        max_salary=job.max_salary,
        salary_currency=job.salary_currency,
        salary_period=job.salary_period,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        min_experience_years=job.min_experience_years,
        max_experience_years=job.max_experience_years,
        education_level=job.education_level,
        status=job.status,
        is_featured=job.is_featured,
        is_remote_friendly=job.is_remote_friendly,
        views_count=job.views_count,
        applications_count=job.applications_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        expires_at=job.expires_at,
        recruiter_name=current_user.recruiter.full_name if current_user.recruiter else None,
        recruiter_company=current_user.recruiter.company if current_user.recruiter else None,
    )


@router.put("/{job_id}", response_model=schemas.JobRead)
def update_job(
    job_id: int,
    payload: schemas.JobUpdate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Update a job posting."""
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to update this job")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(job, field, value)
    
    db.commit()
    db.refresh(job)
    
    logger.info(f"Job updated: {job_id} by recruiter {current_user.recruiter_id}")
    
    return schemas.JobRead(
        job_id=job.job_id,
        recruiter_id=job.recruiter_id,
        title=job.title,
        description=job.description,
        requirements=job.requirements,
        department=job.department,
        location=job.location,
        work_mode=job.work_mode,
        min_salary=job.min_salary,
        max_salary=job.max_salary,
        salary_currency=job.salary_currency,
        salary_period=job.salary_period,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        min_experience_years=job.min_experience_years,
        max_experience_years=job.max_experience_years,
        education_level=job.education_level,
        status=job.status,
        is_featured=job.is_featured,
        is_remote_friendly=job.is_remote_friendly,
        views_count=job.views_count,
        applications_count=job.applications_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        expires_at=job.expires_at,
        recruiter_name=job.recruiter.full_name if job.recruiter else None,
        recruiter_company=job.recruiter.company if job.recruiter else None,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Delete a job posting."""
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this job")

    db.delete(job)
    db.commit()
    
    logger.info(f"Job deleted: {job_id} by recruiter {current_user.recruiter_id}")


@router.get("/{job_id}/applications")
def get_job_applications(
    job_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Get all applications for a specific job (recruiter only)."""
    job = db.query(models.Job).filter(
        models.Job.job_id == job_id,
        models.Job.recruiter_id == current_user.recruiter_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    query = db.query(models.Application).filter(
        models.Application.job_id == job_id
    ).options(
        joinedload(models.Application.candidate)
    )
    
    if status_filter:
        query = query.filter(models.Application.status == status_filter)
    
    applications = query.order_by(
        models.Application.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    return [
        schemas.ApplicationRead(
            application_id=app.application_id,
            job_id=app.job_id,
            candidate_id=app.candidate_id,
            status=app.status,
            match_score=app.match_score,
            screening_score=app.screening_score,
            resume_score=app.resume_score,
            cover_letter=app.cover_letter,
            recruiter_notes=app.recruiter_notes,
            rejection_reason=app.rejection_reason,
            created_at=app.created_at,
            updated_at=app.updated_at,
            reviewed_at=app.reviewed_at,
            candidate_name=app.candidate.full_name if app.candidate else None,
            candidate_email=app.candidate.email if app.candidate else None,
            candidate_phone=app.candidate.phone if app.candidate else None,
            candidate_resume_url=app.candidate.resume_url if app.candidate else None,
        )
        for app in applications
    ]


@router.post("/{job_id}/match-candidates", response_model=list[schemas.RankedCandidate])
def match_and_rank_candidates(
    job_id: int,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """
    AI-powered candidate matching and ranking for a job.
    Ranks all candidates who have applied based on job requirements.
    """
    job = db.query(models.Job).filter(
        models.Job.job_id == job_id,
        models.Job.recruiter_id == current_user.recruiter_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get job description and requirements
    job_text = f"{job.title} {job.description or ''} {job.requirements or ''} {job.required_skills or ''}"
    
    # Get all applications for this job
    applications = db.query(models.Application).join(
        models.Candidate
    ).filter(
        models.Application.job_id == job_id
    ).options(
        joinedload(models.Application.candidate)
    ).all()
    
    candidates_data = []
    for app in applications:
        candidate = app.candidate
        if not candidate:
            continue
        
        # Parse resume if available
        resume_data = {}
        if candidate.resume_url:
            resume_data = parse_resume(candidate.resume_url) or {}
        
        # Build candidate profile for matching
        candidate_profile = {
            "text": f"{candidate.current_title or ''} {candidate.current_company or ''}",
            "skills": (candidate.profile.skills or "").split(",") if candidate.profile and candidate.profile.skills else [],
            "experience": {
                "years": candidate.total_experience_years or 0,
                "job_titles": [candidate.current_title] if candidate.current_title else [],
                "companies": [candidate.current_company] if candidate.current_company else [],
            },
        }
        
        # Merge with parsed resume data
        candidate_profile.update(resume_data)
        candidates_data.append(candidate_profile)
    
    # Rank candidates using AI
    ranked_results = rank_candidates(job_text, candidates_data)
    
    # Update application match scores
    for idx, result in enumerate(ranked_results):
        if idx < len(applications):
            applications[idx].match_score = result["match_score"]
    
    db.commit()
    
    return [
        schemas.RankedCandidate(
            candidate_index=r["candidate_index"],
            combined_score=r["combined_score"],
            match_score=r["match_score"],
            skills=r["skills"],
            experience_years=r["experience_years"],
            education=r["education"],
        )
        for r in ranked_results
    ]


@router.get("/analytics/dashboard")
def get_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Get comprehensive dashboard analytics for recruiters."""
    analytics = get_dashboard_analytics(db, days)
    return analytics

"""
Advanced application routes with AI-powered features.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.utils.ai_resume_parser import calculate_job_candidate_match, parse_resume
from app.utils.dependencies import get_current_user, get_db, require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("", response_model=schemas.ApplicationRead, status_code=status.HTTP_201_CREATED)
def apply_job(
    payload: schemas.ApplicationCreate,
    current_user: models.UserCredential = Depends(require_role("candidate")),
    db: Session = Depends(get_db),
):
    """
    Apply for a job with cover letter and automatic resume matching.
    """
    job = db.query(models.Job).options(
        joinedload(models.Job.recruiter)
    ).filter(models.Job.job_id == payload.job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "Open":
        raise HTTPException(status_code=400, detail="Applications are closed for this job")

    # Check for duplicate application
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

    # Get candidate data for matching
    candidate = current_user.candidate
    resume_data = {}
    if candidate and candidate.resume_url:
        resume_data = parse_resume(candidate.resume_url) or {}
    
    # Calculate match score
    job_description = f"{job.title} {job.description or ''} {job.requirements or ''}"
    match_result = calculate_job_candidate_match(job_description, resume_data) if resume_data else {}
    
    # Create application
    application = models.Application(
        job_id=payload.job_id,
        candidate_id=current_user.candidate_id,
        status="Applied",
        cover_letter=payload.cover_letter,
        applied_via=payload.applied_via,
        referral_code=payload.referral_code,
        match_score=match_result.get("match_score"),
        resume_score=resume_data.get("score"),
    )
    db.add(application)
    
    # Increment job applications count
    if job:
        job.applications_count += 1
    
    db.commit()
    db.refresh(application)
    
    logger.info(f"Application created: {application.application_id} by candidate {current_user.candidate_id}")
    
    # TODO: Send email notification to candidate and recruiter
    
    return schemas.ApplicationRead(
        application_id=application.application_id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        status=application.status,
        match_score=application.match_score,
        screening_score=application.screening_score,
        resume_score=application.resume_score,
        cover_letter=application.cover_letter,
        created_at=application.created_at,
        job_title=job.title if job else None,
    )


@router.get("", response_model=list[schemas.ApplicationRead])
def get_applications(
    job_id: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get applications - role-based access.
    - Candidates: See their own applications
    - Recruiters: See applications for their jobs
    """
    query = db.query(models.Application)
    
    if current_user.role == "recruiter":
        # Recruiter sees applications for their jobs
        query = query.join(models.Job).filter(
            models.Job.recruiter_id == current_user.recruiter_id
        )
        if job_id:
            query = query.filter(models.Application.job_id == job_id)
    else:
        # Candidate sees their own applications
        query = query.filter(models.Application.candidate_id == current_user.candidate_id)
        if job_id:
            query = query.filter(models.Application.job_id == job_id)
    
    # Apply status filter
    if status_filter:
        query = query.filter(models.Application.status == status_filter)
    
    # Order by most recent
    query = query.order_by(models.Application.created_at.desc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    applications = query.offset(offset).limit(page_size).all()
    
    response = []
    for app in applications:
        response.append(
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
                job_title=app.job.title if app.job else None,
                candidate_name=app.candidate.full_name if app.candidate else None,
                candidate_email=app.candidate.email if app.candidate else None,
                candidate_phone=app.candidate.phone if app.candidate else None,
                candidate_resume_url=app.candidate.resume_url if app.candidate else None,
            )
        )
    return response


@router.get("/{application_id}", response_model=schemas.ApplicationRead)
def get_application(
    application_id: int,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific application by ID."""
    application = db.query(models.Application).options(
        joinedload(models.Application.job),
        joinedload(models.Application.candidate)
    ).filter(models.Application.application_id == application_id).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check permissions
    if current_user.role == "candidate":
        if application.candidate_id != current_user.candidate_id:
            raise HTTPException(status_code=403, detail="Not allowed to view this application")
    elif current_user.role == "recruiter":
        if not application.job or application.job.recruiter_id != current_user.recruiter_id:
            raise HTTPException(status_code=403, detail="Not allowed to view this application")
    
    return schemas.ApplicationRead(
        application_id=application.application_id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        status=application.status,
        match_score=application.match_score,
        screening_score=application.screening_score,
        resume_score=application.resume_score,
        cover_letter=application.cover_letter,
        recruiter_notes=application.recruiter_notes,
        rejection_reason=application.rejection_reason,
        created_at=application.created_at,
        updated_at=application.updated_at,
        reviewed_at=application.reviewed_at,
        job_title=application.job.title if application.job else None,
        candidate_name=application.candidate.full_name if application.candidate else None,
        candidate_email=application.candidate.email if application.candidate else None,
        candidate_phone=application.candidate.phone if application.candidate else None,
        candidate_resume_url=application.candidate.resume_url if application.candidate else None,
    )


@router.put("/{application_id}/status", response_model=schemas.ApplicationRead)
def update_application_status(
    application_id: int,
    payload: schemas.ApplicationStatusUpdate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """
    Update application status (recruiter only).
    Sends email notification to candidate on status change.
    """
    application = db.query(models.Application).options(
        joinedload(models.Application.job),
        joinedload(models.Application.candidate)
    ).filter(models.Application.application_id == application_id).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.job or application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to manage this application")
    
    # Store old status for notification
    old_status = application.status
    
    # Update application
    application.status = payload.status
    if payload.recruiter_notes:
        application.recruiter_notes = payload.recruiter_notes
    if payload.rejection_reason and payload.status == "Rejected":
        application.rejection_reason = payload.rejection_reason
    application.reviewed_at = datetime.now()
    
    db.commit()
    db.refresh(application)
    
    logger.info(f"Application {application_id} status updated from {old_status} to {payload.status}")
    
    # TODO: Send email notification to candidate about status change
    
    return schemas.ApplicationRead(
        application_id=application.application_id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        status=application.status,
        match_score=application.match_score,
        screening_score=application.screening_score,
        resume_score=application.resume_score,
        cover_letter=application.cover_letter,
        recruiter_notes=application.recruiter_notes,
        rejection_reason=application.rejection_reason,
        created_at=application.created_at,
        updated_at=application.updated_at,
        reviewed_at=application.reviewed_at,
        job_title=application.job.title if application.job else None,
        candidate_name=application.candidate.full_name if application.candidate else None,
        candidate_email=application.candidate.email if application.candidate else None,
    )


@router.put("/{application_id}/screening", response_model=schemas.ApplicationRead)
def screen_application(
    application_id: int,
    payload: schemas.ApplicationStatusUpdate,
    current_user: models.UserCredential = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """
    Screen application and add screening score (recruiter only).
    """
    application = db.query(models.Application).options(
        joinedload(models.Application.job)
    ).filter(models.Application.application_id == application_id).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.job or application.job.recruiter_id != current_user.recruiter_id:
        raise HTTPException(status_code=403, detail="Not allowed to manage this application")
    
    # Update screening score if provided
    if payload.recruiter_notes:
        # Extract score from notes if it contains a numeric score
        import re
        score_match = re.search(r'score[:\s]*(\d+)', payload.recruiter_notes.lower())
        if score_match:
            application.screening_score = float(score_match.group(1))
    
    application.status = payload.status
    application.reviewed_at = datetime.now()
    
    db.commit()
    db.refresh(application)
    
    return schemas.ApplicationRead(
        application_id=application.application_id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        status=application.status,
        match_score=application.match_score,
        screening_score=application.screening_score,
        created_at=application.created_at,
        job_title=application.job.title if application.job else None,
        candidate_name=application.candidate.full_name if application.candidate else None,
    )


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an application.
    - Candidates can delete their own applications
    - Recruiters can delete applications for their jobs
    """
    application = db.query(models.Application).options(
        joinedload(models.Application.job)
    ).filter(models.Application.application_id == application_id).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check permissions
    can_delete = False
    if current_user.role == "candidate" and application.candidate_id == current_user.candidate_id:
        can_delete = True
    elif current_user.role == "recruiter" and application.job and application.job.recruiter_id == current_user.recruiter_id:
        can_delete = True
    
    if not can_delete:
        raise HTTPException(status_code=403, detail="Not allowed to delete this application")
    
    db.delete(application)
    db.commit()
    
    logger.info(f"Application {application_id} deleted by user {current_user.credential_id}")


@router.get("/{application_id}/match-analysis")
def get_application_match_analysis(
    application_id: int,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed AI-powered match analysis for an application.
    Shows how well the candidate matches the job requirements.
    """
    application = db.query(models.Application).options(
        joinedload(models.Application.job),
        joinedload(models.Application.candidate)
    ).filter(models.Application.application_id == application_id).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check permissions
    if current_user.role == "candidate":
        if application.candidate_id != current_user.candidate_id:
            raise HTTPException(status_code=403, detail="Not allowed to view this application")
    elif current_user.role == "recruiter":
        if not application.job or application.job.recruiter_id != current_user.recruiter_id:
            raise HTTPException(status_code=403, detail="Not allowed to view this application")
    
    # Get job and candidate data
    job = application.job
    candidate = application.candidate
    
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate not found")
    
    # Parse resume
    resume_data = {}
    if candidate.resume_url:
        resume_data = parse_resume(candidate.resume_url) or {}
    
    # Calculate match
    job_description = f"{job.title} {job.description or ''} {job.requirements or ''}"
    match_result = calculate_job_candidate_match(job_description, resume_data) if resume_data else {}
    
    return {
        "application_id": application_id,
        "job_id": job.job_id,
        "job_title": job.title,
        "candidate_id": candidate.candidate_id,
        "candidate_name": candidate.full_name,
        "match_score": match_result.get("match_score", 0),
        "skill_match_percentage": match_result.get("skill_match_percentage", 0),
        "experience_match_percentage": match_result.get("experience_match_percentage", 0),
        "matched_skills": match_result.get("matched_skills", []),
        "missing_skills": match_result.get("missing_skills", []),
        "candidate_skills": match_result.get("candidate_skills", []),
        "required_skills": match_result.get("required_skills", []),
        "recommendation": get_recommendation(match_result.get("match_score", 0)),
    }


def get_recommendation(match_score: float) -> str:
    """Get recommendation based on match score."""
    if match_score >= 80:
        return "Highly Recommended"
    elif match_score >= 60:
        return "Recommended"
    elif match_score >= 40:
        return "Consider"
    else:
        return "Not Recommended"

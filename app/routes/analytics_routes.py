"""
Advanced analytics and reporting routes.
"""
import io
import logging
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models
from app.utils.analytics import (
    generate_activity_report,
    get_candidate_analytics,
    get_dashboard_analytics,
    get_recruiter_analytics,
)
from app.utils.dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def get_dashboard(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive dashboard analytics.
    - Admin: See platform-wide analytics
    - Recruiter: See analytics for their jobs
    - Candidate: See personal analytics
    """
    if current_user.role == "admin":
        # Admin sees platform-wide analytics
        return get_dashboard_analytics(db, days)
    
    elif current_user.role == "recruiter":
        # Recruiter sees their own analytics
        recruiter_analytics = get_recruiter_analytics(db, current_user.recruiter_id)
        
        # Add platform comparison metrics (anonymized)
        platform_stats = get_dashboard_analytics(db, days)
        
        return {
            **recruiter_analytics,
            "platform_benchmarks": {
                "average_applications_per_job": round(
                    platform_stats["overview"]["total_applications"] / 
                    max(platform_stats["overview"]["total_jobs"], 1),
                    2
                ),
                "average_time_to_hire_days": platform_stats["average_time_to_hire_days"],
                "overall_conversion_rate": platform_stats["funnel_metrics"]["overall_conversion_rate"],
            },
        }
    
    else:
        # Candidate sees their own analytics
        return get_candidate_analytics(db, current_user.candidate_id)


@router.get("/activity-report")
def get_activity_report(
    start_date: Optional[datetime] = Query(
        None,
        description="Start date (ISO format). Defaults to 30 days ago."
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date (ISO format). Defaults to today."
    ),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate activity report for a specific period.
    """
    if current_user.role != "admin" and current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only admin and recruiter users can access activity reports"
        )
    
    report = generate_activity_report(db, start_date, end_date)
    
    if current_user.role == "recruiter":
        # Filter report to only include recruiter's data
        recruiter_report = get_recruiter_analytics(db, current_user.recruiter_id)
        report["recruiter_summary"] = recruiter_report
    
    return report


@router.get("/funnel")
def get_recruitment_funnel(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get recruitment funnel metrics showing conversion rates at each stage.
    """
    from sqlalchemy import func
    
    if current_user.role == "recruiter":
        # Get funnel for recruiter's jobs
        query = db.query(models.Application.status, func.count(models.Application.application_id))
        query = query.join(models.Job).filter(
            models.Job.recruiter_id == current_user.recruiter_id
        )
        query = query.group_by(models.Application.status)
        status_counts = dict(query.all())
    else:
        # Platform-wide funnel (admin only)
        if current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only recruiters and admins can access funnel metrics"
            )
        
        query = db.query(models.Application.status, func.count(models.Application.application_id))
        query = query.group_by(models.Application.status)
        status_counts = dict(query.all())
    
    total = sum(status_counts.values())
    
    funnel = {
        "applied": status_counts.get("Applied", 0),
        "screening": status_counts.get("Screening", 0),
        "interviewing": status_counts.get("Interviewing", 0),
        "hired": status_counts.get("Hired", 0),
        "rejected": status_counts.get("Rejected", 0),
    }
    
    # Calculate conversion rates
    conversion_rates = {
        "application_to_screening": round(
            (funnel["screening"] / funnel["applied"] * 100) if funnel["applied"] > 0 else 0,
            2
        ),
        "screening_to_interview": round(
            (funnel["interviewing"] / funnel["screening"] * 100) if funnel["screening"] > 0 else 0,
            2
        ),
        "interview_to_hire": round(
            (funnel["hired"] / funnel["interviewing"] * 100) if funnel["interviewing"] > 0 else 0,
            2
        ),
        "overall_conversion": round(
            (funnel["hired"] / funnel["applied"] * 100) if funnel["applied"] > 0 else 0,
            2
        ),
    }
    
    return {
        "funnel": funnel,
        "conversion_rates": conversion_rates,
        "total_applications": total,
    }


@router.get("/jobs/performance")
def get_job_performance(
    job_id: Optional[int] = Query(None),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get job performance metrics.
    - If job_id provided: metrics for specific job
    - Otherwise: metrics for all recruiter's jobs
    """
    from sqlalchemy import func
    
    if current_user.role != "recruiter" and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters and admins can access job performance metrics"
        )
    
    query = db.query(
        models.Job.job_id,
        models.Job.title,
        models.Job.department,
        models.Job.location,
        func.count(models.Application.application_id).label('applications'),
        func.count(models.Interview.interview_id).label('interviews'),
    )
    query = query.outerjoin(models.Application)
    query = query.outerjoin(models.Interview)
    
    if job_id:
        query = query.filter(models.Job.job_id == job_id)
    
    if current_user.role == "recruiter":
        query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
    
    query = query.group_by(models.Job.job_id)
    results = query.all()
    
    job_performance = []
    for row in results:
        job_id, title, department, location, applications, interviews = row
        job_performance.append({
            "job_id": job_id,
            "title": title,
            "department": department,
            "location": location,
            "applications": applications,
            "interviews": interviews,
            "application_to_interview_ratio": round(
                (interviews / applications * 100) if applications > 0 else 0,
                2
            ),
        })
    
    return {"jobs": job_performance}


@router.get("/candidates/pipeline")
def get_candidate_pipeline(
    status_filter: Optional[str] = Query(None),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get candidate pipeline metrics.
    Shows candidates at different stages of the recruitment process.
    """
    if current_user.role != "recruiter" and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters and admins can access candidate pipeline"
        )
    
    query = db.query(
        models.Candidate.candidate_id,
        models.Candidate.full_name,
        models.Candidate.email,
        models.Candidate.current_title,
        models.Candidate.current_company,
        models.Application.status,
        models.Job.title.label('job_title'),
    )
    query = query.join(models.Application)
    query = query.join(models.Job)
    
    if current_user.role == "recruiter":
        query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
    
    if status_filter:
        query = query.filter(models.Application.status == status_filter)
    
    query = query.order_by(models.Application.created_at.desc())
    results = query.all()
    
    pipeline = [
        {
            "candidate_id": r.candidate_id,
            "name": r.full_name,
            "email": r.email,
            "current_title": r.current_title,
            "current_company": r.current_company,
            "application_status": r.status,
            "job_title": r.job_title,
        }
        for r in results
    ]
    
    return {
        "pipeline": pipeline,
        "total_candidates": len(pipeline),
        "by_status": {
            "applied": sum(1 for p in pipeline if p["application_status"] == "Applied"),
            "screening": sum(1 for p in pipeline if p["application_status"] == "Screening"),
            "interviewing": sum(1 for p in pipeline if p["application_status"] == "Interviewing"),
            "hired": sum(1 for p in pipeline if p["application_status"] == "Hired"),
            "rejected": sum(1 for p in pipeline if p["application_status"] == "Rejected"),
        },
    }


@router.get("/time-to-hire")
def get_time_to_hire_metrics(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get time-to-hire metrics.
    Shows average time spent at each stage of recruitment.
    """
    from sqlalchemy import func
    
    if current_user.role != "recruiter" and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters and admins can access time-to-hire metrics"
        )
    
    # Get hired applications with timestamps
    query = db.query(
        models.Application.application_id,
        models.Application.created_at.label('applied_at'),
        models.Application.reviewed_at,
    )
    query = query.filter(models.Application.status == "Hired")
    
    if current_user.role == "recruiter":
        query = query.join(models.Job).filter(
            models.Job.recruiter_id == current_user.recruiter_id
        )
    
    hired_apps = query.all()
    
    if not hired_apps:
        return {
            "message": "No hired applications found",
            "metrics": None,
        }
    
    # Calculate time to hire for each application
    time_to_hire_days = []
    for app in hired_apps:
        if app.reviewed_at:
            days = (app.reviewed_at - app.applied_at).days
            time_to_hire_days.append(days)
    
    if not time_to_hire_days:
        return {
            "message": "No complete data found",
            "metrics": None,
        }
    
    avg_time = sum(time_to_hire_days) / len(time_to_hire_days)
    min_time = min(time_to_hire_days)
    max_time = max(time_to_hire_days)
    
    return {
        "average_days": round(avg_time, 2),
        "min_days": min_time,
        "max_days": max_time,
        "total_hired": len(time_to_hire_days),
        "distribution": {
            "less_than_7_days": sum(1 for d in time_to_hire_days if d < 7),
            "7_to_14_days": sum(1 for d in time_to_hire_days if 7 <= d < 14),
            "14_to_30_days": sum(1 for d in time_to_hire_days if 14 <= d < 30),
            "more_than_30_days": sum(1 for d in time_to_hire_days if d >= 30),
        },
    }


@router.get("/export")
def export_analytics(
    entity_type: Literal["jobs", "applications", "candidates", "interviews"] = Query(...),
    format: Literal["csv", "json"] = Query("csv"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export analytics data in CSV or JSON format.
    """
    import csv
    import json
    from io import StringIO
    
    if current_user.role not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only recruiters and admins can export data"
        )
    
    # Build query based on entity type
    if entity_type == "jobs":
        query = db.query(models.Job)
        if current_user.role == "recruiter":
            query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
        if start_date:
            query = query.filter(models.Job.created_at >= start_date)
        if end_date:
            query = query.filter(models.Job.created_at <= end_date)
        data = [
            {
                "job_id": j.job_id,
                "title": j.title,
                "department": j.department,
                "location": j.location,
                "status": j.status,
                "applications_count": j.applications_count,
                "created_at": str(j.created_at),
            }
            for j in query.all()
        ]
    
    elif entity_type == "applications":
        query = db.query(models.Application).join(models.Job)
        if current_user.role == "recruiter":
            query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
        if start_date:
            query = query.filter(models.Application.created_at >= start_date)
        if end_date:
            query = query.filter(models.Application.created_at <= end_date)
        data = [
            {
                "application_id": a.application_id,
                "job_id": a.job_id,
                "candidate_id": a.candidate_id,
                "status": a.status,
                "match_score": a.match_score,
                "created_at": str(a.created_at),
            }
            for a in query.all()
        ]
    
    elif entity_type == "candidates":
        query = db.query(models.Candidate)
        data = [
            {
                "candidate_id": c.candidate_id,
                "full_name": c.full_name,
                "email": c.email,
                "current_title": c.current_title,
                "current_company": c.current_company,
                "created_at": str(c.created_at),
            }
            for c in query.all()
        ]
    
    elif entity_type == "interviews":
        query = db.query(models.Interview).join(models.Application).join(models.Job)
        if current_user.role == "recruiter":
            query = query.filter(models.Job.recruiter_id == current_user.recruiter_id)
        if start_date:
            query = query.filter(models.Interview.scheduled_at >= start_date)
        if end_date:
            query = query.filter(models.Interview.scheduled_at <= end_date)
        data = [
            {
                "interview_id": i.interview_id,
                "application_id": i.application_id,
                "scheduled_at": str(i.scheduled_at),
                "interview_type": i.interview_type,
                "status": i.status,
                "interview_score": i.interview_score,
            }
            for i in query.all()
        ]
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    # Format response
    if format == "json":
        return {
            "entity_type": entity_type,
            "count": len(data),
            "data": data,
        }
    
    else:  # CSV
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={entity_type}_export.csv"
            },
        )

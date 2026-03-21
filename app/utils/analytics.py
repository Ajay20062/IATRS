"""
Advanced analytics and reporting utilities.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends
from sqlalchemy import Date, Float, Integer, String, and_, case, cast, extract, func
from sqlalchemy.orm import Session

from app import models
from app.utils.dependencies import get_db


def get_dashboard_analytics(db: Session, days: int = 30) -> dict:
    """Get comprehensive dashboard analytics."""
    date_threshold = datetime.now() - timedelta(days=days)
    
    # Overall statistics
    total_jobs = db.query(func.count(models.Job.job_id)).scalar() or 0
    active_jobs = db.query(func.count(models.Job.job_id)).filter(
        models.Job.status == "Open"
    ).scalar() or 0
    
    total_applications = db.query(func.count(models.Application.application_id)).scalar() or 0
    total_candidates = db.query(func.count(models.Candidate.candidate_id)).scalar() or 0
    total_recruiters = db.query(func.count(models.Recruiter.recruiter_id)).scalar() or 0
    total_interviews = db.query(func.count(models.Interview.interview_id)).scalar() or 0
    
    # Recent applications (last 30 days)
    recent_applications = db.query(func.count(models.Application.application_id)).filter(
        models.Application.created_at >= date_threshold
    ).scalar() or 0
    
    # Application status distribution
    status_distribution = db.query(
        models.Application.status,
        func.count(models.Application.application_id)
    ).group_by(models.Application.status).all()
    
    status_breakdown = {status: count for status, count in status_distribution}
    
    # Job status distribution
    job_status_distribution = db.query(
        models.Job.status,
        func.count(models.Job.job_id)
    ).group_by(models.Job.status).all()
    
    job_status_breakdown = {status: count for status, count in job_status_distribution}
    
    # Department distribution
    department_distribution = db.query(
        models.Job.department,
        func.count(models.Job.job_id)
    ).group_by(models.Job.department).all()
    
    department_breakdown = {dept: count for dept, count in department_distribution}
    
    # Location distribution
    location_distribution = db.query(
        models.Job.location,
        func.count(models.Job.job_id)
    ).group_by(models.Job.location).all()
    
    location_breakdown = {location: count for location, count in location_distribution}
    
    # Interview status distribution
    interview_status_distribution = db.query(
        models.Interview.status,
        func.count(models.Interview.interview_id)
    ).group_by(models.Interview.status).all()
    
    interview_status_breakdown = {status: count for status, count in interview_status_distribution}
    
    # Applications per day (last 30 days)
    applications_trend = db.query(
        cast(models.Application.created_at, Date).label('date'),
        func.count(models.Application.application_id)
    ).filter(
        models.Application.created_at >= date_threshold
    ).group_by(
        cast(models.Application.created_at, Date)
    ).order_by(
        cast(models.Application.created_at, Date)
    ).all()
    
    trend_data = {str(date): count for date, count in applications_trend}
    
    # Top recruiters by jobs posted
    top_recruiters = db.query(
        models.Recruiter.full_name,
        models.Recruiter.company,
        func.count(models.Job.job_id).label('job_count')
    ).join(
        models.Job
    ).group_by(
        models.Recruiter.recruiter_id
    ).order_by(
        func.count(models.Job.job_id).desc()
    ).limit(10).all()
    
    top_recruiters_list = [
        {"name": r.full_name, "company": r.company, "jobs_posted": count}
        for r, count in top_recruiters
    ]
    
    # Hiring funnel metrics
    applied_count = status_breakdown.get("Applied", 0)
    screening_count = status_breakdown.get("Screening", 0)
    interviewing_count = status_breakdown.get("Interviewing", 0)
    hired_count = status_breakdown.get("Hired", 0)
    
    funnel_metrics = {
        "applied": applied_count,
        "screening": screening_count,
        "interviewing": interviewing_count,
        "hired": hired_count,
        "application_to_screening_rate": round((screening_count / applied_count * 100) if applied_count > 0 else 0, 2),
        "screening_to_interview_rate": round((interviewing_count / screening_count * 100) if screening_count > 0 else 0, 2),
        "interview_to_hire_rate": round((hired_count / interviewing_count * 100) if interviewing_count > 0 else 0, 2),
        "overall_conversion_rate": round((hired_count / applied_count * 100) if applied_count > 0 else 0, 2),
    }
    
    # Time to hire (average days from application to hired)
    time_to_hire = db.query(
        func.avg(
            func.timestampdiff(
                "DAY",
                models.Application.created_at,
                func.now()
            )
        )
    ).join(
        models.Application
    ).filter(
        models.Application.status == "Hired"
    ).scalar()
    
    return {
        "overview": {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_applications": total_applications,
            "total_candidates": total_candidates,
            "total_recruiters": total_recruiters,
            "total_interviews": total_interviews,
            "recent_applications": recent_applications,
        },
        "status_breakdown": status_breakdown,
        "job_status_breakdown": job_status_breakdown,
        "department_breakdown": department_breakdown,
        "location_breakdown": location_breakdown,
        "interview_status_breakdown": interview_status_breakdown,
        "applications_trend": trend_data,
        "top_recruiters": top_recruiters_list,
        "funnel_metrics": funnel_metrics,
        "average_time_to_hire_days": round(time_to_hire, 2) if time_to_hire else 0,
    }


def get_recruiter_analytics(db: Session, recruiter_id: int) -> dict:
    """Get analytics specific to a recruiter."""
    # Jobs posted
    jobs_posted = db.query(func.count(models.Job.job_id)).filter(
        models.Job.recruiter_id == recruiter_id
    ).scalar() or 0
    
    active_jobs = db.query(func.count(models.Job.job_id)).filter(
        models.Job.recruiter_id == recruiter_id,
        models.Job.status == "Open"
    ).scalar() or 0
    
    # Total applications for recruiter's jobs
    total_applications = db.query(func.count(models.Application.application_id)).join(
        models.Job
    ).filter(
        models.Job.recruiter_id == recruiter_id
    ).scalar() or 0
    
    # Applications by status
    applications_by_status = db.query(
        models.Application.status,
        func.count(models.Application.application_id)
    ).join(
        models.Job
    ).filter(
        models.Job.recruiter_id == recruiter_id
    ).group_by(
        models.Application.status
    ).all()
    
    status_breakdown = {status: count for status, count in applications_by_status}
    
    # Interviews scheduled
    total_interviews = db.query(func.count(models.Interview.interview_id)).join(
        models.Application
    ).join(
        models.Job
    ).filter(
        models.Job.recruiter_id == recruiter_id
    ).scalar() or 0
    
    upcoming_interviews = db.query(func.count(models.Interview.interview_id)).join(
        models.Application
    ).join(
        models.Job
    ).filter(
        models.Job.recruiter_id == recruiter_id,
        models.Interview.status == "Scheduled",
        models.Interview.scheduled_at >= datetime.now()
    ).scalar() or 0
    
    # Top performing jobs (by applications)
    top_jobs = db.query(
        models.Job.job_id,
        models.Job.title,
        func.count(models.Application.application_id).label('application_count')
    ).join(
        models.Application
    ).filter(
        models.Job.recruiter_id == recruiter_id
    ).group_by(
        models.Job.job_id
    ).order_by(
        func.count(models.Application.application_id).desc()
    ).limit(5).all()
    
    top_jobs_list = [
        {"job_id": job_id, "title": title, "applications": count}
        for job_id, title, count in top_jobs
    ]
    
    # Recent applications (last 7 days)
    recent_applications = db.query(func.count(models.Application.application_id)).join(
        models.Job
    ).filter(
        models.Job.recruiter_id == recruiter_id,
        models.Application.created_at >= datetime.now() - timedelta(days=7)
    ).scalar() or 0
    
    return {
        "jobs_posted": jobs_posted,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "applications_by_status": status_breakdown,
        "total_interviews": total_interviews,
        "upcoming_interviews": upcoming_interviews,
        "top_jobs": top_jobs_list,
        "recent_applications": recent_applications,
    }


def get_candidate_analytics(db: Session, candidate_id: int) -> dict:
    """Get analytics specific to a candidate."""
    # Total applications
    total_applications = db.query(func.count(models.Application.application_id)).filter(
        models.Application.candidate_id == candidate_id
    ).scalar() or 0
    
    # Applications by status
    applications_by_status = db.query(
        models.Application.status,
        func.count(models.Application.application_id)
    ).filter(
        models.Application.candidate_id == candidate_id
    ).group_by(
        models.Application.status
    ).all()
    
    status_breakdown = {status: count for status, count in applications_by_status}
    
    # Total interviews
    total_interviews = db.query(func.count(models.Interview.interview_id)).join(
        models.Application
    ).filter(
        models.Application.candidate_id == candidate_id
    ).scalar() or 0
    
    upcoming_interviews = db.query(func.count(models.Interview.interview_id)).join(
        models.Application
    ).filter(
        models.Application.candidate_id == candidate_id,
        models.Interview.status == "Scheduled",
        models.Interview.scheduled_at >= datetime.now()
    ).scalar() or 0
    
    # Interview by type
    interviews_by_type = db.query(
        models.Interview.interview_type,
        func.count(models.Interview.interview_id)
    ).join(
        models.Application
    ).filter(
        models.Application.candidate_id == candidate_id
    ).group_by(
        models.Interview.interview_type
    ).all()
    
    interview_type_breakdown = {int_type: count for int_type, count in interviews_by_type}
    
    # Application success rate
    hired_count = status_breakdown.get("Hired", 0)
    success_rate = round((hired_count / total_applications * 100) if total_applications > 0 else 0, 2)
    
    # Recent applications (last 30 days)
    recent_applications = db.query(func.count(models.Application.application_id)).filter(
        models.Application.candidate_id == candidate_id,
        models.Application.created_at >= datetime.now() - timedelta(days=30)
    ).scalar() or 0
    
    # Jobs applied to
    jobs_applied = db.query(
        models.Job.job_id,
        models.Job.title,
        models.Job.company,
        models.Application.status,
        models.Application.created_at
    ).join(
        models.Application
    ).filter(
        models.Application.candidate_id == candidate_id
    ).order_by(
        models.Application.created_at.desc()
    ).limit(10).all()
    
    recent_jobs_list = [
        {
            "job_id": job_id,
            "title": title,
            "status": status,
            "applied_date": str(applied_date),
        }
        for job_id, title, _, status, applied_date in jobs_applied
    ]
    
    return {
        "total_applications": total_applications,
        "applications_by_status": status_breakdown,
        "total_interviews": total_interviews,
        "upcoming_interviews": upcoming_interviews,
        "interview_type_breakdown": interview_type_breakdown,
        "success_rate": success_rate,
        "recent_applications": recent_applications,
        "recent_jobs": recent_jobs_list,
    }


def generate_activity_report(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict:
    """Generate activity report for a given period."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    
    # New jobs posted
    new_jobs = db.query(func.count(models.Job.job_id)).filter(
        models.Job.created_at.between(start_date, end_date)
    ).scalar() or 0
    
    # New applications
    new_applications = db.query(func.count(models.Application.application_id)).filter(
        models.Application.created_at.between(start_date, end_date)
    ).scalar() or 0
    
    # New candidates
    new_candidates = db.query(func.count(models.Candidate.candidate_id)).filter(
        models.Candidate.created_at.between(start_date, end_date)
    ).scalar() or 0
    
    # New recruiters
    new_recruiters = db.query(func.count(models.Recruiter.recruiter_id)).filter(
        models.Recruiter.created_at.between(start_date, end_date)
    ).scalar() or 0
    
    # Interviews conducted
    interviews_conducted = db.query(func.count(models.Interview.interview_id)).filter(
        models.Interview.created_at.between(start_date, end_date),
        models.Interview.status == "Completed"
    ).scalar() or 0
    
    # Hires made
    hires_made = db.query(func.count(models.Application.application_id)).filter(
        models.Application.created_at.between(start_date, end_date),
        models.Application.status == "Hired"
    ).scalar() or 0
    
    # Most active departments
    active_departments = db.query(
        models.Job.department,
        func.count(models.Application.application_id).label('application_count')
    ).join(
        models.Application
    ).filter(
        models.Application.created_at.between(start_date, end_date)
    ).group_by(
        models.Job.department
    ).order_by(
        func.count(models.Application.application_id).desc()
    ).limit(5).all()
    
    department_activity = {dept: count for dept, count in active_departments}
    
    return {
        "period": {
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
        "summary": {
            "new_jobs": new_jobs,
            "new_applications": new_applications,
            "new_candidates": new_candidates,
            "new_recruiters": new_recruiters,
            "interviews_conducted": interviews_conducted,
            "hires_made": hires_made,
        },
        "department_activity": department_activity,
    }

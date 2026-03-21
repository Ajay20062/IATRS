"""
Advanced Pydantic schemas for the IATRS API.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============ Authentication Schemas ============

class CandidateSignup(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    current_title: Optional[str] = None
    current_company: Optional[str] = None


class RecruiterSignup(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    company: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=8, max_length=128)
    designation: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["candidate", "recruiter", "admin"]
    expires_in: int = 3600


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class CurrentUserRead(BaseModel):
    role: Literal["candidate", "recruiter", "admin"]
    email: EmailStr
    full_name: str
    candidate_id: Optional[int] = None
    recruiter_id: Optional[int] = None
    company: Optional[str] = None
    is_verified: bool = False
    is_2fa_enabled: bool = False


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class Verify2FARequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class AdminSignup(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=128)


# ============ User Schemas ============

class RecruiterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recruiter_id: int
    full_name: str
    email: EmailStr
    company: str
    created_at: datetime


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int
    full_name: str
    email: EmailStr
    phone: str
    resume_url: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    total_experience_years: Optional[float] = None
    expected_salary: Optional[int] = None
    profile_score: Optional[int] = None
    created_at: datetime


# ============ Job Schemas ============

class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=2, max_length=120)
    work_mode: Optional[Literal["Remote", "Hybrid", "Onsite"]] = "Hybrid"
    
    # Compensation
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_currency: Optional[str] = "USD"
    salary_period: Optional[str] = "YEAR"
    
    # Requirements
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    min_experience_years: Optional[int] = None
    max_experience_years: Optional[int] = None
    education_level: Optional[str] = None
    
    status: Literal["Open", "Closed", "Paused"] = "Open"
    is_featured: bool = False
    expires_at: Optional[datetime] = None


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[Literal["Remote", "Hybrid", "Onsite"]] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    min_experience_years: Optional[int] = None
    status: Optional[Literal["Open", "Closed", "Paused"]] = None
    is_featured: Optional[bool] = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    recruiter_id: int
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: str
    location: str
    work_mode: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    min_experience_years: Optional[int] = None
    max_experience_years: Optional[int] = None
    education_level: Optional[str] = None
    status: str
    is_featured: bool = False
    is_remote_friendly: bool = False
    views_count: int = 0
    applications_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    recruiter_name: Optional[str] = None
    recruiter_company: Optional[str] = None


class JobSearchFilters(BaseModel):
    search: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    work_mode: Optional[Literal["Remote", "Hybrid", "Onsite"]] = None
    status_filter: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    required_skills: Optional[str] = None
    min_experience_years: Optional[int] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


# ============ Application Schemas ============

class ApplicationCreate(BaseModel):
    job_id: int
    cover_letter: Optional[str] = None
    applied_via: Optional[str] = "website"
    referral_code: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: Literal["Applied", "Screening", "Interviewing", "Rejected", "Hired"]
    recruiter_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    job_id: int
    candidate_id: int
    status: str
    match_score: Optional[float] = None
    screening_score: Optional[float] = None
    resume_score: Optional[int] = None
    cover_letter: Optional[str] = None
    recruiter_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    job_title: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    candidate_resume_url: Optional[str] = None


class ApplicationFilters(BaseModel):
    job_id: Optional[int] = None
    status: Optional[str] = None
    candidate_name: Optional[str] = None
    page: int = 1
    page_size: int = 20


# ============ Interview Schemas ============

class InterviewCreate(BaseModel):
    application_id: int
    scheduled_at: datetime
    end_time: Optional[datetime] = None
    interview_type: Literal["Phone", "Video", "Onsite"]
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None
    interview_link: Optional[str] = None
    location_address: Optional[str] = None
    interview_notes: Optional[str] = None


class InterviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interview_type: Optional[Literal["Phone", "Video", "Onsite"]] = None
    status: Optional[Literal["Scheduled", "Completed", "Cancelled", "No-Show"]] = None
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None
    interview_link: Optional[str] = None
    interview_notes: Optional[str] = None
    feedback: Optional[str] = None
    interview_score: Optional[int] = Field(None, ge=0, le=100)
    recommendation: Optional[Literal["Hire", "No Hire", "Maybe"]] = None
    technical_score: Optional[int] = Field(None, ge=0, le=100)
    communication_score: Optional[int] = Field(None, ge=0, le=100)
    cultural_fit_score: Optional[int] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[int] = Field(None, ge=0, le=100)


class InterviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interview_id: int
    application_id: int
    scheduled_at: datetime
    end_time: Optional[datetime] = None
    interview_type: str
    status: str
    interview_link: Optional[str] = None
    location_address: Optional[str] = None
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None
    interview_notes: Optional[str] = None
    feedback: Optional[str] = None
    interview_score: Optional[int] = None
    recommendation: Optional[str] = None
    technical_score: Optional[int] = None
    communication_score: Optional[int] = None
    cultural_fit_score: Optional[int] = None
    problem_solving_score: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_title: Optional[str] = None


class InterviewFeedbackSubmit(BaseModel):
    interview_score: int = Field(..., ge=0, le=100)
    recommendation: Literal["Hire", "No Hire", "Maybe"]
    feedback: str
    technical_score: Optional[int] = Field(None, ge=0, le=100)
    communication_score: Optional[int] = Field(None, ge=0, le=100)
    cultural_fit_score: Optional[int] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[int] = Field(None, ge=0, le=100)


# ============ Profile Schemas ============

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    bio: Optional[str] = Field(None, max_length=2000)
    skills: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    designation: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    social_links: Optional[str] = None  # JSON string
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    total_experience_years: Optional[float] = None
    expected_salary: Optional[int] = None
    notice_period_days: Optional[int] = None
    preferred_locations: Optional[str] = None
    preferred_work_mode: Optional[Literal["Remote", "Hybrid", "Onsite"]] = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: Literal["candidate", "recruiter", "admin"]
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    profile_image: Optional[str] = None
    skills: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    resume_path: Optional[str] = None
    bio: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    designation: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    social_links: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    total_experience_years: Optional[float] = None
    expected_salary: Optional[int] = None
    notice_period_days: Optional[int] = None
    preferred_locations: Optional[str] = None
    preferred_work_mode: Optional[str] = None
    notifications_enabled: bool = True
    profile_views: int = 0
    profile_completeness: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    profile_completion_percentage: int


class ProfileStatsRead(BaseModel):
    applications_count: int
    interviews_attended: int
    interviews_scheduled: int
    jobs_applied: int
    profile_views: int
    profile_completion_percentage: int
    applications_by_status: dict


class ResumeAnalysisRead(BaseModel):
    extracted_keywords: list[str]
    resume_score: int
    match_score: Optional[float] = None
    missing_skills: list[str] = []
    suggested_improvements: list[str] = []


# ============ Analytics Schemas ============

class DashboardAnalytics(BaseModel):
    total_jobs: int
    active_jobs: int
    total_applications: int
    total_candidates: int
    total_recruiters: int
    total_interviews: int
    recent_applications: int
    status_breakdown: dict
    job_status_breakdown: dict
    department_breakdown: dict
    location_breakdown: dict
    interview_status_breakdown: dict
    applications_trend: dict
    top_recruiters: list[dict]
    funnel_metrics: dict
    average_time_to_hire_days: float


class RecruiterAnalytics(BaseModel):
    jobs_posted: int
    active_jobs: int
    total_applications: int
    applications_by_status: dict
    total_interviews: int
    upcoming_interviews: int
    top_jobs: list[dict]
    recent_applications: int


class CandidateAnalytics(BaseModel):
    total_applications: int
    applications_by_status: dict
    total_interviews: int
    upcoming_interviews: int
    interview_type_breakdown: dict
    success_rate: float
    recent_applications: int
    recent_jobs: list[dict]


# ============ Notification Schemas ============

class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    user_id: int
    user_type: str
    title: str
    message: str
    notification_type: str
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationMarkAsRead(BaseModel):
    notification_ids: list[int]


# ============ Job Template Schemas ============

class JobTemplateCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: str = Field(..., min_length=2, max_length=100)
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    min_experience_years: Optional[int] = None
    education_level: Optional[str] = None
    is_public: bool = False


class JobTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: int
    recruiter_id: int
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: str
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    min_experience_years: Optional[int] = None
    education_level: Optional[str] = None
    is_public: bool
    usage_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============ AI Matching Schemas ============

class JobCandidateMatch(BaseModel):
    match_score: float
    skill_match_percentage: float
    experience_match_percentage: float
    matched_skills: list[str]
    missing_skills: list[str]
    candidate_skills: list[str]
    required_skills: list[str]
    recommendation: str  # "Highly Recommended", "Recommended", "Consider", "Not Recommended"


class RankedCandidate(BaseModel):
    candidate_index: int
    candidate_id: Optional[int] = None
    candidate_name: Optional[str] = None
    combined_score: float
    match_score: float
    skills: list[str]
    experience_years: float
    education: list[dict]
    resume_score: Optional[int] = None


# ============ Export/Report Schemas ============

class ExportRequest(BaseModel):
    entity_type: Literal["jobs", "applications", "candidates", "interviews"]
    format: Literal["csv", "excel", "pdf"]
    filters: Optional[dict] = None


class ReportGenerationRequest(BaseModel):
    report_type: Literal["activity", "funnel", "recruiter_performance", "candidate_pipeline"]
    start_date: datetime
    end_date: datetime
    format: Literal["pdf", "excel"] = "pdf"
    filters: Optional[dict] = None


# ============ Pagination ============

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

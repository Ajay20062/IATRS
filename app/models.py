from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


job_status_enum = Enum("Open", "Closed", "Paused", name="job_status", native_enum=False)
application_status_enum = Enum(
    "Applied",
    "Screening",
    "Interviewing",
    "Rejected",
    "Hired",
    name="application_status",
    native_enum=False,
)
interview_type_enum = Enum("Phone", "Video", "Onsite", name="interview_type", native_enum=False)
interview_status_enum = Enum(
    "Scheduled",
    "Completed",
    "Cancelled",
    "No-Show",
    name="interview_status",
    native_enum=False,
)
role_enum = Enum("candidate", "recruiter", "admin", name="user_role", native_enum=False)
work_mode_enum = Enum("Remote", "Hybrid", "Onsite", name="work_mode", native_enum=False)


class Recruiter(Base):
    __tablename__ = "recruiters"

    recruiter_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    company = Column(String(150), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")
    credential = relationship("UserCredential", back_populates="recruiter", uselist=False)

    __table_args__ = (
        Index("ix_recruiters_email", "email"),
        Index("ix_recruiters_company", "company"),
    )


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id"), nullable=False)
    title = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    department = Column(String(100), nullable=False, index=True)
    location = Column(String(120), nullable=False, index=True)
    work_mode = Column(work_mode_enum, nullable=True, default="Hybrid")
    
    # Salary range
    min_salary = Column(Integer, nullable=True)
    max_salary = Column(Integer, nullable=True)
    salary_currency = Column(String(10), nullable=True, default="USD")
    salary_period = Column(String(20), nullable=True, default="YEAR")
    
    # Skills required (comma-separated or JSON)
    required_skills = Column(Text, nullable=True)
    preferred_skills = Column(Text, nullable=True)
    
    # Experience requirements
    min_experience_years = Column(Integer, nullable=True)
    max_experience_years = Column(Integer, nullable=True)
    
    # Education requirements
    education_level = Column(String(50), nullable=True)  # Bachelors, Masters, PhD, etc.
    
    # Job metadata
    status = Column(job_status_enum, nullable=False, default="Open", server_default="Open")
    is_featured = Column(Boolean, default=False, server_default="0")
    is_remote_friendly = Column(Boolean, default=False, server_default="0")
    views_count = Column(Integer, default=0, server_default="0")
    applications_count = Column(Integer, default=0, server_default="0")
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    expires_at = Column(DateTime, nullable=True)

    recruiter = relationship("Recruiter", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_jobs_title_fulltext", "title"),
        Index("ix_jobs_department_status", "department", "status"),
        Index("ix_jobs_location_status", "location", "status"),
    )


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    resume_url = Column(String(300), nullable=True)
    
    # Additional candidate metadata
    current_title = Column(String(150), nullable=True)
    current_company = Column(String(150), nullable=True)
    total_experience_years = Column(Float, nullable=True)
    expected_salary = Column(Integer, nullable=True)
    notice_period_days = Column(Integer, nullable=True)
    preferred_locations = Column(Text, nullable=True)
    preferred_work_mode = Column(work_mode_enum, nullable=True)
    
    # Profile scoring
    profile_score = Column(Integer, default=0, server_default="0")
    is_verified = Column(Boolean, default=False, server_default="0")
    is_active = Column(Boolean, default=True, server_default="1")
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    credential = relationship("UserCredential", back_populates="candidate", uselist=False)
    
    __table_args__ = (
        Index("ix_candidates_email", "email"),
        Index("ix_candidates_current_title", "current_title"),
        Index("ix_candidates_current_company", "current_company"),
    )


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),
        Index("ix_applications_status", "status"),
        Index("ix_applications_created_at", "created_at"),
        Index("ix_applications_job_status", "job_id", "status"),
    )

    application_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    status = Column(
        application_status_enum,
        nullable=False,
        default="Applied",
        server_default="Applied",
    )
    
    # Application scoring and matching
    match_score = Column(Float, nullable=True)  # AI-calculated match score
    screening_score = Column(Float, nullable=True)  # Manual screening score
    resume_score = Column(Integer, nullable=True)  # Resume parsing score
    
    # Application metadata
    cover_letter = Column(Text, nullable=True)
    applied_via = Column(String(50), nullable=True, default="website")  # website, referral, linkedin, etc.
    referral_code = Column(String(50), nullable=True)
    
    # Recruiter notes
    recruiter_notes = Column(Text, nullable=True)
    rejection_reason = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Foreign keys
    job = relationship("Job", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")


class Interview(Base):
    __tablename__ = "interviews"

    interview_id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.application_id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    interview_type = Column(interview_type_enum, nullable=False)
    status = Column(
        interview_status_enum,
        nullable=False,
        default="Scheduled",
        server_default="Scheduled",
    )
    
    # Interview details
    interview_link = Column(String(500), nullable=True)  # Video call link
    location_address = Column(String(500), nullable=True)  # For onsite interviews
    interview_notes = Column(Text, nullable=True)
    
    # Interviewer information
    interviewer_name = Column(String(150), nullable=True)
    interviewer_email = Column(String(150), nullable=True)
    
    # Feedback and scoring
    feedback = Column(Text, nullable=True)
    interview_score = Column(Integer, nullable=True)  # 1-100
    recommendation = Column(String(50), nullable=True)  # Hire, No Hire, Maybe
    
    # Feedback form responses (JSON)
    technical_score = Column(Integer, nullable=True)
    communication_score = Column(Integer, nullable=True)
    cultural_fit_score = Column(Integer, nullable=True)
    problem_solving_score = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    application = relationship("Application", back_populates="interviews")
    
    __table_args__ = (
        Index("ix_interviews_scheduled_at", "scheduled_at"),
        Index("ix_interviews_status", "status"),
    )


class UserCredential(Base):
    __tablename__ = "user_credentials"

    credential_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(role_enum, nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id"), nullable=True)
    
    # Security features
    is_active = Column(Boolean, default=True, server_default="1")
    is_verified = Column(Boolean, default=False, server_default="0")
    is_2fa_enabled = Column(Boolean, default=False, server_default="0")
    two_factor_secret = Column(String(100), nullable=True)
    
    # Password management
    last_password_change = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, server_default="0")
    locked_until = Column(DateTime, nullable=True)
    
    # Session management
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    candidate = relationship("Candidate", back_populates="credential")
    recruiter = relationship("Recruiter", back_populates="credential")
    profile = relationship("UserProfile", back_populates="credential", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_credentials_email", "email"),
        Index("ix_credentials_role", "role"),
        Index("ix_credentials_is_active", "is_active"),
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    profile_id = Column(Integer, primary_key=True, index=True)
    credential_id = Column(Integer, ForeignKey("user_credentials.credential_id"), nullable=False, unique=True)
    full_name = Column(String(120), nullable=True)
    phone_number = Column(String(20), nullable=True)
    profile_image = Column(String(300), nullable=True)
    
    # Candidate-specific fields
    skills = Column(Text, nullable=True)
    education = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    resume_path = Column(String(300), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Recruiter-specific fields
    company_name = Column(String(150), nullable=True)
    company_website = Column(String(255), nullable=True)
    designation = Column(String(120), nullable=True)
    
    # Additional fields
    location = Column(String(150), nullable=True)
    timezone = Column(String(50), nullable=True, default="UTC")
    social_links = Column(Text, nullable=True)  # JSON string for LinkedIn, GitHub, etc.
    preferences = Column(Text, nullable=True)  # JSON string for user preferences
    notifications_enabled = Column(Boolean, default=True, server_default="1")
    
    # Profile analytics
    profile_views = Column(Integer, default=0, server_default="0")
    profile_completeness = Column(Integer, default=0, server_default="0")
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    credential = relationship("UserCredential", back_populates="profile")
    
    __table_args__ = (
        Index("ix_profiles_credential_id", "credential_id"),
        Index("ix_profiles_full_name", "full_name"),
    )


class Notification(Base):
    """Notification model for real-time and email notifications."""
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Can reference candidate_id or recruiter_id
    user_type = Column(String(20), nullable=False)  # 'candidate' or 'recruiter'
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)  # application_update, interview, job_alert, etc.
    
    # Related entity
    related_type = Column(String(50), nullable=True)  # application, interview, job
    related_id = Column(Integer, nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False, server_default="0")
    is_sent = Column(Boolean, default=False, server_default="0")
    
    # Delivery channels
    send_email = Column(Boolean, default=True, server_default="1")
    send_push = Column(Boolean, default=True, server_default="1")
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id", "user_type"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
    )


class AuditLog(Base):
    """Audit log for tracking all important actions in the system."""
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    user_type = Column(String(20), nullable=True)
    action = Column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    entity_type = Column(String(50), nullable=False)  # job, application, candidate, etc.
    entity_id = Column(Integer, nullable=True)
    
    # Details
    old_values = Column(Text, nullable=True)  # JSON string
    new_values = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )


class JobTemplate(Base):
    """Reusable job templates for recruiters."""
    __tablename__ = "job_templates"

    template_id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id"), nullable=False)
    
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    department = Column(String(100), nullable=False)
    required_skills = Column(Text, nullable=True)
    preferred_skills = Column(Text, nullable=True)
    min_experience_years = Column(Integer, nullable=True)
    education_level = Column(String(50), nullable=True)
    
    is_public = Column(Boolean, default=False, server_default="0")
    usage_count = Column(Integer, default=0, server_default="0")
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    recruiter = relationship("Recruiter", backref="templates")


class EmailVerificationToken(Base):
    """Email verification tokens."""
    __tablename__ = "email_verification_tokens"

    token_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True)
    user_type = Column(String(20), nullable=False)
    user_id = Column(Integer, nullable=True)
    
    is_used = Column(Boolean, default=False, server_default="0")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class PasswordResetToken(Base):
    """Password reset tokens."""
    __tablename__ = "password_reset_tokens"

    token_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True)
    
    is_used = Column(Boolean, default=False, server_default="0")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

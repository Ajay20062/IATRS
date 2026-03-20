from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
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
role_enum = Enum("candidate", "recruiter", name="user_role", native_enum=False)


class Recruiter(Base):
    __tablename__ = "recruiters"

    recruiter_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    company = Column(String(150), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")
    credential = relationship("UserCredential", back_populates="recruiter", uselist=False)


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id"), nullable=False)
    title = Column(String(150), nullable=False)
    department = Column(String(100), nullable=False)
    location = Column(String(120), nullable=False)
    status = Column(job_status_enum, nullable=False, default="Open", server_default="Open")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    recruiter = relationship("Recruiter", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    resume_url = Column(String(300), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    credential = relationship("UserCredential", back_populates="candidate", uselist=False)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),)

    application_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=False)
    status = Column(
        application_status_enum,
        nullable=False,
        default="Applied",
        server_default="Applied",
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    job = relationship("Job", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")


class Interview(Base):
    __tablename__ = "interviews"

    interview_id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.application_id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    interview_type = Column(interview_type_enum, nullable=False)
    status = Column(
        interview_status_enum,
        nullable=False,
        default="Scheduled",
        server_default="Scheduled",
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    application = relationship("Application", back_populates="interviews")


class UserCredential(Base):
    __tablename__ = "user_credentials"

    credential_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(role_enum, nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id"), nullable=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    candidate = relationship("Candidate", back_populates="credential")
    recruiter = relationship("Recruiter", back_populates="credential")


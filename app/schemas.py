from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class CandidateSignup(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str


class RecruiterSignup(BaseModel):
    full_name: str
    email: EmailStr
    company: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["candidate", "recruiter"]


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
    resume_url: Optional[str]
    created_at: datetime


class JobCreate(BaseModel):
    title: str
    department: str
    location: str
    status: Literal["Open", "Closed", "Paused"] = "Open"


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    status: Optional[Literal["Open", "Closed", "Paused"]] = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    recruiter_id: int
    title: str
    department: str
    location: str
    status: str
    created_at: datetime


class ApplicationCreate(BaseModel):
    job_id: int


class ApplicationStatusUpdate(BaseModel):
    status: Literal["Applied", "Screening", "Interviewing", "Rejected", "Hired"]


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    job_id: int
    candidate_id: int
    status: str
    created_at: datetime
    job_title: Optional[str] = None
    candidate_name: Optional[str] = None


class InterviewCreate(BaseModel):
    application_id: int
    scheduled_at: datetime
    interview_type: Literal["Phone", "Video", "Onsite"]
    status: Literal["Scheduled", "Completed", "Cancelled", "No-Show"] = "Scheduled"


class InterviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    interview_type: Optional[Literal["Phone", "Video", "Onsite"]] = None
    status: Optional[Literal["Scheduled", "Completed", "Cancelled", "No-Show"]] = None


class InterviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interview_id: int
    application_id: int
    scheduled_at: datetime
    interview_type: str
    status: str
    created_at: datetime


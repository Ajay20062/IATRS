import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import get_settings
from app.utils.dependencies import get_current_user, get_db

router = APIRouter(prefix="/profile", tags=["Profile"])
settings = get_settings()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024
MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024


def _safe_ext(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _save_upload(file: UploadFile, subdir: str, allowed_extensions: set[str], max_size_bytes: int) -> str:
    ext = _safe_ext(file.filename or "")
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = file.file.read()
    if len(content) > max_size_bytes:
        raise HTTPException(status_code=400, detail="File exceeds allowed size")

    upload_dir = Path(settings.upload_dir) / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / file_name
    file_path.write_bytes(content)
    return str(file_path)


def _extract_full_name(credential: models.UserCredential, profile: models.UserProfile | None = None) -> str:
    if profile and profile.full_name:
        return profile.full_name
    if credential.candidate:
        return credential.candidate.full_name
    if credential.recruiter:
        return credential.recruiter.full_name
    return credential.email.split("@", maxsplit=1)[0].replace(".", " ").title()


def _ensure_profile(db: Session, credential: models.UserCredential) -> models.UserProfile:
    profile = credential.profile
    if profile:
        return profile

    profile = models.UserProfile(
        credential_id=credential.credential_id,
        full_name=credential.candidate.full_name if credential.candidate else (credential.recruiter.full_name if credential.recruiter else None),
        phone_number=credential.candidate.phone if credential.candidate else None,
        resume_path=credential.candidate.resume_url if credential.candidate else None,
        company_name=credential.recruiter.company if credential.recruiter else None,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _profile_completion_percentage(credential: models.UserCredential, profile: models.UserProfile) -> int:
    common = [
        _extract_full_name(credential, profile),
        credential.email,
        profile.phone_number,
        profile.profile_image,
        profile.bio,
    ]
    role_specific: list[str | None]
    if credential.role == "candidate":
        role_specific = [profile.skills, profile.education, profile.experience, profile.resume_path]
    elif credential.role == "recruiter":
        role_specific = [profile.company_name, profile.company_website, profile.designation]
    else:
        role_specific = []

    fields = common + role_specific
    completed = sum(1 for value in fields if value and str(value).strip())
    return int((completed / len(fields)) * 100) if fields else 0


def _profile_response(credential: models.UserCredential, profile: models.UserProfile) -> schemas.ProfileRead:
    return schemas.ProfileRead(
        role=credential.role,
        email=credential.email,
        full_name=_extract_full_name(credential, profile),
        phone_number=profile.phone_number,
        profile_image=profile.profile_image,
        skills=profile.skills,
        education=profile.education,
        experience=profile.experience,
        resume_path=profile.resume_path,
        bio=profile.bio,
        company_name=profile.company_name,
        company_website=profile.company_website,
        designation=profile.designation,
        created_at=profile.created_at,
        profile_completion_percentage=_profile_completion_percentage(credential, profile),
    )


@router.get("/me", response_model=schemas.ProfileRead)
def get_my_profile(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(db, current_user)
    return _profile_response(current_user, profile)


@router.put("/update", response_model=schemas.ProfileRead)
def update_profile(
    payload: schemas.ProfileUpdateRequest,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(db, current_user)
    updates = payload.model_dump(exclude_none=True)

    candidate_only = {"skills", "education", "experience"}
    recruiter_only = {"company_name", "company_website", "designation"}

    if current_user.role == "candidate" and recruiter_only.intersection(updates):
        raise HTTPException(status_code=403, detail="Recruiter fields are not editable by candidate users")
    if current_user.role == "recruiter" and candidate_only.intersection(updates):
        raise HTTPException(status_code=403, detail="Candidate fields are not editable by recruiter users")
    if current_user.role == "admin" and (candidate_only.union(recruiter_only)).intersection(updates):
        raise HTTPException(status_code=403, detail="Admin users can only update common profile fields")

    if "full_name" in updates:
        new_name = updates.pop("full_name")
        if current_user.candidate:
            current_user.candidate.full_name = new_name
        if current_user.recruiter:
            current_user.recruiter.full_name = new_name
        if current_user.role == "admin":
            profile.full_name = new_name

    if "phone_number" in updates and current_user.candidate:
        current_user.candidate.phone = updates["phone_number"]

    if "company_name" in updates and current_user.recruiter:
        current_user.recruiter.company = updates["company_name"]

    for field, value in updates.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return _profile_response(current_user, profile)


@router.post("/upload-image", response_model=schemas.ProfileRead)
def upload_profile_image(
    image: UploadFile = File(...),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(db, current_user)
    file_path = _save_upload(image, "images", IMAGE_EXTENSIONS, MAX_IMAGE_SIZE_BYTES)
    profile.profile_image = file_path
    db.commit()
    db.refresh(profile)
    return _profile_response(current_user, profile)


@router.post("/upload-resume", response_model=schemas.ProfileRead)
def upload_resume(
    resume: UploadFile = File(...),
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidate users can upload resumes")

    profile = _ensure_profile(db, current_user)
    file_path = _save_upload(resume, "resumes", RESUME_EXTENSIONS, MAX_RESUME_SIZE_BYTES)
    profile.resume_path = file_path
    if current_user.candidate:
        current_user.candidate.resume_url = file_path
    db.commit()
    db.refresh(profile)
    return _profile_response(current_user, profile)


@router.get("/stats", response_model=schemas.ProfileStatsRead)
def get_profile_stats(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(db, current_user)

    if current_user.role == "candidate":
        applications_count = (
            db.query(func.count(models.Application.application_id))
            .filter(models.Application.candidate_id == current_user.candidate_id)
            .scalar()
            or 0
        )
        interviews_attended = (
            db.query(func.count(models.Interview.interview_id))
            .join(models.Application)
            .filter(
                models.Application.candidate_id == current_user.candidate_id,
                models.Interview.status == "Completed",
            )
            .scalar()
            or 0
        )
    elif current_user.role == "recruiter":
        applications_count = (
            db.query(func.count(models.Application.application_id))
            .join(models.Job)
            .filter(models.Job.recruiter_id == current_user.recruiter_id)
            .scalar()
            or 0
        )
        interviews_attended = (
            db.query(func.count(models.Interview.interview_id))
            .join(models.Application)
            .join(models.Job)
            .filter(
                models.Job.recruiter_id == current_user.recruiter_id,
                models.Interview.status == "Completed",
            )
            .scalar()
            or 0
        )
    else:
        applications_count = db.query(func.count(models.Application.application_id)).scalar() or 0
        interviews_attended = (
            db.query(func.count(models.Interview.interview_id))
            .filter(models.Interview.status == "Completed")
            .scalar()
            or 0
        )

    return schemas.ProfileStatsRead(
        applications_count=applications_count,
        interviews_attended=interviews_attended,
        profile_completion_percentage=_profile_completion_percentage(current_user, profile),
    )


@router.post("/analyze-resume", response_model=schemas.ResumeAnalysisRead)
def analyze_resume(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(db, current_user)
    if current_user.role != "candidate":
        raise HTTPException(status_code=403, detail="Resume analysis is available only for candidate users")
    if not profile.resume_path:
        raise HTTPException(status_code=400, detail="Upload a resume before analysis")

    source = " ".join(
        [
            profile.skills or "",
            profile.education or "",
            profile.experience or "",
            profile.bio or "",
            Path(profile.resume_path).stem,
        ]
    ).lower()

    keyword_bank = {
        "python",
        "sql",
        "java",
        "javascript",
        "react",
        "fastapi",
        "django",
        "aws",
        "docker",
        "kubernetes",
        "machine learning",
        "data analysis",
        "communication",
        "leadership",
    }
    normalized = re.sub(r"\s+", " ", source)
    extracted = sorted([keyword for keyword in keyword_bank if keyword in normalized])

    score = min(100, (len(extracted) * 8) + (18 if profile.experience else 0) + (18 if profile.education else 0))
    return schemas.ResumeAnalysisRead(extracted_keywords=extracted, resume_score=score)

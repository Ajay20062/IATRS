import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import get_settings
from app.utils.dependencies import get_db
from app.utils.security import create_access_token, hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/signup/candidate", response_model=schemas.CandidateRead, status_code=status.HTTP_201_CREATED)
async def signup_candidate(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    resume: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    existing = db.query(models.UserCredential).filter(models.UserCredential.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    resume_path = None
    if resume:
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(resume.filename or "resume").name
        file_name = f"{uuid.uuid4()}_{safe_name}"
        resume_path = str(upload_dir / file_name)
        with open(resume_path, "wb") as out_file:
            out_file.write(await resume.read())

    candidate = models.Candidate(
        full_name=full_name,
        email=email,
        phone=phone,
        resume_url=resume_path,
    )
    db.add(candidate)
    db.flush()

    credential = models.UserCredential(
        email=email,
        password_hash=hash_password(password),
        role="candidate",
        candidate_id=candidate.candidate_id,
    )
    db.add(credential)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/signup/recruiter", response_model=schemas.RecruiterRead, status_code=status.HTTP_201_CREATED)
def signup_recruiter(payload: schemas.RecruiterSignup, db: Session = Depends(get_db)):
    existing = db.query(models.UserCredential).filter(models.UserCredential.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    recruiter = models.Recruiter(
        full_name=payload.full_name,
        email=payload.email,
        company=payload.company,
    )
    db.add(recruiter)
    db.flush()

    credential = models.UserCredential(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="recruiter",
        recruiter_id=recruiter.recruiter_id,
    )
    db.add(credential)
    db.commit()
    db.refresh(recruiter)
    return recruiter


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user_credential = auth.authenticate_user(db, payload.email, payload.password)
    if not user_credential:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(subject=user_credential.email, role=user_credential.role)
    return schemas.TokenResponse(access_token=access_token, role=user_credential.role)

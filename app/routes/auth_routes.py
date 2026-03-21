"""
Advanced authentication routes with email verification, password reset, and 2FA.
"""
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pyotp
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app import auth as auth_utils
from app import models, schemas
from app.config import get_settings
from app.utils.dependencies import get_current_user, get_db
from app.utils.security import create_access_token, hash_password, verify_password
from app.utils.email_service import (
    get_password_reset_template,
    get_welcome_email_template,
    send_email_async,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return str(secrets.randbelow(1000000)).zfill(6)


@router.post("/signup/candidate", response_model=schemas.CandidateRead, status_code=status.HTTP_201_CREATED)
async def signup_candidate(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    current_title: Optional[str] = Form(None),
    current_company: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
):
    """
    Candidate signup with resume upload and email verification.
    """
    # Check if email already exists
    existing = db.query(models.UserCredential).filter(
        models.UserCredential.email == email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Handle resume upload
    resume_path = None
    if resume:
        upload_dir = Path(settings.upload_dir) / "resumes"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(resume.filename or "resume").name
        file_name = f"{uuid.uuid4()}_{safe_name}"
        resume_path = str(upload_dir / file_name)
        with open(resume_path, "wb") as out_file:
            out_file.write(await resume.read())

    # Create candidate
    candidate = models.Candidate(
        full_name=full_name,
        email=email,
        phone=phone,
        resume_url=resume_path,
        current_title=current_title,
        current_company=current_company,
    )
    db.add(candidate)
    db.flush()

    # Create credentials
    credential = models.UserCredential(
        email=email,
        password_hash=hash_password(password),
        role="candidate",
        candidate_id=candidate.candidate_id,
    )
    db.add(credential)
    db.flush()

    # Create profile
    profile = models.UserProfile(
        credential_id=credential.credential_id,
        full_name=full_name,
        phone_number=phone,
        resume_path=resume_path,
    )
    db.add(profile)
    
    # Create email verification token
    verification_token = generate_token()
    expires_at = datetime.now() + timedelta(hours=24)
    email_token = models.EmailVerificationToken(
        email=email,
        token=verification_token,
        user_type="candidate",
        user_id=candidate.candidate_id,
        expires_at=expires_at,
    )
    db.add(email_token)
    
    db.commit()
    db.refresh(candidate)
    
    logger.info(f"Candidate signed up: {candidate.candidate_id}")
    
    # TODO: Send welcome email with verification link
    # welcome_email = get_welcome_email_template(full_name, "candidate")
    # welcome_email.to_email = email
    # await send_email_async(welcome_email)
    
    return schemas.CandidateRead(
        candidate_id=candidate.candidate_id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        resume_url=candidate.resume_url,
        current_title=candidate.current_title,
        current_company=candidate.current_company,
        created_at=candidate.created_at,
    )


@router.post("/signup/recruiter", response_model=schemas.RecruiterRead, status_code=status.HTTP_201_CREATED)
def signup_recruiter(
    payload: schemas.RecruiterSignup,
    db: Session = Depends(get_db),
):
    """
    Recruiter signup with email verification.
    """
    # Check if email already exists
    existing = db.query(models.UserCredential).filter(
        models.UserCredential.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create recruiter
    recruiter = models.Recruiter(
        full_name=payload.full_name,
        email=payload.email,
        company=payload.company,
    )
    db.add(recruiter)
    db.flush()

    # Create credentials
    credential = models.UserCredential(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="recruiter",
        recruiter_id=recruiter.recruiter_id,
    )
    db.add(credential)
    db.flush()

    # Create profile
    profile = models.UserProfile(
        credential_id=credential.credential_id,
        full_name=payload.full_name,
        company_name=recruiter.company,
        designation=payload.designation,
    )
    db.add(profile)
    
    # Create email verification token
    verification_token = generate_token()
    expires_at = datetime.now() + timedelta(hours=24)
    email_token = models.EmailVerificationToken(
        email=payload.email,
        token=verification_token,
        user_type="recruiter",
        user_id=recruiter.recruiter_id,
        expires_at=expires_at,
    )
    db.add(email_token)
    
    db.commit()
    db.refresh(recruiter)
    
    logger.info(f"Recruiter signed up: {recruiter.recruiter_id}")
    
    # TODO: Send welcome email with verification link
    
    return schemas.RecruiterRead(
        recruiter_id=recruiter.recruiter_id,
        full_name=recruiter.full_name,
        email=recruiter.email,
        company=recruiter.company,
        created_at=recruiter.created_at,
    )


@router.post("/signup/admin", response_model=schemas.CurrentUserRead, status_code=status.HTTP_201_CREATED)
def signup_admin(
    payload: schemas.AdminSignup,
    db: Session = Depends(get_db),
):
    """
    Admin signup (restricted - should be disabled in production or require invite code).
    """
    # Check if email already exists
    existing = db.query(models.UserCredential).filter(
        models.UserCredential.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create credentials only (no candidate/recruiter record for admin)
    credential = models.UserCredential(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="admin",
    )
    db.add(credential)
    db.flush()

    # Create profile
    profile = models.UserProfile(
        credential_id=credential.credential_id,
        full_name=payload.full_name,
        phone_number=payload.phone,
    )
    db.add(profile)
    
    db.commit()

    logger.info(f"Admin signed up: {credential.credential_id}")
    
    return schemas.CurrentUserRead(
        role="admin",
        email=payload.email,
        full_name=payload.full_name,
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    payload: schemas.LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login with email and password.
    Supports remember me for extended token expiry.
    """
    # Find user credential
    user_credential = (
        db.query(models.UserCredential)
        .filter(models.UserCredential.email == payload.email)
        .first()
    )
    
    if not user_credential:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if account is locked
    if user_credential.locked_until and user_credential.locked_until > datetime.now():
        raise HTTPException(
            status_code=403,
            detail=f"Account is locked until {user_credential.locked_until}"
        )
    
    # Verify password
    if not verify_password(payload.password, user_credential.password_hash):
        # Increment failed login attempts
        user_credential.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if user_credential.failed_login_attempts >= 5:
            user_credential.locked_until = datetime.now() + timedelta(minutes=30)
            user_credential.failed_login_attempts = 0
        
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if email is verified (optional based on settings)
    # if not user_credential.is_verified:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Please verify your email before logging in"
    #     )
    
    # Reset failed login attempts
    user_credential.failed_login_attempts = 0
    user_credential.last_login_at = datetime.now()
    db.commit()
    
    # Create access token
    expires_in = settings.access_token_expire_minutes * 60
    if payload.remember_me:
        expires_in = settings.refresh_token_expire_days * 24 * 60 * 60
    
    access_token = create_access_token(
        subject=user_credential.email,
        role=user_credential.role,
        expires_delta=timedelta(seconds=expires_in),
    )
    
    logger.info(f"User logged in: {user_credential.email}")
    
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user_credential.role,
        expires_in=expires_in,
    )


@router.post("/refresh-token")
def refresh_token(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    Note: Implement refresh token logic separately for production.
    """
    # For now, this is a placeholder
    # In production, implement proper refresh token validation
    raise HTTPException(status_code=501, detail="Refresh token not implemented")


@router.get("/me", response_model=schemas.CurrentUserRead)
def get_current_profile(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user profile information."""
    if current_user.role == "candidate" and current_user.candidate:
        return schemas.CurrentUserRead(
            role="candidate",
            email=current_user.email,
            full_name=current_user.candidate.full_name,
            candidate_id=current_user.candidate_id,
            is_verified=current_user.is_verified,
            is_2fa_enabled=current_user.is_2fa_enabled,
        )

    if current_user.role == "recruiter" and current_user.recruiter:
        return schemas.CurrentUserRead(
            role="recruiter",
            email=current_user.email,
            full_name=current_user.recruiter.full_name,
            recruiter_id=current_user.recruiter_id,
            company=current_user.recruiter.company,
            is_verified=current_user.is_verified,
            is_2fa_enabled=current_user.is_2fa_enabled,
        )

    if current_user.role == "admin":
        display_name = (
            current_user.profile.full_name
            if current_user.profile and current_user.profile.full_name
            else current_user.email
        )
        return schemas.CurrentUserRead(
            role="admin",
            email=current_user.email,
            full_name=display_name,
            is_verified=current_user.is_verified,
            is_2fa_enabled=current_user.is_2fa_enabled,
        )

    raise HTTPException(status_code=404, detail="User profile not found")


@router.post("/password/reset-request")
def request_password_reset(
    payload: schemas.PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Request password reset. Sends email with reset token.
    """
    user_credential = db.query(models.UserCredential).filter(
        models.UserCredential.email == payload.email
    ).first()
    
    if not user_credential:
        # Don't reveal if email exists
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_token()
    expires_at = datetime.now() + timedelta(hours=1)
    
    # Invalidate existing tokens
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.email == payload.email,
        models.PasswordResetToken.is_used == False
    ).update({"is_used": True})
    
    # Create new token
    password_reset = models.PasswordResetToken(
        email=payload.email,
        token=reset_token,
        expires_at=expires_at,
    )
    db.add(password_reset)
    db.commit()
    
    logger.info(f"Password reset requested for: {payload.email}")
    
    # TODO: Send password reset email
    # reset_email = get_password_reset_template(
    #     user_name=user_credential.email.split("@")[0],
    #     reset_token=reset_token,
    #     reset_link=f"http://localhost:8000/reset-password?token={reset_token}"
    # )
    # reset_email.to_email = payload.email
    # await send_email_async(reset_email)
    
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password/reset-confirm")
def confirm_password_reset(
    payload: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """
    Confirm password reset with token.
    """
    # Find token
    reset_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == payload.token,
        models.PasswordResetToken.is_used == False,
    ).first()
    
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    if reset_token.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="Token has expired")
    
    # Update password
    user_credential = db.query(models.UserCredential).filter(
        models.UserCredential.email == reset_token.email
    ).first()
    
    if not user_credential:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_credential.password_hash = hash_password(payload.new_password)
    user_credential.last_password_change = datetime.now()
    
    # Mark token as used
    reset_token.is_used = True
    
    db.commit()
    
    logger.info(f"Password reset completed for: {reset_token.email}")
    
    return {"message": "Password reset successfully"}


@router.post("/password/change")
def change_password(
    payload: schemas.PasswordChangeRequest,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change password for logged-in user.
    """
    # Verify current password
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    current_user.password_hash = hash_password(payload.new_password)
    current_user.last_password_change = datetime.now()
    
    db.commit()
    
    logger.info(f"Password changed for: {current_user.email}")
    
    return {"message": "Password changed successfully"}


@router.post("/2fa/enable")
def enable_2fa(
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enable two-factor authentication.
    Returns secret key and QR code URL.
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    # Generate secret
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    db.commit()
    
    # Generate QR code URL
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="IATRS"
    )
    
    logger.info(f"2FA enabled for: {current_user.email}")
    
    return {
        "secret": secret,
        "qr_code_url": provisioning_uri,
        "message": "Scan the QR code with your authenticator app and verify with the code",
    }


@router.post("/2fa/verify")
def verify_2fa(
    payload: schemas.Verify2FARequest,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify 2FA code and enable it.
    """
    if not current_user.two_factor_secret:
        raise HTTPException(status_code=400, detail="2FA not initialized")
    
    if current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    # Verify code
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    
    # Enable 2FA
    current_user.is_2fa_enabled = True
    db.commit()
    
    logger.info(f"2FA verified and enabled for: {current_user.email}")
    
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
def disable_2fa(
    payload: schemas.Verify2FARequest,
    current_user: models.UserCredential = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disable two-factor authentication.
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    # Verify current code
    if current_user.two_factor_secret:
        totp = pyotp.TOTP(current_user.two_factor_secret)
        if not totp.verify(payload.code, valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid 2FA code")
    
    # Disable 2FA
    current_user.is_2fa_enabled = False
    current_user.two_factor_secret = None
    db.commit()
    
    logger.info(f"2FA disabled for: {current_user.email}")
    
    return {"message": "2FA disabled successfully"}


@router.post("/verify-email/{token}")
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Verify email address with token.
    """
    email_token = db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.token == token,
        models.EmailVerificationToken.is_used == False,
    ).first()
    
    if not email_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    if email_token.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="Token has expired")
    
    # Mark user as verified
    user_credential = None
    if email_token.user_type == "candidate" and email_token.user_id:
        user_credential = db.query(models.UserCredential).filter(
            models.UserCredential.candidate_id == email_token.user_id
        ).first()
    elif email_token.user_type == "recruiter" and email_token.user_id:
        user_credential = db.query(models.UserCredential).filter(
            models.UserCredential.recruiter_id == email_token.user_id
        ).first()
    
    if user_credential:
        user_credential.is_verified = True
    
    # Mark token as used
    email_token.is_used = True
    db.commit()
    
    logger.info(f"Email verified: {email_token.email}")
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
def resend_verification(
    email: str,
    db: Session = Depends(get_db),
):
    """
    Resend email verification token.
    """
    user_credential = db.query(models.UserCredential).filter(
        models.UserCredential.email == email
    ).first()
    
    if not user_credential:
        return {"message": "If the email exists, a verification link has been sent"}
    
    if user_credential.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    
    # Generate new token
    verification_token = generate_token()
    expires_at = datetime.now() + timedelta(hours=24)
    
    # Invalidate existing tokens
    db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.email == email,
        models.EmailVerificationToken.is_used == False
    ).update({"is_used": True})
    
    # Create new token
    email_token = models.EmailVerificationToken(
        email=email,
        token=verification_token,
        user_type=user_credential.role,
        user_id=user_credential.candidate_id or user_credential.recruiter_id,
        expires_at=expires_at,
    )
    db.add(email_token)
    db.commit()
    
    logger.info(f"Verification email resent to: {email}")
    
    # TODO: Send verification email
    
    return {"message": "Verification email sent"}

"""
OAuth2 authentication routes for Google and LinkedIn login.
"""
import logging
from datetime import datetime, timedelta, timezone

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import get_settings
from app.utils.dependencies import get_db
from app.utils.security import create_access_token, hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/oauth", tags=["OAuth2 Authentication"])
settings = get_settings()

# OAuth2 configuration
oauth = OAuth()

# Google OAuth2
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# LinkedIn OAuth2
if settings.linkedin_client_id and settings.linkedin_client_secret:
    oauth.register(
        name='linkedin',
        client_id=settings.linkedin_client_id,
        client_secret=settings.linkedin_client_secret,
        access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
        authorize_url='https://www.linkedin.com/oauth/v2/authorization',
        api_base_url='https://api.linkedin.com/v2',
        client_kwargs={
            'scope': 'r_emailaddress r_liteprofile'
        }
    )


@router.get("/google/login")
async def google_login(request: Request, redirect_uri: str = None):
    """Initiate Google OAuth2 login."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth2 is not configured")
    
    redirect_url = redirect_uri or str(request.url_for('google_callback'))
    return await oauth.google.authorize_redirect(request, redirect_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth2 callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')
        
        # Check if user exists
        credential = db.query(models.UserCredential).filter(
            models.UserCredential.email == email
        ).first()
        
        if not credential:
            # Create new candidate user
            from app import models
            candidate = models.Candidate(
                full_name=name,
                email=email,
                phone="",  # User will need to add this later
                resume_url=None,
            )
            db.add(candidate)
            db.flush()
            
            credential = models.UserCredential(
                email=email,
                password_hash="",  # OAuth user, no password
                role="candidate",
                candidate_id=candidate.candidate_id,
                is_verified=True,  # Google verified email
            )
            db.add(credential)
            
            profile = models.UserProfile(
                credential_id=credential.credential_id,
                full_name=name,
                profile_image=picture,
            )
            db.add(profile)
            db.commit()
        else:
            # Update last login
            credential.last_login_at = datetime.now()
            db.commit()
        
        # Create access token
        access_token = create_access_token(
            subject=credential.email,
            role=credential.role,
            expires_delta=timedelta(days=settings.refresh_token_expire_days)
        )
        
        # Redirect to frontend with token
        frontend_url = settings.frontend_url or "http://localhost:8000/frontend"
        return RedirectResponse(
            url=f"{frontend_url}/dashboard.html?token={access_token}&role={credential.role}"
        )
        
    except Exception as e:
        logger.error(f"Google OAuth2 error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/linkedin/login")
async def linkedin_login(request: Request, redirect_uri: str = None):
    """Initiate LinkedIn OAuth2 login."""
    if not settings.linkedin_client_id:
        raise HTTPException(status_code=503, detail="LinkedIn OAuth2 is not configured")
    
    redirect_url = redirect_uri or str(request.url_for('linkedin_callback'))
    return await oauth.linkedin.authorize_redirect(request, redirect_url)


@router.get("/linkedin/callback")
async def linkedin_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle LinkedIn OAuth2 callback."""
    try:
        token = await oauth.linkedin.authorize_access_token(request)
        
        # Get user info from LinkedIn
        resp = await oauth.linkedin.get('me', token=token)
        user_info = resp.json()
        
        email_resp = await oauth.linkedin.get(
            'emailAddress?q=members&projection=(elements*(handle~))',
            token=token
        )
        email_info = email_resp.json()
        
        email = email_info.get('elements', [{}])[0].get('handle~', {}).get('emailAddress')
        first_name = user_info.get('firstName', {}).get('localized', {}).get('en_US', '')
        last_name = user_info.get('lastName', {}).get('localized', {}).get('en_US', '')
        name = f"{first_name} {last_name}"
        
        if not email:
            raise HTTPException(status_code=400, detail="Failed to get email from LinkedIn")
        
        # Check if user exists
        credential = db.query(models.UserCredential).filter(
            models.UserCredential.email == email
        ).first()
        
        if not credential:
            # Create new candidate user
            candidate = models.Candidate(
                full_name=name,
                email=email,
                phone="",
                resume_url=None,
            )
            db.add(candidate)
            db.flush()
            
            credential = models.UserCredential(
                email=email,
                password_hash="",
                role="candidate",
                candidate_id=candidate.candidate_id,
                is_verified=True,
            )
            db.add(credential)
            
            profile = models.UserProfile(
                credential_id=credential.credential_id,
                full_name=name,
            )
            db.add(profile)
            db.commit()
        else:
            credential.last_login_at = datetime.now()
            db.commit()
        
        # Create access token
        access_token = create_access_token(
            subject=credential.email,
            role=credential.role,
            expires_delta=timedelta(days=settings.refresh_token_expire_days)
        )
        
        # Redirect to frontend with token
        frontend_url = settings.frontend_url or "http://localhost:8000/frontend"
        return RedirectResponse(
            url=f"{frontend_url}/dashboard.html?token={access_token}&role={credential.role}"
        )
        
    except Exception as e:
        logger.error(f"LinkedIn OAuth2 error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

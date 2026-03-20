from sqlalchemy.orm import Session

from app import models
from app.utils.security import verify_password


def authenticate_user(db: Session, email: str, password: str) -> models.UserCredential | None:
    user_credential = db.query(models.UserCredential).filter(models.UserCredential.email == email).first()
    if not user_credential:
        return None
    if not verify_password(password, user_credential.password_hash):
        return None
    return user_credential


from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal
from app.utils.security import ALGORITHM, SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.UserCredential:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_role: str | None = payload.get("role")
        if email is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    credential = db.query(models.UserCredential).filter(models.UserCredential.email == email).first()
    if not credential:
        raise credentials_exception
    if token_role and token_role != credential.role:
        raise credentials_exception
    return credential


def require_role(required_role: str):
    def _require_role(current_user: models.UserCredential = Depends(get_current_user)) -> models.UserCredential:
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail=f"{required_role.title()} access required")
        return current_user

    return _require_role

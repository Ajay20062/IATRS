import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    auto_create_tables: bool
    upload_dir: str
    cors_origins: list[str]


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return ["*"]
    return [item.strip() for item in value.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Intelligent ATS"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        database_url=os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/iatrs"),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-this-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_as_int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), 60),
        auto_create_tables=_as_bool(os.getenv("AUTO_CREATE_TABLES"), True),
        upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
        cors_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS")),
    )


import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Application
    app_name: str
    app_version: str
    debug: bool
    frontend_url: str
    
    # Database
    database_url: str
    auto_create_tables: bool
    
    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    
    # OAuth2
    google_client_id: str
    google_client_secret: str
    linkedin_client_id: str
    linkedin_client_secret: str
    
    # CORS
    cors_origins: list[str]
    
    # File Upload
    upload_dir: str
    max_upload_size_mb: int
    
    # Email Configuration
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_email: str
    from_name: str
    enable_email: bool
    
    # Redis Cache
    redis_host: str
    redis_port: int
    redis_db: int
    enable_cache: bool
    
    # Rate Limiting
    rate_limit_per_minute: int
    enable_rate_limit: bool
    
    # AI Features
    enable_ai_features: bool
    ai_model_path: Optional[str]
    
    # Security
    bcrypt_rounds: int
    enable_2fa: bool
    
    # Logging
    log_level: str
    log_file: str
    
    # Pagination
    default_page_size: int
    max_page_size: int


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
        # Application
        app_name=os.getenv("APP_NAME", "Intelligent ATS"),
        app_version=os.getenv("APP_VERSION", "2.0.0"),
        debug=_as_bool(os.getenv("DEBUG"), True),
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:8000/frontend"),
        
        # Database
        database_url=os.getenv("DATABASE_URL", "sqlite:///./iatrs.db"),
        auto_create_tables=_as_bool(os.getenv("AUTO_CREATE_TABLES"), True),
        
        # JWT Authentication
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-this-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_as_int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), 60),
        refresh_token_expire_days=_as_int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"), 7),
        
        # OAuth2
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        linkedin_client_id=os.getenv("LINKEDIN_CLIENT_ID", ""),
        linkedin_client_secret=os.getenv("LINKEDIN_CLIENT_SECRET", ""),
        
        # CORS
        cors_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS")),
        
        # File Upload
        upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
        max_upload_size_mb=_as_int(os.getenv("MAX_UPLOAD_SIZE_MB"), 10),
        
        # Email Configuration
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=_as_int(os.getenv("SMTP_PORT"), 587),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        from_email=os.getenv("FROM_EMAIL", ""),
        from_name=os.getenv("FROM_NAME", "IATRS"),
        enable_email=_as_bool(os.getenv("ENABLE_EMAIL"), False),
        
        # Redis Cache
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=_as_int(os.getenv("REDIS_PORT"), 6379),
        redis_db=_as_int(os.getenv("REDIS_DB"), 0),
        enable_cache=_as_bool(os.getenv("ENABLE_CACHE"), False),
        
        # Rate Limiting
        rate_limit_per_minute=_as_int(os.getenv("RATE_LIMIT_PER_MINUTE"), 60),
        enable_rate_limit=_as_bool(os.getenv("ENABLE_RATE_LIMIT"), False),
        
        # AI Features
        enable_ai_features=_as_bool(os.getenv("ENABLE_AI_FEATURES"), True),
        ai_model_path=os.getenv("AI_MODEL_PATH"),
        
        # Security
        bcrypt_rounds=_as_int(os.getenv("BCRYPT_ROUNDS"), 12),
        enable_2fa=_as_bool(os.getenv("ENABLE_2FA"), False),
        
        # Logging
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "logs/iatrs.log"),
        
        # Pagination
        default_page_size=_as_int(os.getenv("DEFAULT_PAGE_SIZE"), 20),
        max_page_size=_as_int(os.getenv("MAX_PAGE_SIZE"), 100),
    )

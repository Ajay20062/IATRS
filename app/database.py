"""
IATRS - Database Configuration
SQLAlchemy database setup and session management.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./iatrs.db")

# Engine configuration
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    # SQLite specific settings
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
        "echo": os.getenv("DEBUG", "false").lower() == "true"
    }
else:
    # MySQL/PostgreSQL settings
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
        "echo": os.getenv("DEBUG", "false").lower() == "true"
    }

# Create engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    """
    from app import models  # Import all models to register them
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")


def drop_db():
    """
    Drop all tables (use with caution!).
    """
    from app import models
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All database tables dropped!")


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()

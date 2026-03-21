# IATRS - Project Structure

```
IATRS/
│
├── 📁 app/                          # Main application package
│   ├── __init__.py                  # Package initialization
│   ├── main.py                      # FastAPI application entry point
│   ├── database.py                  # Database configuration
│   ├── models.py                    # SQLAlchemy database models
│   ├── schemas.py                   # Pydantic validation schemas
│   ├── config.py                    # Application configuration
│   ├── auth.py                      # Authentication utilities
│   ├── schema_migrations.py         # Database migration utilities
│   │
│   ├── 📁 routes/                   # API route handlers
│   │   ├── __init__.py
│   │   ├── auth_routes.py           # Authentication endpoints
│   │   ├── oauth_routes.py          # OAuth2 endpoints
│   │   ├── job_routes.py            # Job management endpoints
│   │   ├── application_routes.py    # Application endpoints
│   │   ├── interview_routes.py      # Interview endpoints
│   │   ├── profile_routes.py        # Profile endpoints
│   │   ├── notification_routes.py   # Notification endpoints
│   │   ├── analytics_routes.py      # Analytics endpoints
│   │   └── system_routes.py         # System endpoints
│   │
│   └── 📁 utils/                    # Utility modules
│       ├── __init__.py
│       ├── security.py              # Password hashing, JWT
│       ├── dependencies.py          # FastAPI dependencies
│       ├── ai_resume_parser.py      # AI resume parsing
│       ├── analytics.py             # Analytics engine
│       ├── email_service.py         # Email sending service
│       ├── cache.py                 # Redis caching
│       ├── rate_limiter.py          # Rate limiting
│       └── logging_config.py        # Logging configuration
│
├── 📁 frontend/                     # Frontend files
│   ├── index.html                   # Home page
│   ├── login.html                   # Login page
│   ├── signup.html                  # Signup page
│   ├── dashboard.html               # Dashboard page
│   ├── profile.html                 # Profile page
│   ├── api-status.html              # API status page
│   ├── database-schema.html         # Database schema viewer
│   │
│   ├── 📁 css/                      # Stylesheets
│   │   ├── dark-mode.css            # Dark mode styles
│   │   └── [other styles]
│   │
│   └── 📁 js/                       # JavaScript files
│       ├── dark-mode.js             # Dark mode toggle
│       └── [other scripts]
│
├── 📁 database/                     # Database files
│   ├── __init__.py
│   └── schema.sql                   # SQL schema definition
│
├── 📁 tests/                        # Test files
│   ├── __init__.py
│   ├── test_advanced.py             # Advanced tests
│   ├── test_auth.py                 # Authentication tests
│   ├── test_jobs.py                 # Job tests
│   └── test_applications.py         # Application tests
│
├── 📁 uploads/                      # Uploaded files
│   ├── .gitkeep
│   ├── 📁 resumes/                  # Uploaded resumes
│   │   └── .gitkeep
│   └── 📁 images/                   # Uploaded images
│       └── .gitkeep
│
├── 📁 logs/                         # Log files
│   ├── .gitkeep
│   ├── iatrs.log                    # Application log
│   └── error.log                    # Error log
│
├── 📁 scripts/                      # Utility scripts
│   └── [utility scripts]
│
├── 📁 config/                       # Configuration files
│   └── [config files]
│
├── 📁 backups/                      # Database backups
│   └── [backup files]
│
├── 📄 setup.py                      # Setup script
├── 📄 run.py                        # Application runner
├── 📄 seed_database.py              # Database seeding
├── 📄 start.bat                     # Windows startup script
├── 📄 start.sh                      # Linux/Mac startup script
├── 📄 requirements.txt              # Python dependencies
├── 📄 .env.example                  # Environment template
├── 📄 .gitignore                    # Git ignore rules
├── 📄 README.md                     # Main documentation
├── 📄 docker-compose.yml            # Docker configuration
├── 📄 Dockerfile                    # Docker build file
└── 📄 ADVANCED_FEATURES.md          # Feature documentation
```

## File Descriptions

### Core Application Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application, middleware, WebSocket |
| `app/database.py` | Database connection, session management |
| `app/models.py` | SQLAlchemy ORM models (12 tables) |
| `app/schemas.py` | Pydantic schemas for validation |
| `app/config.py` | Configuration from environment |
| `app/auth.py` | Authentication logic |

### Route Files (API Endpoints)

| File | Endpoints | Description |
|------|-----------|-------------|
| `auth_routes.py` | 8 | Signup, login, password reset, 2FA |
| `oauth_routes.py` | 4 | Google/LinkedIn OAuth |
| `job_routes.py` | 7 | Job CRUD, matching, analytics |
| `application_routes.py` | 6 | Apply, track, screen applications |
| `interview_routes.py` | 7 | Schedule, feedback, reschedule |
| `profile_routes.py` | 6 | Profile management, uploads |
| `notification_routes.py` | 6 | Real-time notifications |
| `analytics_routes.py` | 7 | Dashboard, funnel, export |
| `system_routes.py` | 3 | Health, stats, schema |

### Utility Files

| File | Purpose |
|------|---------|
| `security.py` | Password hashing, JWT tokens |
| `dependencies.py` | Database session, auth dependencies |
| `ai_resume_parser.py` | Resume parsing, skill extraction |
| `analytics.py` | Analytics calculations |
| `email_service.py` | Email templates, sending |
| `cache.py` | Redis caching |
| `rate_limiter.py` | API rate limiting |
| `logging_config.py` | Logging setup |

### Scripts

| File | Purpose |
|------|---------|
| `setup.py` | Complete application setup |
| `run.py` | Application runner |
| `seed_database.py` | Sample data generation |
| `start.bat` | Windows startup |
| `start.sh` | Linux/Mac startup |

## Quick Navigation

- **Start Application**: `python run.py` or `start.bat`
- **Setup from Scratch**: `python setup.py`
- **Seed Database**: `python seed_database.py`
- **Run Tests**: `pytest -v`
- **API Docs**: http://localhost:8000/docs

# Intelligent Applicant Tracking System (ATS)

A full-stack ATS built with:
- Backend: FastAPI + SQLAlchemy
- Database: MySQL
- Auth: JWT + bcrypt hashing
- Frontend: HTML/CSS/JavaScript (Bootstrap)
- Testing: pytest


Compatibility retained:
- Root `app.py` entrypoint
- Root `schema.sql`
- Legacy helper `db_connect.py`
- Utility frontend pages:
  - `frontend/api-status.html`
  - `frontend/database-schema.html`

Primary implementation:
- FastAPI app under `app/` (auth, jobs, applications, interviews)

## Important Runtime Note

This project is validated for **Python 3.12/3.13**.  
If your machine only has **Python 3.14**, some dependencies (especially `pydantic-core`) may fail to install locally.

Use either:
- Docker (recommended, fully reproducible), or
- Python 3.12 virtual environment.

## 1. Project Structure

```text
project/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── routes/
│   │   ├── auth_routes.py
│   │   ├── job_routes.py
│   │   ├── application_routes.py
│   │   └── interview_routes.py
│   ├── utils/
│   │   ├── security.py
│   │   └── dependencies.py
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   └── dashboard.html
│
├── database/
│   └── schema.sql
│
├── docker-compose.yml
├── Dockerfile
├── .env.example
│
├── tests/
│   ├── test_auth.py
│   ├── test_jobs.py
│   └── test_applications.py
│
├── requirements.txt
└── README.md
```

## 2. Step-by-Step Setup

### Option A (Recommended): Run with Docker

### Step A1: Start services

```powershell
docker compose up --build
```

### Step A2: Open app

- Frontend: `http://127.0.0.1:8000/frontend/index.html`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

---

### Option B: Run locally (Python 3.12)

### Step B1: Create and activate virtual environment

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
```

### Step B2: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step B3: Create MySQL database and tables

1. Open MySQL.
2. Run [`database/schema.sql`](database/schema.sql).

### Step B4: Configure environment variables

Set these before running:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:password@localhost:3306/iatrs"
$env:JWT_SECRET_KEY="replace-with-a-secure-secret"
$env:AUTO_CREATE_TABLES="true"
```

### Step B5: Start FastAPI app

```powershell
uvicorn app.main:app --reload
```

- API docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:8000/frontend/index.html`

## 3. Authentication and Roles

- Candidate signup: `POST /auth/signup/candidate` (supports resume upload).
- Recruiter signup: `POST /auth/signup/recruiter`.
- Login: `POST /auth/login`.
- JWT token required for protected endpoints.
- Role-based access:
  - Recruiter: create/manage jobs, view applications, schedule interviews.
  - Candidate: apply for jobs, track applications, view interviews.

## 4. API Endpoints

### Authentication
- `POST /auth/signup/candidate`
- `POST /auth/signup/recruiter`
- `POST /auth/login`

### Jobs
- `GET /jobs` (supports `search`, `location`, `department`, `status`)
- `POST /jobs` (Recruiter only)
- `PUT /jobs/{id}` (Recruiter owner only)
- `DELETE /jobs/{id}` (Recruiter owner only)

### Applications
- `POST /applications` (Candidate applies)
- `GET /applications` (Recruiter sees their jobs, candidate sees own)
- `PUT /applications/{id}/status` (Recruiter owner only)

### Interviews
- `POST /interviews` (Recruiter schedules)
- `GET /interviews` (Role-based)
- `PUT /interviews/{id}` (Recruiter owner only)

### System
- `GET /health`
- `GET /stats/schema` (live table counts for schema viewer)

## 5. Frontend Modules

- Login page
- Signup page (candidate/recruiter tabs)
- Candidate dashboard:
  - search/filter jobs
  - apply
  - view application status badges
  - view interview schedule
- Recruiter dashboard:
  - post jobs
  - view applicants
  - update application status
  - schedule interviews
  - basic notifications

## 6. Run Tests

```powershell
pytest -q
```

Tests included:
- Signup/Login
- Job creation
- Application submission and status update

## 7. Notes

- The requested ATS tables are implemented exactly.
- A supplemental `user_credentials` table is added for password hashing and JWT authentication.
- Resume uploads are stored as local file paths in `uploads/`.
- `/health` endpoint added for service checks.
- Frontend pages use relative navigation links for better compatibility across local preview and API-hosted mode.

# IATRS Advanced Features Documentation

## Overview

The Intelligent Applicant Tracking System (IATRS) has been enhanced with advanced features to provide a comprehensive, AI-powered recruitment platform. This document outlines all the new features and improvements.

---

## 🚀 New Features

### 1. AI-Powered Resume Parsing & Matching

**Location:** `app/utils/ai_resume_parser.py`

#### Features:
- **Resume Text Extraction**: Support for PDF, DOCX, and TXT formats
- **Skill Extraction**: Automatic extraction of 100+ tech skills from resumes
- **Education Parsing**: Identifies education levels (PhD, Masters, Bachelors, etc.)
- **Experience Analysis**: Extracts years of experience, job titles, and companies
- **Contact Information**: Extracts email, phone, LinkedIn, and GitHub profiles
- **Resume Scoring**: Calculates a score (0-100) based on skills, education, and experience
- **Job-Candidate Matching**: AI-powered matching algorithm using:
  - BM25 ranking algorithm
  - TF-IDF + Cosine Similarity
  - Skill match percentage
  - Experience match percentage
- **Candidate Ranking**: Ranks all applicants for a job based on match score

#### Usage:
```python
from app.utils.ai_resume_parser import parse_resume, calculate_job_candidate_match, rank_candidates

# Parse resume
resume_data = parse_resume("/path/to/resume.pdf")

# Calculate match score
match_result = calculate_job_candidate_match(job_description, resume_data)

# Rank multiple candidates
ranked_results = rank_candidates(job_description, candidates_data)
```

---

### 2. Enhanced Authentication System

**Location:** `app/routes/auth_routes.py`

#### Features:
- **Email Verification**: Token-based email verification system
- **Password Reset**: Secure password reset with token-based email flow
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA using pyotp
- **Account Lockout**: Automatic lockout after 5 failed login attempts
- **Remember Me**: Extended token expiry for remember me option
- **Role-Based Access**: Candidate, Recruiter, and Admin roles
- **Resume Upload**: Candidates can upload resumes during signup

#### New Endpoints:
```
POST /auth/signup/candidate          - Candidate signup with resume
POST /auth/signup/recruiter          - Recruiter signup
POST /auth/signup/admin              - Admin signup
POST /auth/login                     - Login with email/password
POST /auth/password/reset-request    - Request password reset
POST /auth/password/reset-confirm    - Confirm password reset
POST /auth/password/change           - Change password (logged-in users)
POST /auth/2fa/enable                - Enable 2FA
POST /auth/2fa/verify                - Verify 2FA code
POST /auth/2fa/disable               - Disable 2FA
POST /auth/verify-email/{token}      - Verify email address
POST /auth/resend-verification       - Resend verification email
GET  /auth/me                        - Get current user profile
```

---

### 3. Real-Time Notifications (WebSocket)

**Location:** `app/main.py`, `app/routes/notification_routes.py`

#### Features:
- **WebSocket Support**: Real-time push notifications
- **Connection Manager**: Manages multiple WebSocket connections
- **Notification Types**:
  - Application updates
  - Interview invitations
  - Interview reminders
  - Job alerts
  - Status changes
- **Email Integration**: Optional email notifications
- **Read/Unread Status**: Track notification read status

#### WebSocket Connection:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications');
ws.send(JSON.stringify({
    user_id: 1,
    user_type: 'candidate'
}));
```

#### REST Endpoints:
```
GET    /notifications              - Get all notifications
GET    /notifications/unread-count - Get unread count
POST   /notifications/mark-as-read - Mark specific as read
POST   /notifications/mark-all-as-read - Mark all as read
DELETE /notifications/{id}         - Delete notification
DELETE /notifications/clear-all    - Clear all notifications
```

---

### 4. Advanced Analytics Dashboard

**Location:** `app/utils/analytics.py`, `app/routes/analytics_routes.py`

#### Features:
- **Dashboard Analytics**: Comprehensive platform metrics
- **Recruitment Funnel**: Conversion rates at each stage
- **Time-to-Hire Metrics**: Average time for each recruitment stage
- **Candidate Pipeline**: View candidates at different stages
- **Job Performance**: Applications and interviews per job
- **Activity Reports**: Generate reports for custom date ranges
- **Export Functionality**: Export data in CSV/JSON format

#### Analytics Endpoints:
```
GET /analytics/dashboard           - Comprehensive dashboard
GET /analytics/funnel              - Recruitment funnel metrics
GET /analytics/jobs/performance    - Job performance metrics
GET /analytics/candidates/pipeline - Candidate pipeline
GET /analytics/time-to-hire        - Time-to-hire analysis
GET /analytics/activity-report     - Activity report
GET /analytics/export              - Export data (CSV/JSON)
```

#### Dashboard Metrics:
- Total jobs, applications, candidates, recruiters, interviews
- Application status distribution
- Department and location breakdowns
- Applications trend (last 30 days)
- Top recruiters by jobs posted
- Hiring funnel conversion rates
- Average time to hire

---

### 5. Enhanced Job Management

**Location:** `app/routes/job_routes.py`

#### New Job Features:
- **Salary Range**: Min/max salary with currency and period
- **Work Mode**: Remote, Hybrid, or Onsite options
- **Skills Requirements**: Required and preferred skills
- **Experience Requirements**: Min/max years of experience
- **Education Requirements**: Education level specifications
- **Job Metadata**: Views count, applications count, featured jobs
- **Advanced Filtering**: Search by skills, salary, location, etc.
- **AI Candidate Matching**: Automatically rank candidates

#### Enhanced Job Schema:
```python
{
    "title": "Software Engineer",
    "description": "...",
    "requirements": "...",
    "department": "Engineering",
    "location": "San Francisco",
    "work_mode": "Hybrid",
    "min_salary": 100000,
    "max_salary": 150000,
    "salary_currency": "USD",
    "required_skills": "python,fastapi,sql",
    "min_experience_years": 3,
    "education_level": "Bachelors",
    "is_featured": true,
    "expires_at": "2026-04-21"
}
```

#### New Endpoints:
```
GET    /jobs/{id}/applications      - Get job applications
POST   /jobs/{id}/match-candidates  - AI candidate matching
GET    /jobs/analytics/dashboard    - Job analytics
```

---

### 6. Advanced Application Management

**Location:** `app/routes/application_routes.py`

#### New Features:
- **AI Match Scoring**: Automatic match score calculation
- **Resume Scoring**: Resume quality score
- **Screening Score**: Manual screening score by recruiters
- **Cover Letters**: Support for cover letters
- **Application Source**: Track where application came from
- **Referral Tracking**: Referral code support
- **Match Analysis**: Detailed skill/experience match breakdown
- **Status Update Notifications**: Email on status change

#### Application Schema Enhancements:
```python
{
    "application_id": 1,
    "match_score": 85.5,
    "screening_score": 78.0,
    "resume_score": 82,
    "cover_letter": "...",
    "applied_via": "website",
    "referral_code": "REF123",
    "recruiter_notes": "...",
    "rejection_reason": "...",
    "reviewed_at": "2026-03-21T10:00:00"
}
```

#### New Endpoints:
```
GET    /applications/{id}/match-analysis  - Detailed match analysis
PUT    /applications/{id}/screening       - Screen application
```

---

### 7. Interview Management Enhancements

**Location:** `app/routes/interview_routes.py`

#### New Features:
- **Comprehensive Feedback Forms**: Multi-dimensional scoring
- **Interview Scoring**: Overall and category-specific scores
- **Interviewer Assignment**: Assign interviewers by name/email
- **Video Call Links**: Store meeting links for virtual interviews
- **Location Tracking**: Address for onsite interviews
- **Rescheduling**: Easy reschedule with reason tracking
- **Cancellation**: Cancel interviews with reason
- **Interview Statistics**: Summary metrics

#### Feedback Categories:
- Overall Interview Score (0-100)
- Technical Skills Score (0-100)
- Communication Score (0-100)
- Cultural Fit Score (0-100)
- Problem Solving Score (0-100)
- Recommendation: Hire / No Hire / Maybe

#### New Endpoints:
```
POST   /interviews/{id}/feedback      - Submit feedback
POST   /interviews/{id}/reschedule    - Reschedule interview
POST   /interviews/{id}/cancel        - Cancel interview
GET    /interviews/stats/summary      - Interview statistics
```

---

### 8. Email Service Integration

**Location:** `app/utils/email_service.py`

#### Features:
- **SMTP Integration**: Configurable SMTP settings
- **Email Templates**: Professional HTML email templates
- **Async Support**: Non-blocking email sending
- **Template Types**:
  - Welcome emails
  - Application confirmation
  - Interview invitations
  - Application status updates
  - Password reset
  - Email verification

#### Configuration:
```env
ENABLE_EMAIL=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@iatrs.com
FROM_NAME=IATRS
```

---

### 9. Enhanced Database Models

**Location:** `app/models.py`

#### New Models:
- **Notification**: Real-time notification storage
- **AuditLog**: Track all system actions
- **JobTemplate**: Reusable job templates
- **EmailVerificationToken**: Email verification tokens
- **PasswordResetToken**: Password reset tokens

#### Enhanced Models:
- **Job**: Added salary, skills, work_mode, metadata fields
- **Candidate**: Added experience, salary expectations, scoring
- **Application**: Added match scores, screening, feedback
- **Interview**: Added feedback, scoring, interviewer details
- **UserCredential**: Added 2FA, security fields
- **UserProfile**: Extended with social links, preferences

#### Database Indexes:
- Email indexes for fast lookups
- Status indexes for filtering
- Created_at indexes for sorting
- Composite indexes for common queries

---

### 10. Configuration Enhancements

**Location:** `app/config.py`

#### New Settings:
```python
# Application
DEBUG=true
APP_VERSION=2.0.0

# Security
BCRYPT_ROUNDS=12
ENABLE_2FA=false

# Email
ENABLE_EMAIL=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Cache
ENABLE_CACHE=false
REDIS_HOST=localhost
REDIS_PORT=6379

# Rate Limiting
ENABLE_RATE_LIMIT=false
RATE_LIMIT_PER_MINUTE=60

# AI Features
ENABLE_AI_FEATURES=true

# Pagination
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

---

## 📦 New Dependencies

Added to `requirements.txt`:

```txt
# AI & NLP
spacy==3.8.4
rank-bm25==0.2.2
scikit-learn==1.6.1

# File Processing
python-docx==1.1.2
pypdf==5.3.0
openpyxl==3.1.5
reportlab==4.3.0

# Email & Notifications
aiosmtplib==3.0.2
fastapi-websocket==0.1.1

# Caching & Rate Limiting
redis==5.2.1
slowapi==0.1.9

# Security
pyotp==2.9.0
authlib==1.4.1

# Database Migrations
alembic==1.15.1
```

---

## 🔧 Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run Database Migrations

```bash
# Tables will be auto-created on first run
# Or use Alembic for migrations:
alembic upgrade head
```

### 5. Start the Application

```bash
uvicorn app.main:app --reload
```

---

## 📊 API Documentation

Once running, access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔐 Security Features

1. **Password Hashing**: Bcrypt with configurable rounds
2. **JWT Tokens**: Secure authentication with expiry
3. **2FA Support**: TOTP-based two-factor authentication
4. **Account Lockout**: After 5 failed attempts
5. **Email Verification**: Token-based verification
6. **Password Reset**: Secure token-based reset
7. **CORS Configuration**: Configurable origins
8. **Rate Limiting**: Optional API throttling

---

## 📈 Performance Optimizations

1. **Database Indexes**: Optimized queries
2. **Redis Caching**: Optional caching layer
3. **Connection Pooling**: SQLAlchemy connection management
4. **Async Operations**: Non-blocking I/O where possible
5. **Pagination**: All list endpoints support pagination

---

## 🧪 Testing

Run tests with pytest:

```bash
pytest -v
```

---

## 📝 Future Enhancements

- [ ] OAuth2 provider integration (Google, LinkedIn)
- [ ] Calendar integration (Google Calendar, Outlook)
- [ ] Advanced reporting with PDF export
- [ ] Machine learning model for better matching
- [ ] Chatbot for candidate queries
- [ ] Mobile app support
- [ ] Multi-language support
- [ ] Advanced search with Elasticsearch

---

## 🤝 Support

For issues or questions:
- Check the API documentation at `/docs`
- Review the code comments
- Check logs for error details

---

**Version:** 2.0.0  
**Last Updated:** March 21, 2026

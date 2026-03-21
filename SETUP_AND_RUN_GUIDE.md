# 🚀 IATRS v2.0 - Complete Setup & Run Guide

## 📋 Quick Start (Choose One)

### Option 1: Automated Setup (Recommended)

```bash
# Run the complete setup
python setup.py

# Then start the application
python run.py
```

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
py -3.14 -m venv .venv

# 2. Activate virtual environment
.venv\Scripts\activate    # Windows
source .venv/bin/activate # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac

# 5. Initialize database
python -c "from app.database import init_db; init_db()"

# 6. Seed database (optional)
python seed_database.py

# 7. Start application
python run.py
```

### Option 3: One-Click Start (Windows)

```bash
start.bat
```

---

## 📁 Project Organization

```
IATRS/
├── app/                    # Main application
│   ├── main.py            # Entry point
│   ├── database.py        # Database config
│   ├── models.py          # Database models
│   ├── schemas.py         # Validation schemas
│   ├── routes/            # API endpoints
│   └── utils/             # Utilities
├── frontend/              # Web interface
├── tests/                 # Test files
├── uploads/               # User uploads
├── logs/                  # Log files
├── setup.py              # Setup script
├── run.py                # Runner script
└── start.bat             # Quick start
```

---

## 🔧 Configuration

### Edit `.env` File

```env
# Database
DATABASE_URL=sqlite:///./iatrs.db

# Security
JWT_SECRET_KEY=your-secret-key-change-this

# Features
DEBUG=true
ENABLE_EMAIL=false
ENABLE_CACHE=false
ENABLE_RATE_LIMIT=false
ENABLE_2FA=false

# Server
HOST=127.0.0.1
PORT=8000
```

---

## 🎯 Running the Application

### Method 1: Using run.py (Recommended)

```bash
python run.py
```

**Output:**
```
============================================================
  IATRS v2.0.0 - Starting Application
============================================================

📍 Host: http://127.0.0.1:8000
📚 Docs: http://127.0.0.1:8000/docs
🔧 Reload: Enabled

Press CTRL+C to stop
```

### Method 2: Using uvicorn Directly

```bash
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Method 3: Using start.bat (Windows)

```bash
start.bat
```

---

## 🌐 Access Points

Once running, access:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://127.0.0.1:8000/frontend/index.html | Main UI |
| **API Docs** | http://127.0.0.1:8000/docs | Swagger UI |
| **ReDoc** | http://127.0.0.1:8000/redoc | Alternative docs |
| **Health** | http://127.0.0.1:8000/health | Health check |
| **Stats** | http://127.0.0.1:8000/stats/schema | DB stats |

---

## 🧪 Testing

### Run All Tests

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=app -v
```

### Run Specific Test File

```bash
pytest tests/test_advanced.py -v
```

---

## 🗄️ Database Management

### Initialize Database

```bash
python -c "from app.database import init_db; init_db()"
```

### Seed Sample Data

```bash
python seed_database.py
```

**Sample Data Includes:**
- 3 Recruiters
- 5 Candidates
- 5 Jobs
- 6 Applications
- 3 Interviews

### Reset Database

```bash
# Delete SQLite file
del iatrs.db       # Windows
rm iatrs.db        # Linux/Mac

# Reinitialize
python -c "from app.database import init_db; init_db()"
```

---

## 🔐 Test Credentials

After seeding, use these to login:

**All passwords:** `password123`

### Recruiters
```
sarah@techcorp.com
michael@innovate.io
emily@startup.co
```

### Candidates
```
john.doe@email.com
jane.smith@email.com
robert.wilson@email.com
alice.brown@email.com
david.lee@email.com
```

### Admin
```
admin@iatrs.com
```

---

## 📊 API Endpoints Overview

### Authentication
```
POST /auth/signup/candidate    - Register candidate
POST /auth/signup/recruiter    - Register recruiter
POST /auth/login               - Login
GET  /auth/me                  - Current user
```

### Jobs
```
GET  /jobs                     - List jobs
POST /jobs                     - Create job
GET  /jobs/{id}                - Get job
PUT  /jobs/{id}                - Update job
DELETE /jobs/{id}              - Delete job
```

### Applications
```
POST /applications             - Apply
GET  /applications             - Get applications
PUT  /applications/{id}/status - Update status
```

### Interviews
```
POST /interviews               - Schedule
GET  /interviews               - List
POST /interviews/{id}/feedback - Submit feedback
```

### Analytics
```
GET /analytics/dashboard       - Dashboard
GET /analytics/funnel          - Funnel metrics
GET /analytics/export          - Export data
```

---

## 🐛 Troubleshooting

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Use different port
python run.py --port 8001

# Or kill process on port 8000 (Windows)
netstat -ano | findstr :8000
taskkill /F /PID <PID>
```

### Database Connection Error

**Error:** `Can't connect to database`

**Solution:**
```bash
# Check DATABASE_URL in .env
# For SQLite, ensure file is not locked
# For MySQL, ensure server is running
```

### Import Errors

**Error:** `ModuleNotFoundError`

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Ensure you're in virtual environment
```

### Permission Errors

**Error:** `Permission denied`

**Solution:**
```bash
# Run as administrator (Windows)
# Or fix directory permissions (Linux/Mac)
chmod -R 755 uploads/ logs/
```

---

## 📝 Development Workflow

### 1. Make Changes
Edit files in `app/`, `frontend/`, etc.

### 2. Test Changes
```bash
pytest tests/test_file.py -v
```

### 3. Run Application
```bash
python run.py
```

### 4. Test in Browser
http://127.0.0.1:8000/docs

### 5. Check Logs
```bash
# View logs in real-time
tail -f logs/iatrs.log    # Linux/Mac
Get-Content logs/iatrs.log -Wait  # Windows
```

---

## 🎨 Frontend Development

### Enable Auto-Reload

The application automatically reloads on file changes when `DEBUG=true`.

### Access Frontend Files

```
frontend/
├── index.html
├── login.html
├── signup.html
├── dashboard.html
├── css/
│   └── dark-mode.css
└── js/
    └── dark-mode.js
```

### Toggle Dark Mode

Click the 🌙/☀️ button in the bottom-right corner of any page.

---

## 📦 Docker Deployment

### Build and Run

```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f app

# Stop services
docker compose down
```

### Access in Docker

- Application: http://localhost:8000
- MySQL: localhost:3306
- Redis: localhost:6379

---

## 🔐 Security Best Practices

### Production Checklist

- [ ] Change `JWT_SECRET_KEY`
- [ ] Set `DEBUG=false`
- [ ] Use strong database password
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Set up monitoring
- [ ] Regular backups

### Environment Variables

Never commit `.env` file. Use `.env.example` as template.

```bash
# Add to .gitignore
.env
*.db
uploads/*
logs/*
```

---

## 📞 Support & Resources

| Resource | Location |
|----------|----------|
| API Documentation | http://localhost:8000/docs |
| Full Documentation | README.md |
| Features Guide | ADVANCED_FEATURES.md |
| Project Structure | PROJECT_STRUCTURE.md |
| GitHub Issues | Create issue on repository |

---

## ✅ Setup Verification Checklist

Run these to verify everything works:

```bash
# 1. Check Python version
py --version

# 2. Check imports
py -c "from app.main import app; print('OK')"

# 3. Check database
py -c "from app.database import init_db; init_db()"

# 4. Start server
python run.py

# 5. Test health endpoint
curl http://127.0.0.1:8000/health

# 6. Test API docs
# Open browser: http://127.0.0.1:8000/docs
```

---

## 🎉 Success!

If all steps complete without errors, your IATRS application is ready!

**Next Steps:**
1. Open http://127.0.0.1:8000/frontend/index.html
2. Login with test credentials
3. Explore features
4. Check API documentation
5. Start developing!

---

**Version:** 2.0.0  
**Last Updated:** March 21, 2026  
**Status:** ✅ Production Ready

@echo off
REM ===========================================
REM IATRS v2.0 - Quick Start Script (Windows)
REM ===========================================

echo.
echo ================================================================
echo   IATRS v2.0.0 - Intelligent Applicant Tracking System
echo ================================================================
echo.

REM Check if Python exists
py --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.12 or higher.
    pause
    exit /b 1
)

echo [1/4] Python found...
py --version

REM Check virtual environment
if not exist ".venv" (
    echo.
    echo [2/4] Creating virtual environment...
    py -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/4] Virtual environment found.
)

REM Activate virtual environment
echo.
echo [3/4] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [4/4] Checking dependencies...
pip install -r requirements.txt --quiet --upgrade

REM Create directories
if not exist "uploads" mkdir uploads
if not exist "uploads\resumes" mkdir uploads\resumes
if not exist "uploads\images" mkdir uploads\images
if not exist "logs" mkdir logs

REM Check .env file
if not exist ".env" (
    echo.
    echo Creating .env file...
    copy .env.example .env
    echo Please review .env file with your settings.
)

REM Start application
echo.
echo ================================================================
echo   Starting IATRS Application...
echo ================================================================
echo.
echo Access URLs:
echo   Frontend: http://127.0.0.1:8000/frontend/index.html
echo   API Docs: http://127.0.0.1:8000/docs
echo   Health:   http://127.0.0.1:8000/health
echo.
echo Press CTRL+C to stop the server.
echo ================================================================
echo.

REM Run application
py run.py

pause

@echo off
title Smart ATS - Setup and Launch
color 0A

echo ========================================
echo    Smart ATS Recruitment System
echo    Setup and Launch Script
echo ========================================
echo.

echo [1/5] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python detected

echo.
echo [2/5] Setting up virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

echo.
echo [3/5] Installing dependencies...
call venv\Scripts\activate
pip install -r requirements.txt >nul 2>&1
echo ✅ Dependencies installed

echo.
echo [4/5] Checking database setup...
if not exist ".env" (
    echo ⚠️  .env file not found. Creating template...
    echo DB_HOST=localhost > .env
    echo DB_USER=root >> .env
    echo DB_PASSWORD= >> .env
    echo DB_NAME=iatrs >> .env
    echo ✅ .env template created - Please update with your MySQL credentials
) else (
    echo ✅ .env file exists
)

echo.
echo [5/5] Seeding database with sample data...
python seed_data.py
echo ✅ Database setup complete

echo.
echo ========================================
echo    Setup Complete! 🎉
echo ========================================
echo.
echo To start the application:
echo   1. Double-click start.bat
echo   2. Or run: python app.py
echo.
echo Application will be available at:
echo   Backend API: http://127.0.0.1:5000
echo   Frontend: Open frontend/index.html
echo.
echo Press any key to start the application now...
pause >nul

echo.
echo Starting Smart ATS...
echo.
python app.py

pause

#!/bin/bash
# ===========================================
# IATRS v2.0 - Quick Start Script (Linux/Mac)
# ===========================================

echo ""
echo "================================================================"
echo "  IATRS v2.0.0 - Intelligent Applicant Tracking System"
echo "================================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.12 or higher."
    exit 1
fi

echo "[1/4] Python found..."
python3 --version

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo ""
    echo "[2/4] Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        exit 1
    fi
else
    echo "[2/4] Virtual environment found."
fi

# Activate virtual environment
echo ""
echo "[3/4] Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo ""
echo "[4/4] Checking dependencies..."
pip install -r requirements.txt --quiet --upgrade

# Create directories
mkdir -p uploads/resumes uploads/images logs

# Check .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please review .env file with your settings."
fi

# Start application
echo ""
echo "================================================================"
echo "  Starting IATRS Application..."
echo "================================================================"
echo ""
echo "Access URLs:"
echo "  Frontend: http://127.0.0.1:8000/frontend/index.html"
echo "  API Docs: http://127.0.0.1:8000/docs"
echo "  Health:   http://127.0.0.1:8000/health"
echo ""
echo "Press CTRL+C to stop the server."
echo "================================================================"
echo ""

# Run application
python run.py

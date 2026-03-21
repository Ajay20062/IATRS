#!/usr/bin/env python3
"""
IATRS - Complete Setup Script
Sets up the entire application from scratch.
"""
import os
import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(step, text):
    """Print step information."""
    print(f"\n[{step}] {text}")
    print("-" * 40)


def run_command(command, shell=True):
    """Run shell command."""
    try:
        subprocess.run(command, shell=shell, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        return False


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 12):
        print(f"⚠️  Warning: Python 3.12+ recommended (you have {version.major}.{version.minor})")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def create_virtual_environment():
    """Create virtual environment if it doesn't exist."""
    if not Path(".venv").exists():
        print("Creating virtual environment...")
        run_command(f"{sys.executable} -m venv .venv")
        print("✅ Virtual environment created")
    else:
        print("✅ Virtual environment already exists")


def install_dependencies():
    """Install Python dependencies."""
    print("Installing dependencies...")
    
    # Activate venv and install
    if os.name == 'nt':  # Windows
        pip_path = ".venv\\Scripts\\pip"
    else:  # Linux/Mac
        pip_path = ".venv/bin/pip"
    
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt")
    print("✅ Dependencies installed")


def create_directories():
    """Create necessary directories."""
    dirs = [
        "uploads",
        "uploads/resumes",
        "uploads/images",
        "logs",
        "config",
        "backups"
    ]
    
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    # Create .gitkeep files
    for dir_name in dirs:
        gitkeep = Path(dir_name) / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
    
    print("✅ Directories created")


def create_env_file():
    """Create .env file if it doesn't exist."""
    if not Path(".env").exists():
        print("Creating .env file from template...")
        env_content = """# IATRS Configuration
DATABASE_URL=sqlite:///./iatrs.db
JWT_SECRET_KEY=change-this-secret-in-production
DEBUG=true
ENABLE_EMAIL=false
ENABLE_CACHE=false
ENABLE_RATE_LIMIT=false
ENABLE_2FA=false
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print("✅ .env file created - Please review and update!")
    else:
        print("✅ .env file already exists")


def initialize_database():
    """Initialize database."""
    print("Initializing database...")
    
    # Try to import and initialize
    try:
        from app.database import init_db
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
        print("ℹ️  Database will be created on first run")


def seed_database():
    """Seed database with sample data."""
    response = input("\n🌱 Seed database with sample data? (y/n): ")
    if response.lower() == 'y':
        try:
            import seed_database
            seed_database.seed_database()
        except Exception as e:
            print(f"⚠️  Seeding failed: {e}")
    else:
        print("⏭️  Skipping database seeding")


def main():
    """Main setup function."""
    print_header("IATRS v2.0.0 - Complete Setup")
    
    # Step 1: Check Python
    print_step(1, "Checking Python Version")
    check_python_version()
    
    # Step 2: Virtual Environment
    print_step(2, "Setting Up Virtual Environment")
    create_virtual_environment()
    
    # Step 3: Dependencies
    print_step(3, "Installing Dependencies")
    install_dependencies()
    
    # Step 4: Directories
    print_step(4, "Creating Directories")
    create_directories()
    
    # Step 5: Environment
    print_step(5, "Configuring Environment")
    create_env_file()
    
    # Step 6: Database
    print_step(6, "Initializing Database")
    initialize_database()
    
    # Step 7: Seed Data
    print_step(7, "Sample Data")
    seed_database()
    
    # Complete
    print_header("Setup Complete! 🎉")
    
    print("""
Next Steps:
-----------
1. Review and update .env file with your settings
2. Run: start.bat (Windows) or ./start.sh (Linux/Mac)
3. Access application at: http://127.0.0.1:8000
4. View API docs at: http://127.0.0.1:8000/docs

Test Credentials (if seeded):
------------------------------
Recruiters:
  - sarah@techcorp.com / password123
  - michael@innovate.io / password123

Candidates:
  - john.doe@email.com / password123
  - jane.smith@email.com / password123

Admin:
  - admin@iatrs.com / password123

""")


if __name__ == "__main__":
    main()

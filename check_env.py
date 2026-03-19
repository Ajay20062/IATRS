"""
Smart ATS - Python Environment Check
This script verifies the Python environment and dependencies
"""

import sys
import subprocess
import os

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"✅ Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("⚠️  Warning: Python 3.8+ recommended")
    else:
        print("✅ Python version is compatible")

def check_virtual_env():
    """Check if running in virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        print(f"📁 Virtual Environment: {sys.prefix}")
        return True
    else:
        print("⚠️  Not running in virtual environment")
        return False

def check_dependencies():
    """Check required packages"""
    required_packages = [
        'flask',
        'flask_cors', 
        'mysql.connector',
        'dotenv',
        'requests'
    ]
    
    print("\n📦 Checking dependencies:")
    all_installed = True
    
    for package in required_packages:
        try:
            if package == 'flask_cors':
                import flask_cors
            elif package == 'mysql.connector':
                import mysql.connector
            elif package == 'dotenv':
                import dotenv
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Not installed")
            all_installed = False
    
    return all_installed

def check_database_connection():
    """Check database connection"""
    try:
        from db_connect import get_db_connection
        connection = get_db_connection()
        if connection:
            connection.close()
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def check_env_file():
    """Check if .env file exists"""
    if os.path.exists('.env'):
        print("✅ .env file exists")
        return True
    else:
        print("⚠️  .env file not found - create it with database credentials")
        return False

def main():
    """Main environment check"""
    print("🔍 Smart ATS - Python Environment Check")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Check virtual environment
    is_venv = check_virtual_env()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check database
    db_ok = check_database_connection()
    
    # Check .env file
    env_ok = check_env_file()
    
    print("\n" + "=" * 50)
    print("📊 Environment Summary:")
    
    if is_venv and deps_ok and db_ok and env_ok:
        print("🎉 Environment is properly configured!")
        print("🚀 You can start the application with: python app.py")
    else:
        print("⚠️  Environment needs attention:")
        if not is_venv:
            print("   - Activate virtual environment: venv\\Scripts\\activate")
        if not deps_ok:
            print("   - Install dependencies: pip install -r requirements.txt")
        if not db_ok:
            print("   - Check database configuration in .env file")
        if not env_ok:
            print("   - Create .env file with database credentials")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
IATRS - Application Runner
Starts the IATRS application with proper configuration.
"""
import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_setup():
    """Check if application is properly set up."""
    issues = []
    
    # Check .env file
    if not Path(".env").exists():
        issues.append("⚠️  .env file not found - copy .env.example to .env")
    
    # Check uploads directory
    if not Path("uploads").exists():
        Path("uploads").mkdir(exist_ok=True)
    
    # Check logs directory
    if not Path("logs").exists():
        Path("logs").mkdir(exist_ok=True)
    
    if issues:
        print("Setup Issues:")
        for issue in issues:
            print(f"  {issue}")
        print()
    
    return len(issues) == 0


def main():
    """Run the application."""
    print("\n" + "=" * 60)
    print("  IATRS v2.0.0 - Starting Application")
    print("=" * 60 + "\n")
    
    # Check setup
    check_setup()
    
    # Get configuration
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("UVICORN_RELOAD", "true").lower() in ["true", "1", "yes"]
    
    print(f"📍 Host: http://{host}:{port}")
    print(f"📚 Docs: http://{host}:{port}/docs")
    print(f"🔧 Reload: {'Enabled' if reload else 'Disabled'}")
    print("\nPress CTRL+C to stop\n")
    
    # Start application
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

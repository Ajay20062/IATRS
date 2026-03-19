@echo off
echo Starting Smart ATS Recruitment System...
echo.

echo Activating Python virtual environment...
call venv\Scripts\activate

echo.
echo Starting Flask server...
echo Server will be available at: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.

python app.py

pause

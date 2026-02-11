@echo off
echo ==========================================
echo Starting AI Legal Consultant Web Server...
echo ==========================================

:: Check for .env file
if not exist .env (
    echo [WARNING] .env file not found. Please ensure OPENAI_API_KEY is set.
)

:: Start the FastAPI server in a new window
start "Legal AI Backend" cmd /k "python -m app.server"

:: Wait a few seconds for server to initialize
timeout /t 3 /nobreak > nul

:: Open the frontend in the default browser via localhost
echo Opening the UI in your browser...
start "" "http://localhost:8000"

echo ==========================================
echo Server is running at http://localhost:8000
echo UI is opened from web/index.html
echo ==========================================
pause

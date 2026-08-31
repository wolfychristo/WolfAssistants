@echo off
echo Starting Email Automation Tool...
echo.

echo Starting Backend (FastAPI)...
cd backend
start "Backend" cmd /k "python -m venv venv ; venv\Scripts\activate ; pip install -r requirements.txt ; python main.py"

echo.
echo Starting Frontend (React)...
cd ..\frontend
start "Frontend" cmd /k "npm install ; npm start"

echo.
echo Services are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit this launcher...
pause >nul

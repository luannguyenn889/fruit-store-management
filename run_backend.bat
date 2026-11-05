@echo off
if "%1" neq "spawned" (
    start "FruitStore Backend API (FastAPI)" cmd /k ""%~f0" spawned"
    exit /b
)

title FruitStore Backend API (FastAPI)
color 0A
echo ====================================================
echo   Khoi dong FruitStore Management Backend (FastAPI)
echo   Swagger UI: http://localhost:8000/docs
echo ====================================================
cd /d "%~dp0\backend"
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause

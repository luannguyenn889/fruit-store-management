@echo off
if "%1" neq "spawned" (
    start "Fresh Orchard Frontend (Angular)" cmd /k ""%~f0" spawned"
    exit /b
)

title Fresh Orchard Frontend (Angular)
color 0B
echo ====================================================
echo   Khoi dong Fresh Orchard Frontend (Angular)
echo   Trang chu: http://localhost:4200
echo ====================================================
cd /d "%~dp0\frontend"
npm start
pause

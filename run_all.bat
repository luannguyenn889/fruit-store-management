@echo off
echo Dang khoi dong toan bo he thong FruitStore (Backend + Frontend)...
start "" "%~dp0run_backend.bat"
timeout /t 2 /nobreak >nul
start "" "%~dp0run_frontend.bat"
echo Da khoi dong ca 2 cua so doc lap:
echo - Backend:  http://localhost:8000/docs
echo - Frontend: http://localhost:4200
exit


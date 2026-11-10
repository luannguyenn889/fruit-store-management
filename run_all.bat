@echo off
REM ============================================================================
REM MODULE: run_all.bat
REM NHIEM VU: Khoi dong dong loat toan bo he thong Backend SOA (3 process)
REM           va Angular Frontend (:4200) trong cac cua so Terminal rieng biet.
REM ============================================================================

echo Dang khoi dong toan bo he thong FruitStore SOA (Backend 3 Services + Angular Frontend)...
call "%~dp0run_backend.bat"
timeout /t 2 /nobreak >nul
call "%~dp0run_frontend.bat"
echo Da khoi dong thanh cong:
echo - API Gateway:     http://localhost:8000/docs
echo - Auth Service:    http://localhost:8001/docs
echo - Catalog Service: http://localhost:8002/docs
echo - Frontend UI:     http://localhost:4200
exit /b

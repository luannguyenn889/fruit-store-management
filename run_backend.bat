@echo off
REM ============================================================================
REM MODULE: run_backend.bat
REM NHIEM VU: Khoi dong 3 tien trinh Backend SOA doc lap trong 3 cua so Terminal:
REM           1. Auth Service    -> http://localhost:8001/docs (fruitstore_auth_db)
REM           2. Catalog Service -> http://localhost:8002/docs (fruitstore_catalog_db)
REM           3. API Gateway     -> http://localhost:8000/docs (Cong proxy chinh)
REM ============================================================================

echo ============================================================================
echo   KHOI DONG HE THONG BACKEND SOA FRUITSTORE (3 MICROSERVICES DOC LAP)
echo ============================================================================

REM 1. Khoi dong Auth Service (Cong 8001)
start "FruitStore - Auth Service (:8001)" cmd /k "color 0B && cd /d "%~dp0backend\services\auth-service" && "%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001"

REM 2. Khoi dong Catalog Service (Cong 8002)
start "FruitStore - Catalog Service (:8002)" cmd /k "color 0E && cd /d "%~dp0backend\services\catalog-service" && "%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002"

REM 3. Khoi dong API Gateway (Cong 8000)
start "FruitStore - API Gateway (:8000)" cmd /k "color 0A && cd /d "%~dp0backend\gateway" && "%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Da mo 3 cua so Terminal cho Auth Service (:8001), Catalog Service (:8002) va API Gateway (:8000).
exit /b

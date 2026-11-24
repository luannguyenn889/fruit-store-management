@echo off
REM ============================================================================
REM MODULE: run_backend.bat
REM NHIEM VU: Khoi dong 4 tien trinh Backend SOA doc lap trong 4 cua so Terminal:
REM           1. Auth Service      -> http://localhost:8001/docs (fruitstore_auth_db)
REM           2. Catalog Service   -> http://localhost:8002/docs (fruitstore_catalog_db)
REM           3. Inventory Service -> http://localhost:8003/docs (fruitstore_inventory_db)
REM           4. API Gateway       -> http://localhost:8000/docs (Cong proxy chinh)
REM ============================================================================

echo ============================================================================
echo   KHOI DONG HE THONG BACKEND SOA FRUITSTORE (4 MICROSERVICES DOC LAP)
echo ============================================================================

REM 1. Khoi dong Auth Service (Cong 8001)
start "FruitStore - Auth Service (:8001)" cmd /k "color 0B && cd /d "%~dp0backend\services\auth-service" && "%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001"

REM 2. Khoi dong Catalog Service (Cong 8002)
start "FruitStore - Catalog Service (:8002)" cmd /k "color 0E && cd /d "%~dp0backend\services\catalog-service" && "%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002"

REM 3. Khoi dong Inventory Service (Cong 8003)
start "FruitStore - Inventory Service (:8003)" cmd /k "color 0D && cd /d "%~dp0backend\services\inventory-service" && "%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8003"

REM 4. Khoi dong API Gateway (Cong 8000)
start "FruitStore - API Gateway (:8000)" cmd /k "color 0A && cd /d "%~dp0backend\gateway" && "%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Da mo 4 cua so Terminal cho Auth (:8001), Catalog (:8002), Inventory (:8003) va API Gateway (:8000).
exit /b

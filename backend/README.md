# Hướng dẫn Khởi tạo & Vận hành Backend SOA — FruitStore (Tuần 1)

> **Nhiệm vụ tài liệu:** Hướng dẫn từng bước cách thiết lập cơ sở dữ liệu độc lập (`Database-per-Service`), chạy Alembic migration, nạp dữ liệu mẫu (`seed`) và khởi chạy 3 tiến trình Backend (`API Gateway :8000`, `Auth Service :8001`, `Catalog Service :8002`).

---

## 1. Kiến trúc các dịch vụ (SOA Tuần 1)

| Dịch vụ | Thư mục | Cổng | Database sở hữu | DB Role riêng |
|---|---|---|---|---|
| **API Gateway** | `backend/gateway` | `:8000` | Không dùng DB | — |
| **Auth Service** | `backend/services/auth-service` | `:8001` | `fruitstore_auth_db` | `auth_user` |
| **Catalog Service** | `backend/services/catalog-service` | `:8002` | `fruitstore_catalog_db` | `catalog_user` |

---

## 2. Thứ tự khởi tạo lần đầu

### Bước 1: Tạo Database & Cô lập quyền truy cập (PostgreSQL Superuser)
1. Mở **pgAdmin 4** hoặc `psql` bằng tài khoản superuser `postgres`.
2. Mở file [`docs/databases/00_init_all_databases.sql`](../docs/databases/00_init_all_databases.sql), đổi mật khẩu placeholder `CHANGE_ME_auth` và `CHANGE_ME_catalog` (nếu muốn) cho khớp với file `.env` của từng service, sau đó thực thi script để tạo các role, tạo database và thu hồi quyền kết nối chéo (`REVOKE CONNECT ... FROM PUBLIC`).
3. Kết nối vào từng database (`fruitstore_auth_db` và `fruitstore_catalog_db`) bằng `postgres` để bật extension UUID:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   GRANT ALL ON SCHEMA public TO auth_user;    -- chạy trong fruitstore_auth_db
   GRANT ALL ON SCHEMA public TO catalog_user; -- chạy trong fruitstore_catalog_db
   ```

### Bước 2: Chạy Alembic Migration độc lập cho từng Service (NFR-M02)
Mở PowerShell tại thư mục gốc `d:\fruit-store-management`:

```powershell
# 1. Migration cho Auth Service (fruitstore_auth_db)
cd d:\fruit-store-management\backend\services\auth-service
..\..\.venv\Scripts\alembic.exe upgrade head

# 2. Migration cho Catalog Service (fruitstore_catalog_db)
cd d:\fruit-store-management\backend\services\catalog-service
..\..\.venv\Scripts\alembic.exe upgrade head
```

### Bước 3: Khởi tạo dữ liệu mẫu tường minh (Seed Data)
```powershell
# 1. Seed 5 vai trò RBAC & các tài khoản mẫu (admin@, manager@, staff@, warehouse@)
cd d:\fruit-store-management\backend\services\auth-service
..\..\.venv\Scripts\python.exe -m app.scripts.seed

# 2. Seed danh mục & các sản phẩm trái cây mẫu (Xoài cát Hòa Lộc, Táo Fuji, Cam sành...)
cd d:\fruit-store-management\backend\services\catalog-service
..\..\.venv\Scripts\python.exe -m app.scripts.seed
```

**Tài khoản mẫu mặc định sau khi seed:**
- **Manager:** `manager@fruitstore.com` / `Manager@123`
- **Admin:** `admin@fruitstore.com` / `Admin@123`
- **Staff (POS):** `staff@fruitstore.com` / `Staff@123`
- **Warehouse:** `warehouse@fruitstore.com` / `Warehouse@123`

### Bước 4: Khởi chạy 3 tiến trình Backend
Chạy file [`run_backend.bat`](../run_backend.bat) ở thư mục gốc (hoặc [`run_all.bat`](../run_all.bat) để bật cả Angular Frontend):
- **API Gateway Swagger:** http://localhost:8000/docs
- **Auth Service Swagger:** http://localhost:8001/docs
- **Catalog Service Swagger:** http://localhost:8002/docs

---

## 3. Chạy kiểm thử tự động (Unit, API & E2E Tests)

```powershell
# Kiểm thử Auth Service (bao gồm Alembic upgrade -> downgrade -> upgrade)
d:\fruit-store-management\backend\.venv\Scripts\pytest.exe -c d:\fruit-store-management\backend\services\auth-service\pytest.ini d:\fruit-store-management\backend\services\auth-service\tests\test_auth_api.py -q

# Kiểm thử Catalog Service (bao gồm PriceHistory, SELECT FOR UPDATE, RBAC, Alembic)
d:\fruit-store-management\backend\.venv\Scripts\pytest.exe -c d:\fruit-store-management\backend\services\catalog-service\pytest.ini d:\fruit-store-management\backend\services\catalog-service\tests\test_catalog_api.py -q

# Kiểm thử tích hợp End-to-End qua API Gateway (:8000 -> :8001 & :8002)
d:\fruit-store-management\backend\.venv\Scripts\pytest.exe -c d:\fruit-store-management\backend\services\auth-service\pytest.ini d:\fruit-store-management\backend\tests\e2e\test_catalog_via_gateway.py -q
```


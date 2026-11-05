# 01. Cơ Sở Dữ Liệu Dịch Vụ Xác Thực — Auth DB (`fruitstore_auth_db`)

## 1. Thông tin chung
- **Dịch vụ sở hữu:** `auth-service`
- **Tên Database:** `fruitstore_auth_db`
- **DB User:** `auth_user`
- **Chuỗi kết nối (FastAPI SQLAlchemy Async):**
  ```env
  DATABASE_URL=postgresql+psycopg://auth_user:auth_pass@postgres:5432/fruitstore_auth_db
  ```
- **Trách nhiệm dữ liệu:** Lưu trữ thông tin tài khoản đăng nhập, mật khẩu đã băm (bcrypt/argon2), danh sách vai trò (RBAC), gán quyền cho người dùng và quản lý Refresh Token.
- **Nguyên tắc cô lập SOA:** Không một dịch vụ nào khác được đọc trực tiếp bảng `users`. Các dịch vụ khác nhận thông tin người dùng (`sub`/`user_id`, `roles`) từ **JWT Access Token** hoặc gọi API nội bộ của `auth-service`.

---

## 2. Sơ đồ quan hệ thực thể (ERD)

```mermaid
erDiagram
    users ||--o{ user_roles : "có vai trò"
    roles ||--o{ user_roles : "được gán cho"
    users ||--o{ refresh_tokens : "sở hữu phiên"

    users {
        UUID id PK
        VARCHAR(255) email UK
        VARCHAR(20) phone UK
        VARCHAR(255) password_hash
        VARCHAR(150) full_name
        VARCHAR(20) status
        TIMESTAMPTZ last_login_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    roles {
        SMALLSERIAL id PK
        VARCHAR(50) code UK
        VARCHAR(100) name
        TEXT description
        TIMESTAMPTZ created_at
    }
    user_roles {
        UUID user_id PK, FK
        SMALLINT role_id PK, FK
        TIMESTAMPTZ assigned_at
    }
    refresh_tokens {
        UUID id PK
        UUID user_id FK
        VARCHAR(255) token_hash UK
        VARCHAR(255) user_agent
        VARCHAR(64) ip_address
        BOOLEAN is_revoked
        TIMESTAMPTZ expires_at
        TIMESTAMPTZ created_at
    }
```

---

## 3. Đặc tả chi tiết các bảng (Data Dictionary)

### 3.1. Bảng `users` (Tài khoản người dùng)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | Mã định danh duy nhất của người dùng (dùng làm `sub` trong JWT) |
| `email` | `VARCHAR(255)` | `NOT NULL, UNIQUE` | — | Email đăng nhập |
| `phone` | `VARCHAR(20)` | `UNIQUE, NULL` | `NULL` | Số điện thoại liên hệ |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | — | Mật khẩu đã mã hóa bằng Argon2/Bcrypt |
| `full_name` | `VARCHAR(150)` | `NOT NULL` | — | Họ và tên hiển thị |
| `status` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'ACTIVE'` | Trạng thái: `'ACTIVE'`, `'LOCKED'`, `'INACTIVE'` |
| `last_login_at` | `TIMESTAMPTZ` | `NULL` | `NULL` | Thời điểm đăng nhập gần nhất |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm tạo tài khoản |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật gần nhất |

### 3.2. Bảng `roles` (Danh mục vai trò RBAC)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `SMALLSERIAL` | `PRIMARY KEY` | Tự tăng | ID vai trò |
| `code` | `VARCHAR(50)` | `NOT NULL, UNIQUE` | — | Mã vai trò: `'ADMIN'`, `'MANAGER'`, `'STAFF'`, `'WAREHOUSE_STAFF'`, `'CUSTOMER'` |
| `name` | `VARCHAR(100)` | `NOT NULL` | — | Tên hiển thị tiếng Việt (VD: Quản trị viên, Nhân viên kho) |
| `description` | `TEXT` | `NULL` | `NULL` | Mô tả phạm vi quyền hạn |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Ngày tạo |

### 3.3. Bảng `user_roles` (Bảng trung gian Người dùng – Vai trò)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `user_id` | `UUID` | `PK, FK -> users(id) ON DELETE CASCADE` | — | ID người dùng |
| `role_id` | `SMALLINT` | `PK, FK -> roles(id) ON DELETE RESTRICT` | — | ID vai trò |
| `assigned_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm gán quyền |

### 3.4. Bảng `refresh_tokens` (Quản lý phiên làm mới JWT)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID bản ghi token |
| `user_id` | `UUID` | `NOT NULL, FK -> users(id) ON DELETE CASCADE` | — | Người dùng sở hữu phiên |
| `token_hash` | `VARCHAR(255)` | `NOT NULL, UNIQUE` | — | Mã băm SHA-256 của Refresh Token |
| `user_agent` | `VARCHAR(255)` | `NULL` | `NULL` | Thông tin trình duyệt/thiết bị |
| `ip_address` | `VARCHAR(64)` | `NULL` | `NULL` | Địa chỉ IP lúc đăng nhập |
| `is_revoked` | `BOOLEAN` | `NOT NULL` | `FALSE` | `TRUE` nếu đã đăng xuất hoặc bị thu hồi |
| `expires_at` | `TIMESTAMPTZ` | `NOT NULL` | — | Thời điểm hết hạn token |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cấp token |

---

## 4. Mã lệnh DDL chuẩn PostgreSQL 16

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE roles (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'LOCKED', 'INACTIVE')),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id SMALLINT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    user_agent VARCHAR(255),
    ip_address VARCHAR(64),
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_refresh_tokens_user_active ON refresh_tokens(user_id, expires_at)
    WHERE is_revoked = FALSE;

-- Dữ liệu khởi tạo (Seed Roles)
INSERT INTO roles (code, name, description) VALUES
('ADMIN', 'Quản trị viên', 'Toàn quyền cấu hình hệ thống và quản lý tài khoản'),
('MANAGER', 'Quản lý cửa hàng', 'Quản lý sản phẩm, giá bán, kho, nhà cung cấp và xem báo cáo'),
('STAFF', 'Nhân viên bán hàng', 'Bán hàng tại quầy POS, xử lý đơn hàng và thanh toán'),
('WAREHOUSE_STAFF', 'Nhân viên kho', 'Nhập hàng theo lô, kiểm kê và xử lý trái cây hết hạn/hư hỏng'),
('CUSTOMER', 'Khách hàng', 'Xem sản phẩm, đặt hàng trực tuyến và theo dõi đơn hàng');
```


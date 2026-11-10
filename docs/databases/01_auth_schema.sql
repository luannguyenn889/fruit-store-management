-- =============================================================================
-- DATABASE SCHEMA: Auth Service (fruitstore_auth_db)
-- Description: Quản lý người dùng, vai trò (RBAC), và Refresh Token
-- Engine: PostgreSQL 16+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Bảng danh mục vai trò (Roles)
CREATE TABLE IF NOT EXISTS roles (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Bảng tài khoản người dùng (Users)
CREATE TABLE IF NOT EXISTS users (
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

-- 3. Bảng gán vai trò người dùng (User Roles - Many-to-Many)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id SMALLINT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

-- 4. Bảng quản lý Refresh Token (Phiên đăng nhập)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    user_agent VARCHAR(255),
    ip_address VARCHAR(64),
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes tối ưu truy vấn
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_active 
    ON refresh_tokens(user_id, expires_at) 
    WHERE is_revoked = FALSE;

-- Dữ liệu khởi tạo mặc định các Roles (Seed Data)
INSERT INTO roles (code, name, description) VALUES
('ADMIN', 'Quản trị viên', 'Toàn quyền cấu hình hệ thống và quản trị tài khoản'),
('MANAGER', 'Quản lý cửa hàng', 'Quản lý sản phẩm, giá bán, kho, nhà cung cấp và xem báo cáo'),
('STAFF', 'Nhân viên bán hàng', 'Bán hàng tại quầy POS, xử lý đơn hàng và thanh toán'),
('WAREHOUSE', 'Nhân viên kho', 'Nhập hàng theo lô, kiểm kê và xử lý trái cây hết hạn/hư hỏng'),
('CUSTOMER', 'Khách hàng', 'Xem sản phẩm, đặt hàng trực tuyến và theo dõi đơn hàng')
ON CONFLICT (code) DO NOTHING;


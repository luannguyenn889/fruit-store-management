-- =============================================================================
-- DATABASE SCHEMA: Order Service (fruitstore_order_db)
-- Description: Quản lý khách hàng, đơn hàng (POS & Online), chi tiết đơn và lịch sử trạng thái
-- Engine: PostgreSQL 16+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Bảng Khách hàng (Customers)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE, -- Tham chiếu logic tới Auth Service nếu có tài khoản
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) UNIQUE,
    email VARCHAR(255),
    loyalty_points INT NOT NULL DEFAULT 0 CHECK (loyalty_points >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Bảng Sổ địa chỉ khách hàng (Customer Addresses)
CREATE TABLE IF NOT EXISTS customer_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    recipient_name VARCHAR(150) NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    address_line TEXT NOT NULL,
    ward VARCHAR(100),
    district VARCHAR(100),
    city VARCHAR(100),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Bảng Đơn hàng (Orders)
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_code VARCHAR(40) NOT NULL UNIQUE,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'ONLINE'
        CHECK (channel IN ('POS', 'ONLINE')),
    status VARCHAR(25) NOT NULL DEFAULT 'PENDING_PAYMENT'
        CHECK (status IN ('PENDING_PAYMENT', 'PAID', 'PROCESSING', 'SHIPPING', 'COMPLETED', 'CANCELLED', 'EXPIRED')),
    payment_status VARCHAR(20) NOT NULL DEFAULT 'UNPAID'
        CHECK (payment_status IN ('UNPAID', 'PAID', 'FAILED', 'REFUNDED')),
    subtotal NUMERIC(14, 2) NOT NULL CHECK (subtotal >= 0),
    discount_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    shipping_fee NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (shipping_fee >= 0),
    total_amount NUMERIC(14, 2) NOT NULL CHECK (total_amount >= 0),
    shipping_address_snapshot TEXT,
    note TEXT,
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    created_by_staff_id UUID, -- Thu ngân nếu bán qua POS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Bảng Chi tiết từng loại trái cây trong đơn (Order Items - Snapshot giá & thông tin)
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL, -- Tham chiếu logic tới Catalog Service
    product_sku_snapshot VARCHAR(50) NOT NULL,
    product_name_snapshot VARCHAR(200) NOT NULL,
    unit_snapshot VARCHAR(20) NOT NULL DEFAULT 'kg',
    quantity NUMERIC(10, 3) NOT NULL CHECK (quantity > 0),
    unit_price_snapshot NUMERIC(14, 2) NOT NULL CHECK (unit_price_snapshot >= 0),
    line_total NUMERIC(14, 2) NOT NULL CHECK (line_total >= 0)
);

-- 5. Bảng Lịch sử chuyển trạng thái đơn (Order Status History)
CREATE TABLE IF NOT EXISTS order_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    old_status VARCHAR(25),
    new_status VARCHAR(25) NOT NULL,
    note TEXT,
    changed_by_user_id UUID,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes tối ưu danh sách đơn và lọc đơn
CREATE INDEX IF NOT EXISTS idx_orders_customer_created ON orders(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);


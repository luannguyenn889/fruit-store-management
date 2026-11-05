-- =============================================================================
-- DATABASE SCHEMA: Inventory Service (fruitstore_inventory_db)
-- Description: Quản lý nhà cung cấp, phiếu nhập kho, lô hàng (FEFO), giữ hàng, và biến động kho
-- Engine: PostgreSQL 16+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Bảng Nhà cung cấp (Suppliers)
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Bảng Phiếu nhập kho (Purchase Orders)
CREATE TABLE IF NOT EXISTS purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_number VARCHAR(50) NOT NULL UNIQUE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'RECEIVED', 'CANCELLED')),
    total_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    created_by_user_id UUID, -- Tham chiếu logic tới Auth Service
    note TEXT,
    received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Bảng Chi tiết phiếu nhập (Purchase Items)
CREATE TABLE IF NOT EXISTS purchase_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL, -- Tham chiếu logic tới Catalog Service
    quantity_ordered NUMERIC(10, 3) NOT NULL CHECK (quantity_ordered > 0),
    quantity_received NUMERIC(10, 3) NOT NULL DEFAULT 0 CHECK (quantity_received >= 0),
    unit_cost NUMERIC(14, 2) NOT NULL CHECK (unit_cost >= 0),
    expiry_date DATE NOT NULL
);

-- 4. Bảng Lô hàng tồn kho (Stock Lots - Quản lý hạn dùng FEFO)
CREATE TABLE IF NOT EXISTS stock_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_code VARCHAR(60) NOT NULL UNIQUE,
    product_id UUID NOT NULL, -- Tham chiếu logic tới Catalog Service
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    purchase_order_id UUID REFERENCES purchase_orders(id) ON DELETE SET NULL,
    quantity_received NUMERIC(10, 3) NOT NULL CHECK (quantity_received > 0),
    quantity_remaining NUMERIC(10, 3) NOT NULL CHECK (quantity_remaining >= 0),
    quantity_reserved NUMERIC(10, 3) NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    unit_cost NUMERIC(14, 2) NOT NULL CHECK (unit_cost >= 0),
    received_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expiry_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE'
        CHECK (status IN ('AVAILABLE', 'NEAR_EXPIRY', 'EXPIRED', 'DEPLETED', 'BLOCKED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_lot_dates CHECK (expiry_date >= received_date),
    CONSTRAINT chk_lot_quantities CHECK (quantity_remaining >= quantity_reserved)
);

-- 5. Bảng Giữ hàng khi đặt đơn (Reservations)
CREATE TABLE IF NOT EXISTS reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL UNIQUE, -- Tham chiếu logic tới Order Service
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'COMMITTED', 'RELEASED', 'EXPIRED')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Bảng Chi tiết giữ hàng theo từng lô (Reservation Items - Cốt lõi FEFO)
CREATE TABLE IF NOT EXISTS reservation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id UUID NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    lot_id UUID NOT NULL REFERENCES stock_lots(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL CHECK (quantity > 0)
);

-- 7. Bảng Nhật ký biến động kho (Stock Movements - Audit trail)
CREATE TABLE IF NOT EXISTS stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id UUID NOT NULL REFERENCES stock_lots(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL,
    movement_type VARCHAR(30) NOT NULL
        CHECK (movement_type IN ('IN', 'SALE_OUT', 'WASTE_EXPIRED', 'WASTE_DAMAGED', 'ADJUSTMENT')),
    quantity_change NUMERIC(10, 3) NOT NULL CHECK (quantity_change <> 0),
    unit_cost_snapshot NUMERIC(14, 2) NOT NULL CHECK (unit_cost_snapshot >= 0),
    reference_type VARCHAR(30) NOT NULL,
    reference_id UUID,
    idempotency_key VARCHAR(100) UNIQUE,
    reason TEXT,
    performed_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes tối ưu thuật toán xuất kho FEFO (First Expired, First Out)
CREATE INDEX IF NOT EXISTS idx_stock_lots_fefo
    ON stock_lots(product_id, expiry_date ASC)
    WHERE status IN ('AVAILABLE', 'NEAR_EXPIRY') AND quantity_remaining > quantity_reserved;

-- Index cảnh báo hàng sắp hết hạn
CREATE INDEX IF NOT EXISTS idx_stock_lots_expiring
    ON stock_lots(expiry_date ASC)
    WHERE status IN ('AVAILABLE', 'NEAR_EXPIRY') AND quantity_remaining > 0;


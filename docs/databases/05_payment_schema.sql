-- =============================================================================
-- DATABASE SCHEMA: Payment Service (fruitstore_payment_db)
-- Description: Quản lý giao dịch thanh toán, hoàn tiền và sự kiện callback/webhook
-- Engine: PostgreSQL 16+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Bảng Giao dịch thanh toán (Payments)
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL, -- Tham chiếu logic tới Order Service
    order_code VARCHAR(40) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    method VARCHAR(30) NOT NULL
        CHECK (method IN ('CASH', 'BANK_QR', 'VNPAY_MOCK', 'MOMO_MOCK')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'REFUNDED')),
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    provider_transaction_id VARCHAR(150) UNIQUE,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ràng buộc mỗi đơn hàng chỉ có duy nhất 1 giao dịch thành công (SUCCEEDED)
CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_order_succeeded
    ON payments(order_id) WHERE status = 'SUCCEEDED';

-- 2. Bảng Hoàn tiền (Refunds)
CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'SUCCEEDED', 'FAILED')),
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    reason TEXT NOT NULL,
    requested_by_user_id UUID,
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Bảng Nhật ký sự kiện & Webhook Callback (Payment Events)
CREATE TABLE IF NOT EXISTS payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    provider_event_id VARCHAR(150) UNIQUE,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes tối ưu tra cứu giao dịch
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status_created ON payments(status, created_at DESC);


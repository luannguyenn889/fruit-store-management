-- =============================================================================
-- DATABASE SCHEMA: Reporting Service (fruitstore_reporting_db)
-- Description: Read Model tổng hợp doanh thu theo ngày, sản phẩm bán chạy, hao hụt và tồn kho
-- Engine: PostgreSQL 16+
-- =============================================================================

-- 1. Bảng Tổng hợp doanh thu theo ngày (Daily Sales Summary)
CREATE TABLE IF NOT EXISTS daily_sales_summary (
    report_date DATE PRIMARY KEY,
    total_orders INT NOT NULL DEFAULT 0,
    pos_orders INT NOT NULL DEFAULT 0,
    online_orders INT NOT NULL DEFAULT 0,
    cancelled_orders INT NOT NULL DEFAULT 0,
    gross_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0,
    discount_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    net_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Bảng Tổng hợp doanh số theo từng loại trái cây (Product Sales Summary)
CREATE TABLE IF NOT EXISTS product_sales_summary (
    report_date DATE NOT NULL,
    product_id UUID NOT NULL,
    product_sku VARCHAR(50) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'kg',
    quantity_sold NUMERIC(10, 3) NOT NULL DEFAULT 0,
    revenue NUMERIC(14, 2) NOT NULL DEFAULT 0,
    estimated_cogs NUMERIC(14, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (report_date, product_id)
);

-- 3. Bảng Tổng hợp hao hụt và hủy trái cây hỏng/hết hạn (Wastage Summary)
CREATE TABLE IF NOT EXISTS wastage_summary (
    report_date DATE NOT NULL,
    product_id UUID NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'kg',
    expired_quantity NUMERIC(10, 3) NOT NULL DEFAULT 0,
    damaged_quantity NUMERIC(10, 3) NOT NULL DEFAULT 0,
    total_loss_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (report_date, product_id)
);

-- 4. Bảng Chụp ảnh nhanh giá trị tồn kho theo ngày (Inventory Snapshots)
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    snapshot_date DATE NOT NULL,
    product_id UUID NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    total_remaining NUMERIC(10, 3) NOT NULL DEFAULT 0,
    total_reserved NUMERIC(10, 3) NOT NULL DEFAULT 0,
    expiring_soon_qty NUMERIC(10, 3) NOT NULL DEFAULT 0,
    inventory_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_date, product_id)
);

-- 5. Bảng Điểm mốc đồng bộ dữ liệu (Sync Checkpoints)
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    source_service VARCHAR(50) PRIMARY KEY,
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'IDLE',
    last_error TEXT
);

-- Indexes tối ưu báo cáo sản phẩm bán chạy nhất
CREATE INDEX IF NOT EXISTS idx_product_sales_date_rev 
    ON product_sales_summary(report_date, revenue DESC);


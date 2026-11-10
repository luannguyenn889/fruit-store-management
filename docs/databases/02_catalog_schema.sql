-- =============================================================================
-- DATABASE SCHEMA: Catalog Service (fruitstore_catalog_db)
-- Description: Quản lý danh mục, sản phẩm trái cây, hình ảnh, và lịch sử đổi giá
-- Engine: PostgreSQL 16+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Bảng danh mục sản phẩm (Categories)
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Bảng sản phẩm trái cây (Products)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    unit VARCHAR(20) NOT NULL DEFAULT 'kg'
        CHECK (unit IN ('kg', 'hop', 'qua')),
    price NUMERIC(14, 2) NOT NULL CHECK (price >= 0),
    origin VARCHAR(150),
    default_shelf_life_days INT NOT NULL DEFAULT 7 CHECK (default_shelf_life_days > 0),
    storage_condition VARCHAR(30) NOT NULL DEFAULT 'COOL_2_8C'
        CHECK (storage_condition IN ('AMBIENT', 'COOL_2_8C', 'COOL_8_12C')),
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'OUT_OF_SEASON')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Bảng hình ảnh sản phẩm (Product Images)
CREATE TABLE IF NOT EXISTS product_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    alt_text VARCHAR(200),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ràng buộc mỗi sản phẩm chỉ có tối đa 1 ảnh chính
CREATE UNIQUE INDEX IF NOT EXISTS uq_product_primary_image
    ON product_images(product_id) WHERE is_primary = TRUE;

-- 4. Bảng lịch sử thay đổi giá bán (Price History)
CREATE TABLE IF NOT EXISTS price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    old_price NUMERIC(14, 2) NOT NULL CHECK (old_price >= 0),
    new_price NUMERIC(14, 2) NOT NULL CHECK (new_price >= 0),
    changed_by_user_id UUID, -- Tham chiếu logic tới Auth Service
    reason VARCHAR(255),
    effective_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes tối ưu tra cứu và tìm kiếm
CREATE INDEX IF NOT EXISTS idx_products_category_status ON products(category_id, status);
CREATE INDEX IF NOT EXISTS idx_products_name_search ON products USING gin (to_tsvector('simple', name));


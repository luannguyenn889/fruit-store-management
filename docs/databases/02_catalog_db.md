# 02. Cơ Sở Dữ Liệu Dịch Vụ Sản Phẩm — Catalog DB (`fruitstore_catalog_db`)

## 1. Thông tin chung
- **Dịch vụ sở hữu:** `catalog-service`
- **Tên Database:** `fruitstore_catalog_db`
- **DB User:** `catalog_user`
- **Chuỗi kết nối (FastAPI SQLAlchemy Async):**
  ```env
  DATABASE_URL=postgresql+psycopg://catalog_user:catalog_pass@postgres:5432/fruitstore_catalog_db
  ```
- **Trách nhiệm dữ liệu:** Quản lý danh mục trái cây, thông tin chi tiết sản phẩm, đơn vị tính (`kg`, `hop`, `qua`), nguồn gốc xuất xứ, điều kiện bảo quản, giá bán hiện hành, lịch sử thay đổi giá và đường dẫn hình ảnh sản phẩm.
- **Chiến lược lưu hình ảnh:** File ảnh vật lý (`.webp`, `.jpg`, `.png`) lưu tại Docker Volume `/storage/products/`. Database chỉ lưu đường dẫn tương đối (ví dụ `/media/products/xoai-cat-hoa-loc.webp`).

---

## 2. Sơ đồ quan hệ thực thể (ERD)

```mermaid
erDiagram
    categories ||--o{ products : "phân loại"
    products ||--o{ product_images : "có hình ảnh"
    products ||--o{ price_history : "lưu vết giá"

    categories {
        UUID id PK
        VARCHAR(100) name
        VARCHAR(120) slug UK
        TEXT description
        BOOLEAN is_active
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    products {
        UUID id PK
        UUID category_id FK
        VARCHAR(50) sku UK
        VARCHAR(200) name
        VARCHAR(220) slug UK
        VARCHAR(20) unit
        NUMERIC(14_2) price
        VARCHAR(150) origin
        INT default_shelf_life_days
        VARCHAR(30) storage_condition
        TEXT description
        VARCHAR(20) status
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    product_images {
        UUID id PK
        UUID product_id FK
        VARCHAR(500) image_url
        VARCHAR(200) alt_text
        BOOLEAN is_primary
        SMALLINT sort_order
        TIMESTAMPTZ created_at
    }
    price_history {
        UUID id PK
        UUID product_id FK
        NUMERIC(14_2) old_price
        NUMERIC(14_2) new_price
        UUID changed_by_user_id "Logic ref -> Auth DB"
        VARCHAR(255) reason
        TIMESTAMPTZ effective_at
    }
```

---

## 3. Đặc tả chi tiết các bảng (Data Dictionary)

### 3.1. Bảng `categories` (Danh mục trái cây)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | Mã danh mục |
| `name` | `VARCHAR(100)` | `NOT NULL` | — | Tên danh mục (VD: Trái cây nội địa, Trái cây nhập khẩu, Giỏ quà) |
| `slug` | `VARCHAR(120)` | `NOT NULL, UNIQUE` | — | Đường dẫn thân thiện SEO (VD: `trai-cay-nhap-khau`) |
| `description` | `TEXT` | `NULL` | `NULL` | Mô tả danh mục |
| `is_active` | `BOOLEAN` | `NOT NULL` | `TRUE` | Trạng thái hiển thị |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm tạo |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật |

### 3.2. Bảng `products` (Thông tin trái cây)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | Mã định danh sản phẩm (tham chiếu bởi Inventory, Order) |
| `category_id` | `UUID` | `NOT NULL, FK -> categories(id)` | — | Thuộc danh mục |
| `sku` | `VARCHAR(50)` | `NOT NULL, UNIQUE` | — | Mã hàng hóa (VD: `FRT-XOAI-001`, `FRT-TAO-FUJI`) |
| `name` | `VARCHAR(200)` | `NOT NULL` | — | Tên trái cây (VD: Xoài cát Hòa Lộc) |
| `slug` | `VARCHAR(220)` | `NOT NULL, UNIQUE` | — | Slug URL (VD: `xoai-cat-hoa-loc`) |
| `unit` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'kg'` | Đơn vị tính: `'kg'`, `'hop'`, `'qua'` |
| `price` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | — | Giá bán hiện hành trên 1 đơn vị tính (VNĐ) |
| `origin` | `VARCHAR(150)` | `NULL` | `NULL` | Nguồn gốc xuất xứ (VD: Tiền Giang, Nhập khẩu Úc) |
| `default_shelf_life_days` | `INT` | `NOT NULL, CHECK (> 0)` | `7` | Số ngày bảo quản tiêu chuẩn (gợi ý hạn dùng khi nhập kho) |
| `storage_condition` | `VARCHAR(30)` | `NOT NULL` | `'COOL_2_8C'` | Điều kiện bảo quản: `'AMBIENT'`, `'COOL_2_8C'`, `'COOL_8_12C'` |
| `description` | `TEXT` | `NULL` | `NULL` | Mô tả hương vị, dinh dưỡng, cách bảo quản |
| `status` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'ACTIVE'` | `'ACTIVE'`, `'INACTIVE'`, `'OUT_OF_SEASON'` |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm tạo |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật |

### 3.3. Bảng `product_images` (Hình ảnh sản phẩm)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID ảnh |
| `product_id` | `UUID` | `NOT NULL, FK -> products(id) ON DELETE CASCADE` | — | Sản phẩm sở hữu ảnh |
| `image_url` | `VARCHAR(500)` | `NOT NULL` | — | Đường dẫn ảnh (VD: `/media/products/tao-fuji.webp`) |
| `alt_text` | `VARCHAR(200)` | `NULL` | `NULL` | Văn bản thay thế |
| `is_primary` | `BOOLEAN` | `NOT NULL` | `FALSE` | Ảnh đại diện chính của sản phẩm |
| `sort_order` | `SMALLINT` | `NOT NULL` | `0` | Thứ tự hiển thị trong gallery |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm tải lên |

### 3.4. Bảng `price_history` (Lịch sử thay đổi giá bán)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID bản ghi lịch sử giá |
| `product_id` | `UUID` | `NOT NULL, FK -> products(id) ON DELETE CASCADE` | — | Sản phẩm thay đổi giá |
| `old_price` | `NUMERIC(14, 2)` | `NOT NULL` | — | Giá cũ trước khi đổi |
| `new_price` | `NUMERIC(14, 2)` | `NOT NULL` | — | Giá mới |
| `changed_by_user_id` | `UUID` | `NULL` | `NULL` | Tham chiếu logic tới `users.id` (Auth DB) |
| `reason` | `VARCHAR(255)` | `NULL` | `NULL` | Lý do đổi giá (VD: Khuyến mãi cuối tuần, Giá mùa vụ) |
| `effective_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm áp dụng |

---

## 4. Mã lệnh DDL chuẩn PostgreSQL 16

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
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

CREATE TABLE product_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    alt_text VARCHAR(200),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Đảm bảo mỗi sản phẩm chỉ có tối đa 1 ảnh chính (is_primary = TRUE)
CREATE UNIQUE INDEX uq_product_primary_image
    ON product_images(product_id) WHERE is_primary = TRUE;

CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    old_price NUMERIC(14, 2) NOT NULL CHECK (old_price >= 0),
    new_price NUMERIC(14, 2) NOT NULL CHECK (new_price >= 0),
    changed_by_user_id UUID,
    reason VARCHAR(255),
    effective_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_category_status ON products(category_id, status);
CREATE INDEX idx_products_name_search ON products USING gin (to_tsvector('simple', name));
```


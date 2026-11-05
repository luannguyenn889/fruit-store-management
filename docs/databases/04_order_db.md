# 04. Cơ Sở Dữ Liệu Dịch Vụ Đơn Hàng & Khách Hàng — Order DB (`fruitstore_order_db`)

## 1. Thông tin chung
- **Dịch vụ sở hữu:** `order-service`
- **Tên Database:** `fruitstore_order_db`
- **DB User:** `order_user`
- **Chuỗi kết nối (FastAPI SQLAlchemy Async):**
  ```env
  DATABASE_URL=postgresql+psycopg://order_user:order_pass@postgres:5432/fruitstore_order_db
  ```
- **Trách nhiệm dữ liệu:**
  - Quản lý hồ sơ khách hàng (`customers`) và sổ địa chỉ giao hàng (`customer_addresses`).
  - Quản lý đơn hàng bán tại quầy POS và đơn đặt trực tuyến (`orders`).
  - Lưu chi tiết mặt hàng trong đơn (`order_items`) kèm **bản chụp (snapshot)** tên sản phẩm, mã SKU, đơn vị tính và đơn giá tại đúng thời điểm mua.
  - Lưu lịch sử chuyển trạng thái đơn hàng (`order_status_history`).

---

## 2. Sơ đồ quan hệ thực thể (ERD)

```mermaid
erDiagram
    customers ||--o{ customer_addresses : "có địa chỉ"
    customers ||--o{ orders : "đặt đơn"
    orders ||--o{ order_items : "gồm các món"
    orders ||--o{ order_status_history : "lịch sử trạng thái"

    customers {
        UUID id PK
        UUID user_id UK "Logic ref -> Auth DB (NULL cho khách vãng lai)"
        VARCHAR(150) full_name
        VARCHAR(20) phone UK
        VARCHAR(255) email
        INT loyalty_points
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    customer_addresses {
        UUID id PK
        UUID customer_id FK
        VARCHAR(150) recipient_name
        VARCHAR(20) recipient_phone
        TEXT address_line
        VARCHAR(100) ward
        VARCHAR(100) district
        VARCHAR(100) city
        BOOLEAN is_default
        TIMESTAMPTZ created_at
    }
    orders {
        UUID id PK
        VARCHAR(40) order_code UK
        UUID customer_id FK "NULLable (khách lẻ POS)"
        VARCHAR(20) channel "POS | ONLINE"
        VARCHAR(25) status
        VARCHAR(20) payment_status
        NUMERIC(14_2) subtotal
        NUMERIC(14_2) discount_amount
        NUMERIC(14_2) shipping_fee
        NUMERIC(14_2) total_amount
        TEXT shipping_address_snapshot
        TEXT note
        VARCHAR(100) idempotency_key UK
        UUID created_by_staff_id "Logic ref -> Auth DB"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    order_items {
        UUID id PK
        UUID order_id FK
        UUID product_id "Logic ref -> Catalog DB"
        VARCHAR(50) product_sku_snapshot
        VARCHAR(200) product_name_snapshot
        VARCHAR(20) unit_snapshot
        NUMERIC(10_3) quantity
        NUMERIC(14_2) unit_price_snapshot
        NUMERIC(14_2) line_total
    }
    order_status_history {
        UUID id PK
        UUID order_id FK
        VARCHAR(25) old_status
        VARCHAR(25) new_status
        TEXT note
        UUID changed_by_user_id "Logic ref -> Auth DB"
        TIMESTAMPTZ changed_at
    }
```

---

## 3. Đặc tả chi tiết các bảng (Data Dictionary)

### 3.1. Bảng `customers` (Hồ sơ khách hàng)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID khách hàng |
| `user_id` | `UUID` | `UNIQUE, NULL` | `NULL` | Liên kết logic với `users.id` (Auth DB) nếu khách có tài khoản online |
| `full_name` | `VARCHAR(150)` | `NOT NULL` | — | Họ tên khách hàng |
| `phone` | `VARCHAR(20)` | `UNIQUE, NULL` | `NULL` | Số điện thoại tích điểm / tra cứu tại POS |
| `email` | `VARCHAR(255)` | `NULL` | `NULL` | Email nhận hóa đơn |
| `loyalty_points` | `INT` | `NOT NULL, CHECK (>= 0)` | `0` | Điểm tích lũy |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Ngày tạo |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Ngày cập nhật |

### 3.2. Bảng `orders` (Đơn hàng)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID đơn hàng |
| `order_code` | `VARCHAR(40)` | `NOT NULL, UNIQUE` | — | Mã đơn hiển thị (VD: `ORD-20261022-0001`) |
| `customer_id` | `UUID` | `NULL, FK -> customers(id)` | `NULL` | Khách mua (có thể `NULL` khi khách lẻ mua nhanh tại POS) |
| `channel` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'ONLINE'` | Kênh bán: `'POS'` (tại quầy) hoặc `'ONLINE'` (đặt web) |
| `status` | `VARCHAR(25)` | `NOT NULL, CHECK` | `'PENDING_PAYMENT'` | `'PENDING_PAYMENT'`, `'PAID'`, `'PROCESSING'`, `'SHIPPING'`, `'COMPLETED'`, `'CANCELLED'`, `'EXPIRED'` |
| `payment_status` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'UNPAID'` | `'UNPAID'`, `'PAID'`, `'FAILED'`, `'REFUNDED'` |
| `subtotal` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | — | Tổng tiền hàng trước giảm giá |
| `discount_amount` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | `0` | Số tiền giảm giá |
| `shipping_fee` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | `0` | Phí giao hàng |
| `total_amount` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | — | Tổng thanh toán (`subtotal - discount_amount + shipping_fee`) |
| `shipping_address_snapshot` | `TEXT` | `NULL` | `NULL` | Địa chỉ người nhận chụp lại lúc đặt đơn |
| `note` | `TEXT` | `NULL` | `NULL` | Ghi chú của khách hoặc thu ngân |
| `idempotency_key` | `VARCHAR(100)` | `NOT NULL, UNIQUE` | — | Khóa chống tạo đơn trùng khi retry mạng |
| `created_by_staff_id` | `UUID` | `NULL` | `NULL` | Nhân viên thu ngân tạo đơn (nếu `channel = 'POS'`) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm đặt hàng |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật |

### 3.3. Bảng `order_items` (Chi tiết từng loại trái cây trong đơn)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID dòng chi tiết |
| `order_id` | `UUID` | `NOT NULL, FK -> orders(id) ON DELETE CASCADE` | — | Thuộc đơn hàng |
| `product_id` | `UUID` | `NOT NULL` | — | Tham chiếu logic tới `products.id` (Catalog DB) |
| `product_sku_snapshot` | `VARCHAR(50)` | `NOT NULL` | — | Mã SKU tại thời điểm mua |
| `product_name_snapshot` | `VARCHAR(200)` | `NOT NULL` | — | Tên trái cây tại thời điểm mua |
| `unit_snapshot` | `VARCHAR(20)` | `NOT NULL` | `'kg'` | Đơn vị tính tại thời điểm mua |
| `quantity` | `NUMERIC(10, 3)` | `NOT NULL, CHECK (> 0)` | — | Khối lượng/số lượng mua (VD: `2.500` kg) |
| `unit_price_snapshot` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | — | Đơn giá tại thời điểm mua (VNĐ) |
| `line_total` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | — | Thành tiền (`ROUND(quantity * unit_price_snapshot, 2)`) |

---

## 4. Mã lệnh DDL chuẩn PostgreSQL 16

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) UNIQUE,
    email VARCHAR(255),
    loyalty_points INT NOT NULL DEFAULT 0 CHECK (loyalty_points >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE customer_addresses (
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

CREATE TABLE orders (
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
    created_by_staff_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL,
    product_sku_snapshot VARCHAR(50) NOT NULL,
    product_name_snapshot VARCHAR(200) NOT NULL,
    unit_snapshot VARCHAR(20) NOT NULL DEFAULT 'kg',
    quantity NUMERIC(10, 3) NOT NULL CHECK (quantity > 0),
    unit_price_snapshot NUMERIC(14, 2) NOT NULL CHECK (unit_price_snapshot >= 0),
    line_total NUMERIC(14, 2) NOT NULL CHECK (line_total >= 0)
);

CREATE TABLE order_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    old_status VARCHAR(25),
    new_status VARCHAR(25) NOT NULL,
    note TEXT,
    changed_by_user_id UUID,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_customer_created ON orders(customer_id, created_at DESC);
CREATE INDEX idx_orders_status_created ON orders(status, created_at DESC);
CREATE INDEX idx_order_items_product ON order_items(product_id);
```


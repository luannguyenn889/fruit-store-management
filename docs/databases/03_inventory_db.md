# 03. Cơ Sở Dữ Liệu Dịch Vụ Kho & Lô Hàng — Inventory DB (`fruitstore_inventory_db`)

## 1. Thông tin chung
- **Dịch vụ sở hữu:** `inventory-service`
- **Tên Database:** `fruitstore_inventory_db`
- **DB User:** `inventory_user`
- **Chuỗi kết nối (FastAPI SQLAlchemy Async):**
  ```env
  DATABASE_URL=postgresql+psycopg://inventory_user:inventory_pass@postgres:5432/fruitstore_inventory_db
  ```
- **Trách nhiệm dữ liệu:**
  - Quản lý nhà cung cấp (`suppliers`) và phiếu nhập kho (`purchase_orders`, `purchase_items`).
  - Quản lý tồn kho trái cây theo **từng lô hàng (`stock_lots`)** gắn với ngày nhập, hạn sử dụng (`expiry_date`) và giá vốn (`unit_cost`).
  - Thực thi thuật toán **FEFO (First Expired, First Out)**: ưu tiên giữ hàng và xuất kho ở lô có hạn sử dụng gần nhất.
  - Quản lý giữ hàng tạm thời (`reservations`, `reservation_items`) khi khách đặt đơn chờ thanh toán.
  - Ghi vết mọi biến động kho (`stock_movements`): nhập kho, xuất bán, hủy hàng hết hạn/hư hỏng, kiểm kê điều chỉnh.

---

## 2. Sơ đồ quan hệ thực thể (ERD)

```mermaid
erDiagram
    suppliers ||--o{ purchase_orders : "cung cấp"
    purchase_orders ||--o{ purchase_items : "chi tiết nhập"
    suppliers ||--o{ stock_lots : "nguồn hàng"
    purchase_orders ||--o{ stock_lots : "sinh ra lô"
    stock_lots ||--o{ stock_movements : "biến động"
    reservations ||--o{ reservation_items : "chi tiết giữ"
    stock_lots ||--o{ reservation_items : "giữ từ lô"

    suppliers {
        UUID id PK
        VARCHAR(50) code UK
        VARCHAR(200) name
        VARCHAR(20) phone
        VARCHAR(255) email
        TEXT address
        BOOLEAN is_active
        TIMESTAMPTZ created_at
    }
    purchase_orders {
        UUID id PK
        VARCHAR(50) po_number UK
        UUID supplier_id FK
        VARCHAR(20) status
        NUMERIC(14_2) total_amount
        UUID created_by_user_id "Logic ref -> Auth DB"
        TEXT note
        TIMESTAMPTZ received_at
        TIMESTAMPTZ created_at
    }
    purchase_items {
        UUID id PK
        UUID purchase_order_id FK
        UUID product_id "Logic ref -> Catalog DB"
        NUMERIC(10_3) quantity_ordered
        NUMERIC(10_3) quantity_received
        NUMERIC(14_2) unit_cost
        DATE expiry_date
    }
    stock_lots {
        UUID id PK
        VARCHAR(60) lot_code UK
        UUID product_id "Logic ref -> Catalog DB"
        UUID supplier_id FK
        UUID purchase_order_id FK
        NUMERIC(10_3) quantity_received
        NUMERIC(10_3) quantity_remaining
        NUMERIC(10_3) quantity_reserved
        NUMERIC(14_2) unit_cost
        DATE received_date
        DATE expiry_date
        VARCHAR(20) status
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    reservations {
        UUID id PK
        UUID order_id UK "Logic ref -> Order DB"
        VARCHAR(100) idempotency_key UK
        VARCHAR(20) status
        TIMESTAMPTZ expires_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    reservation_items {
        UUID id PK
        UUID reservation_id FK
        UUID lot_id FK
        UUID product_id "Logic ref -> Catalog DB"
        NUMERIC(10_3) quantity
    }
    stock_movements {
        UUID id PK
        UUID lot_id FK
        UUID product_id "Logic ref -> Catalog DB"
        VARCHAR(30) movement_type
        NUMERIC(10_3) quantity_change
        NUMERIC(14_2) unit_cost_snapshot
        VARCHAR(30) reference_type
        UUID reference_id
        VARCHAR(100) idempotency_key UK
        TEXT reason
        UUID performed_by_user_id "Logic ref -> Auth DB"
        TIMESTAMPTZ created_at
    }
```

---

## 3. Đặc tả chi tiết các bảng (Data Dictionary)

### 3.1. Bảng `suppliers` (Nhà cung cấp trái cây)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID nhà cung cấp |
| `code` | `VARCHAR(50)` | `NOT NULL, UNIQUE` | — | Mã NCC (VD: `NCC-HOALOC-01`) |
| `name` | `VARCHAR(200)` | `NOT NULL` | — | Tên nhà vườn / công ty nhập khẩu |
| `phone` | `VARCHAR(20)` | `NULL` | `NULL` | Số điện thoại |
| `email` | `VARCHAR(255)` | `NULL` | `NULL` | Email liên hệ |
| `address` | `TEXT` | `NULL` | `NULL` | Địa chỉ |
| `is_active` | `BOOLEAN` | `NOT NULL` | `TRUE` | Đang hợp tác |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Ngày tạo |

### 3.2. Bảng `purchase_orders` & `purchase_items` (Phiếu nhập kho)
- `purchase_orders`: Lưu thông tin tổng quát phiếu nhập (`po_number`, `supplier_id`, `status`: `'DRAFT'`, `'RECEIVED'`, `'CANCELLED'`, `total_amount`, `received_at`).
- `purchase_items`: Chi tiết từng mặt hàng trái cây trong phiếu nhập (`product_id`, `quantity_ordered`, `quantity_received`, `unit_cost`, `expiry_date`). Khi phiếu chuyển sang `'RECEIVED'`, hệ thống tự động sinh các lô tương ứng trong `stock_lots`.

### 3.3. Bảng `stock_lots` (Lô trái cây tồn kho — Trái tim của Inventory Service)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID lô hàng |
| `lot_code` | `VARCHAR(60)` | `NOT NULL, UNIQUE` | — | Mã lô (VD: `LOT-20261022-001`) |
| `product_id` | `UUID` | `NOT NULL` | — | Tham chiếu logic tới `products.id` (Catalog DB) |
| `supplier_id` | `UUID` | `NULL, FK -> suppliers(id)` | `NULL` | Nhà cung cấp của lô này |
| `purchase_order_id` | `UUID` | `NULL, FK -> purchase_orders(id)` | `NULL` | Phiếu nhập sinh ra lô này |
| `quantity_received` | `NUMERIC(10, 3)` | `NOT NULL, CHECK (> 0)` | — | Khối lượng nhập ban đầu (kg) |
| `quantity_remaining` | `NUMERIC(10, 3)` | `NOT NULL, CHECK (>= 0)` | — | Khối lượng thực tế còn trong kho (bao gồm cả phần đang giữ) |
| `quantity_reserved` | `NUMERIC(10, 3)` | `NOT NULL, CHECK (>= 0)` | `0` | Khối lượng đang bị khóa bởi các đơn chờ thanh toán |
| `unit_cost` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (>= 0)` | — | Giá vốn nhập trên 1 đơn vị tính (VNĐ/kg) |
| `received_date` | `DATE` | `NOT NULL` | `CURRENT_DATE` | Ngày nhập kho |
| `expiry_date` | `DATE` | `NOT NULL, CHECK (>= received_date)` | — | Ngày hết hạn sử dụng |
| `status` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'AVAILABLE'` | `'AVAILABLE'`, `'NEAR_EXPIRY'`, `'EXPIRED'`, `'DEPLETED'`, `'BLOCKED'` |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm tạo lô |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật |

> **Công thức tồn khả dụng của 1 lô:** `available_qty = quantity_remaining - quantity_reserved` (chỉ xét các lô có `status IN ('AVAILABLE', 'NEAR_EXPIRY')` và `expiry_date >= CURRENT_DATE`).

### 3.4. Bảng `reservations` & `reservation_items` (Giữ hàng theo lô khi đặt đơn)
- `reservations`: Lưu phiên giữ hàng cho một `order_id` (`status`: `'ACTIVE'`, `'COMMITTED'`, `'RELEASED'`, `'EXPIRED'`; `expires_at` mặc định +15 phút).
- `reservation_items`: Lưu chính xác số lượng (`quantity`) đã giữ ở từng `lot_id` theo thứ tự **FEFO** (`expiry_date ASC`).
  - Khi thanh toán thành công (`COMMITTED`): giảm `quantity_remaining` và giảm `quantity_reserved` ở từng `lot_id`, đồng thời ghi `stock_movements` loại `'SALE_OUT'`.
  - Khi hủy đơn hoặc quá hạn (`RELEASED` / `EXPIRED`): giảm `quantity_reserved` ở từng `lot_id` để trả lại hàng vào tồn khả dụng.

### 3.5. Bảng `stock_movements` (Sổ cái truy vết mọi biến động kho)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID giao dịch kho |
| `lot_id` | `UUID` | `NOT NULL, FK -> stock_lots(id)` | — | Lô hàng bị tác động |
| `product_id` | `UUID` | `NOT NULL` | — | ID sản phẩm (để truy vấn nhanh không cần join) |
| `movement_type` | `VARCHAR(30)` | `NOT NULL, CHECK` | — | `'IN'`, `'SALE_OUT'`, `'WASTE_EXPIRED'`, `'WASTE_DAMAGED'`, `'ADJUSTMENT'` |
| `quantity_change` | `NUMERIC(10, 3)` | `NOT NULL, CHECK (<> 0)` | — | Số lượng thay đổi (`+` khi nhập, `-` khi xuất/hủy) |
| `unit_cost_snapshot` | `NUMERIC(14, 2)` | `NOT NULL` | — | Giá vốn của lô tại thời điểm biến động (dùng tính giá trị hao hụt/COGS) |
| `reference_type` | `VARCHAR(30)` | `NOT NULL` | — | `'PURCHASE_ORDER'`, `'SALES_ORDER'`, `'EXPIRY_CHECK'`, `'STOCKTAKE'` |
| `reference_id` | `UUID` | `NULL` | `NULL` | ID của đơn hàng hoặc phiếu nhập |
| `idempotency_key` | `VARCHAR(100)` | `UNIQUE, NULL` | `NULL` | Chống ghi trùng biến động kho |
| `reason` | `TEXT` | `NULL` | `NULL` | Ghi chú lý do (VD: Hủy 3kg chuối chín rục quá hạn) |
| `performed_by_user_id` | `UUID` | `NULL` | `NULL` | Nhân viên thực hiện |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm ghi sổ |

---

## 4. Mã lệnh DDL chuẩn PostgreSQL 16

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_number VARCHAR(50) NOT NULL UNIQUE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'RECEIVED', 'CANCELLED')),
    total_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    created_by_user_id UUID,
    note TEXT,
    received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE purchase_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL,
    quantity_ordered NUMERIC(10, 3) NOT NULL CHECK (quantity_ordered > 0),
    quantity_received NUMERIC(10, 3) NOT NULL DEFAULT 0 CHECK (quantity_received >= 0),
    unit_cost NUMERIC(14, 2) NOT NULL CHECK (unit_cost >= 0),
    expiry_date DATE NOT NULL
);

CREATE TABLE stock_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_code VARCHAR(60) NOT NULL UNIQUE,
    product_id UUID NOT NULL,
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

CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL UNIQUE,
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'COMMITTED', 'RELEASED', 'EXPIRED')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reservation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id UUID NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    lot_id UUID NOT NULL REFERENCES stock_lots(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL CHECK (quantity > 0)
);

CREATE TABLE stock_movements (
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

-- Index phục vụ chọn lô FEFO cực nhanh
CREATE INDEX idx_stock_lots_fefo
    ON stock_lots(product_id, expiry_date ASC)
    WHERE status IN ('AVAILABLE', 'NEAR_EXPIRY') AND quantity_remaining > quantity_reserved;

-- Index cảnh báo lô sắp hết hạn
CREATE INDEX idx_stock_lots_expiring
    ON stock_lots(expiry_date ASC)
    WHERE status IN ('AVAILABLE', 'NEAR_EXPIRY') AND quantity_remaining > 0;
```


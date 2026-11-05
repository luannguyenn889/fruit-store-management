# Kế Hoạch Thiết Kế & Triển Khai Database Cho Các Dịch Vụ (SOA)
**Dự án:** Hệ thống Quản lý Cửa hàng Trái cây (FruitStore Management System)  
**Công nghệ:** Python FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · Docker Compose  

---

## PHẦN 1. Phân Tích Đề Xuất Từ Cuộc Trò Chuyện Gốc

Từ nội dung tiếp theo trong link chia sẻ (bàn sâu về **thiết kế Database cho từng Service**, **lưu trữ hình ảnh sản phẩm** và **AI Chatbot Service**), dưới đây là đánh giá kỹ thuật và các điểm cần hoàn thiện để đưa vào triển khai thực tế:

### 1.1. Những điểm hợp lý cần giữ vững
- **Mô hình Database-per-Service trên 1 PostgreSQL Instance:** Tạo 6 database logic riêng biệt (`fruitstore_auth_db`, `fruitstore_catalog_db`, `fruitstore_inventory_db`, `fruitstore_order_db`, `fruitstore_payment_db`, `fruitstore_reporting_db` + `fruitstore_chatbot_db` mở rộng) chạy chung trên một container PostgreSQL với **tài khoản (DB User) tách biệt cho từng service**. Giải pháp này vừa chứng minh chuẩn xác tính độc lập dữ liệu của SOA khi bảo vệ đồ án, vừa nhẹ RAM hơn nhiều so với việc chạy 6 container PostgreSQL.
- **Không dùng Foreign Key xuyên Database:** Các trường như `product_id`, `order_id`, `customer_id`, `user_id` chỉ lưu dưới dạng tham chiếu logic (`UUID` hoặc `BIGINT`). Tính toàn vẹn được kiểm soát qua REST API và cơ chế bù trừ (Saga / Reservation).
- **Lưu trữ hình ảnh ngoài Database:** Không dùng `BYTEA` trong PostgreSQL. Lưu file vật lý vào Docker Volume (`storage/products/*.webp`) hoặc MinIO, còn bảng `product_images` chỉ lưu đường dẫn tương đối (`/media/products/...`).
- **Tách dữ liệu AI Chatbot:** Chatbot không đọc trực tiếp DB của các service khác mà dùng **Function Calling** gọi qua REST API của Catalog, Inventory, Order; DB riêng của Chatbot chỉ lưu hội thoại và log gọi tool.

### 1.2. Các lỗ hổng kỹ thuật trong bản gốc cần bổ sung ngay vào thiết kế DB
| Vấn đề trong bản gốc | Hệ quả nếu giữ nguyên | Giải pháp nâng cấp trong bản kế hoạch này |
|---|---|---|
| Chưa thống nhất kiểu Khóa chính (`SERIAL` vs `UUID`) | Lộ số lượng đơn/sản phẩm qua URL, dễ xung đột ID khi đồng bộ hoặc gộp báo cáo giữa các service | Dùng **`UUID` (v4/v7)** cho tất cả thực thể đi xuyên service (`users.id`, `products.id`, `orders.id`, `stock_lots.id`, `payments.id`) kèm mã hiển thị thân thiện (`order_code`, `lot_code`, `sku`). |
| Bảng `reservations` trong Inventory DB chỉ lưu `product_id` mà không gắn với `lot_id` | Không biết giữ hàng ở lô nào → vi phạm quy tắc **FEFO** (First Expired, First Out) hoặc giữ nhầm lô sắp hỏng | Bổ sung bảng/liên kết `reservation_items` gắn trực tiếp với `lot_id` để giữ đúng lô có hạn sử dụng gần nhất ngay khi tạo đơn. |
| Bảng `stock_lots` thiếu `cost_price` (giá vốn nhập của từng lô) | Trái cây mỗi đợt nhập có giá khác nhau; nếu chỉ lưu ở `purchase_items` sẽ khó tính giá trị hao hụt khi hủy 1 lô hàng hỏng | Thêm `unit_cost NUMERIC(12,2)` trực tiếp vào `stock_lots` và `stock_movements`. |
| Thiếu `idempotency_key` ở Order DB & Inventory DB | Bản gốc mới chỉ nhắc `idempotency_key` ở bảng `payments`, nhưng nếu mạng chập chờn lúc đặt hàng/xuất kho sẽ bị tạo 2 đơn hoặc trừ kho 2 lần | Bổ sung cột `idempotency_key UNIQUE` vào cả `orders`, `reservations`, và `stock_movements`. |
| Chưa có cơ chế chống Race Condition ở tầng DB | Hai khách cùng mua 1 kg xoài cuối cùng sẽ dẫn đến tồn kho âm | Thêm ràng buộc `CHECK (quantity_remaining >= 0)` và `CHECK (quantity_reserved >= 0)` ngay trong PostgreSQL + khóa dòng `SELECT ... FOR UPDATE`. |

---

## PHẦN 2. Kiến Trúc Kết Nối & Phân Quyền PostgreSQL

```mermaid
flowchart TB
    subgraph Services["Tầng Dịch Vụ (FastAPI Services)"]
        S_AUTH["Auth Service"]
        S_CAT["Catalog Service"]
        S_INV["Inventory Service"]
        S_ORD["Order Service"]
        S_PAY["Payment Service"]
        S_REP["Reporting Service"]
        S_BOT["Chatbot Service (Mở rộng)"]
    end

    subgraph PG["PostgreSQL 16 Server (Single Container)"]
        DB_AUTH[("fruitstore_auth_db\n(User: auth_user)")]
        DB_CAT[("fruitstore_catalog_db\n(User: catalog_user)")]
        DB_INV[("fruitstore_inventory_db\n(User: inventory_user)")]
        DB_ORD[("fruitstore_order_db\n(User: order_user)")]
        DB_PAY[("fruitstore_payment_db\n(User: payment_user)")]
        DB_REP[("fruitstore_reporting_db\n(User: reporting_user)")]
        DB_BOT[("fruitstore_chatbot_db\n(User: chatbot_user)")]
    end

    S_AUTH -->|psycopg async| DB_AUTH
    S_CAT -->|psycopg async| DB_CAT
    S_INV -->|psycopg async| DB_INV
    S_ORD -->|psycopg async| DB_ORD
    S_PAY -->|psycopg async| DB_PAY
    S_REP -->|psycopg async| DB_REP
    S_BOT -.->|psycopg async| DB_BOT
```

> [!IMPORTANT]
> **Quy tắc cô lập cứng (Strict Isolation):** Mỗi service kết nối bằng một PostgreSQL Role riêng (`REVOKE CONNECT ON DATABASE ... FROM PUBLIC`). Nếu một thành viên trong nhóm vô tình viết câu lệnh SQL truy vấn chéo sang DB khác, PostgreSQL sẽ từ chối ngay lập tức (`permission denied`).

---

## PHẦN 3. Thiết Kế Chi Tiết Từng Database (Schema, Kiểu Dữ Liệu & Ràng Buộc)

### Quy ước chung cho mọi Database
- **Chuẩn tiền tệ:** `NUMERIC(14, 2)` (VNĐ, không dùng `FLOAT`).
- **Chuẩn khối lượng trái cây:** `NUMERIC(10, 3)` (cho phép bán lẻ tới từng gram, ví dụ `1.250` kg).
- **Chuẩn thời gian:** `TIMESTAMPTZ` (luôn lưu kèm múi giờ UTC, hiển thị `Asia/Ho_Chi_Minh` ở Angular).
- **Audit columns:** Mọi bảng chính đều có `created_at TIMESTAMPTZ DEFAULT NOW()` và `updated_at TIMESTAMPTZ DEFAULT NOW()`.

---

### 3.1. Auth DB (`fruitstore_auth_db`) — Quản lý Tài khoản & Phân quyền
**Service sở hữu:** `auth-service`

```mermaid
erDiagram
    users ||--o{ user_roles : has
    roles ||--o{ user_roles : assigned_to
    users ||--o{ refresh_tokens : owns

    users {
        UUID id PK
        VARCHAR(255) email UK "NOT NULL"
        VARCHAR(20) phone UK
        VARCHAR(255) password_hash "NOT NULL"
        VARCHAR(150) full_name "NOT NULL"
        VARCHAR(20) status "ACTIVE | LOCKED | INACTIVE"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    roles {
        SMALLSERIAL id PK
        VARCHAR(50) code UK "ADMIN | MANAGER | STAFF | WAREHOUSE | CUSTOMER"
        VARCHAR(150) name
        TEXT description
    }
    user_roles {
        UUID user_id PK, FK
        SMALLINT role_id PK, FK
        TIMESTAMPTZ assigned_at
    }
    refresh_tokens {
        UUID id PK
        UUID user_id FK
        VARCHAR(255) token_hash UK "SHA-256 hash"
        BOOLEAN is_revoked "DEFAULT FALSE"
        TIMESTAMPTZ expires_at "NOT NULL"
        TIMESTAMPTZ created_at
    }
```

- **Index bắt buộc:** `idx_users_email`, `idx_refresh_tokens_user_id_active`.
- **Dữ liệu khởi tạo (Seed):** 5 role chuẩn (`ADMIN`, `MANAGER`, `STAFF`, `WAREHOUSE`, `CUSTOMER`) và 1 tài khoản Admin mặc định.

---

### 3.2. Catalog DB (`fruitstore_catalog_db`) — Danh mục, Sản phẩm, Giá & Hình ảnh
**Service sở hữu:** `catalog-service`

```mermaid
erDiagram
    categories ||--o{ products : contains
    products ||--o{ product_images : has
    products ||--o{ price_history : tracks

    categories {
        UUID id PK
        VARCHAR(100) name "NOT NULL"
        VARCHAR(120) slug UK "NOT NULL"
        TEXT description
        BOOLEAN is_active "DEFAULT TRUE"
        TIMESTAMPTZ created_at
    }
    products {
        UUID id PK
        UUID category_id FK
        VARCHAR(50) sku UK "VD: FRT-XOAI-001"
        VARCHAR(200) name "NOT NULL"
        VARCHAR(220) slug UK "NOT NULL"
        VARCHAR(20) unit "kg | hop | trai | gio"
        NUMERIC(14_2) price "CHECK (price >= 0)"
        VARCHAR(100) origin "VD: Hòa Lộc - Tiền Giang, Nhập khẩu Úc"
        INT shelf_life_days "Số ngày bảo quản tiêu chuẩn"
        VARCHAR(20) storage_condition "NORMAL | COLD_2_8C"
        TEXT description
        VARCHAR(20) status "ACTIVE | INACTIVE | OUT_OF_SEASON"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    product_images {
        UUID id PK
        UUID product_id FK
        VARCHAR(500) image_url "VD: /media/products/xoai-cat-hoa-loc.webp"
        BOOLEAN is_primary "DEFAULT FALSE"
        SMALLINT sort_order "DEFAULT 0"
        TIMESTAMPTZ created_at
    }
    price_history {
        UUID id PK
        UUID product_id FK
        NUMERIC(14_2) old_price
        NUMERIC(14_2) new_price
        UUID changed_by_user_id "Logic ref -> Auth DB"
        TIMESTAMPTZ effective_at "DEFAULT NOW()"
    }
```

- **Điểm nhấn đặc thù trái cây:** Thêm cột `shelf_life_days` (số ngày hạn dùng gợi ý khi nhập kho) và `storage_condition` (điều kiện bảo quản: nhiệt độ phòng hay tủ mát 2–8°C) để phục vụ cả quản lý kho lẫn tư vấn của AI Chatbot.
- **Lưu trữ ảnh:** Mỗi sản phẩm chỉ cho phép tối đa 1 ảnh có `is_primary = TRUE` (dùng Unique Partial Index: `CREATE UNIQUE INDEX uq_primary_image ON product_images(product_id) WHERE is_primary = TRUE;`).

---

### 3.3. Inventory DB (`fruitstore_inventory_db`) — Lô hàng (FEFO), Tồn kho, Nhập hàng & Hao hụt
**Service sở hữu:** `inventory-service`

```mermaid
erDiagram
    suppliers ||--o{ purchase_orders : supplies
    purchase_orders ||--o{ purchase_items : includes
    suppliers ||--o{ stock_lots : provides
    purchase_orders ||--o{ stock_lots : generates
    stock_lots ||--o{ stock_movements : logs
    reservations ||--o{ reservation_items : locks
    stock_lots ||--o{ reservation_items : allocated_from

    suppliers {
        UUID id PK
        VARCHAR(50) code UK "NCC-001"
        VARCHAR(200) name "NOT NULL"
        VARCHAR(20) phone
        TEXT address
        BOOLEAN is_active "DEFAULT TRUE"
    }
    purchase_orders {
        UUID id PK
        VARCHAR(50) po_number UK "PO-202610-001"
        UUID supplier_id FK
        VARCHAR(20) status "DRAFT | RECEIVED | CANCELLED"
        NUMERIC(14_2) total_amount "DEFAULT 0"
        UUID created_by_user_id "Logic ref -> Auth DB"
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
    }
    stock_lots {
        UUID id PK
        VARCHAR(60) lot_code UK "LOT-20261022-01"
        UUID product_id "Logic ref -> Catalog DB"
        UUID supplier_id FK
        UUID purchase_order_id FK "NULLable nếu nhập lẻ"
        NUMERIC(10_3) quantity_received "CHECK (> 0)"
        NUMERIC(10_3) quantity_remaining "CHECK (>= 0)"
        NUMERIC(10_3) quantity_reserved "DEFAULT 0, CHECK (>= 0)"
        NUMERIC(14_2) unit_cost "Giá vốn / kg"
        DATE received_date "NOT NULL"
        DATE expiry_date "NOT NULL, CHECK (expiry_date >= received_date)"
        VARCHAR(20) status "AVAILABLE |NEAR_EXPIRY | EXPIRED | DEPLETED"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    reservations {
        UUID id PK
        UUID order_id UK "Logic ref -> Order DB"
        VARCHAR(100) idempotency_key UK
        VARCHAR(20) status "ACTIVE | COMMITTED | RELEASED | EXPIRED"
        TIMESTAMPTZ expires_at "NOW() + 15 minutes"
        TIMESTAMPTZ created_at
    }
    reservation_items {
        UUID id PK
        UUID reservation_id FK
        UUID lot_id FK
        UUID product_id "Logic ref -> Catalog DB"
        NUMERIC(10_3) quantity "CHECK (> 0)"
    }
    stock_movements {
        UUID id PK
        UUID lot_id FK
        VARCHAR(25) movement_type "IN | SALE_OUT | WASTE_EXPIRED | WASTE_DAMAGED | ADJUSTMENT"
        NUMERIC(10_3) quantity_change "+ nhập, - xuất/hủy"
        NUMERIC(14_2) unit_cost_snapshot
        VARCHAR(50) reference_type "ORDER | PO | MANUAL_CHECK"
        UUID reference_id "order_id hoặc po_id"
        VARCHAR(100) idempotency_key UK
        TEXT reason
        UUID performed_by_user_id "Logic ref -> Auth DB"
        TIMESTAMPTZ created_at
    }
```

- **Ràng buộc sống còn trong PostgreSQL:**
  ```sql
  ALTER TABLE stock_lots ADD CONSTRAINT chk_lot_available
  CHECK (quantity_remaining >= quantity_reserved AND quantity_remaining >= 0 AND quantity_reserved >= 0);
  ```
- **Tồn khả dụng để bán của 1 lô:** `available = quantity_remaining - quantity_reserved` (chỉ tính các lô có `status IN ('AVAILABLE', 'NEAR_EXPIRY')` và `expiry_date >= CURRENT_DATE`).
- **Index tối ưu FEFO:** `CREATE INDEX idx_stock_lots_fefo ON stock_lots (product_id, expiry_date ASC) WHERE status IN ('AVAILABLE', 'NEAR_EXPIRY') AND quantity_remaining > quantity_reserved;`

---

### 3.4. Order DB (`fruitstore_order_db`) — Khách hàng, Đơn hàng (POS & Online)
**Service sở hữu:** `order-service`

```mermaid
erDiagram
    customers ||--o{ customer_addresses : has
    customers ||--o{ orders : places
    orders ||--o{ order_items : contains
    orders ||--o{ order_status_history : logs

    customers {
        UUID id PK
        UUID user_id UK "NULLable cho khách vãng lai tại POS"
        VARCHAR(150) full_name "NOT NULL"
        VARCHAR(20) phone UK
        VARCHAR(255) email
        INT loyalty_points "DEFAULT 0"
        TIMESTAMPTZ created_at
    }
    customer_addresses {
        UUID id PK
        UUID customer_id FK
        VARCHAR(150) recipient_name
        VARCHAR(20) recipient_phone
        TEXT address_line "NOT NULL"
        BOOLEAN is_default "DEFAULT FALSE"
    }
    orders {
        UUID id PK
        VARCHAR(40) order_code UK "ORD-20261022-0001"
        UUID customer_id FK "NULLable nếu khách lẻ POS không lưu tên"
        VARCHAR(20) channel "POS | ONLINE"
        VARCHAR(25) status "PENDING_PAYMENT | PAID | PROCESSING | COMPLETED | CANCELLED | EXPIRED"
        NUMERIC(14_2) subtotal "NOT NULL"
        NUMERIC(14_2) discount_amount "DEFAULT 0"
        NUMERIC(14_2) shipping_fee "DEFAULT 0"
        NUMERIC(14_2) total_amount "NOT NULL"
        TEXT shipping_address_snapshot
        VARCHAR(100) idempotency_key UK "Chống bấm đúp đặt hàng"
        UUID created_by_staff_id "Logic ref -> Auth DB (nếu bán tại POS)"
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    order_items {
        UUID id PK
        UUID order_id FK
        UUID product_id "Logic ref -> Catalog DB"
        VARCHAR(50) product_sku_snapshot
        VARCHAR(200) product_name_snapshot "NOT NULL"
        VARCHAR(20) unit_snapshot "kg"
        NUMERIC(10_3) quantity "CHECK (> 0)"
        NUMERIC(14_2) unit_price_snapshot "Giá tại thời điểm mua"
        NUMERIC(14_2) line_total "quantity * unit_price_snapshot"
    }
    order_status_history {
        UUID id PK
        UUID order_id FK
        VARCHAR(25) old_status
        VARCHAR(25) new_status "NOT NULL"
        TEXT note
        UUID changed_by_user_id
        TIMESTAMPTZ changed_at "DEFAULT NOW()"
    }
```

- **Snapshot dữ liệu:** `order_items` bắt buộc lưu `product_name_snapshot`, `product_sku_snapshot`, `unit_price_snapshot` để khi Catalog đổi tên/giá trái cây thì hóa đơn lịch sử không bao giờ bị sai lệch.

---

### 3.5. Payment DB (`fruitstore_payment_db`) — Giao dịch Thanh toán & Hoàn tiền
**Service sở hữu:** `payment-service`

```mermaid
erDiagram
    payments ||--o{ refunds : has
    payments ||--o{ payment_events : logs

    payments {
        UUID id PK
        UUID order_id "Logic ref -> Order DB"
        VARCHAR(40) order_code
        NUMERIC(14_2) amount "CHECK (> 0)"
        VARCHAR(30) method "CASH | BANK_TRANSFER_QR | VNPAY_MOCK | MOMO_MOCK"
        VARCHAR(20) status "PENDING | SUCCEEDED | FAILED | REFUNDED"
        VARCHAR(100) idempotency_key UK "NOT NULL"
        VARCHAR(150) provider_transaction_id
        TIMESTAMPTZ paid_at
        TIMESTAMPTZ created_at
    }
    refunds {
        UUID id PK
        UUID payment_id FK
        NUMERIC(14_2) amount "CHECK (> 0)"
        VARCHAR(20) status "PENDING | SUCCEEDED | FAILED"
        TEXT reason
        TIMESTAMPTZ created_at
    }
    payment_events {
        UUID id PK
        UUID payment_id FK
        VARCHAR(50) event_type "INITIATED | WEBHOOK_RECEIVED | CONFIRMED | FAILED"
        JSONB payload "Dữ liệu callback mô phỏng"
        TIMESTAMPTZ created_at "DEFAULT NOW()"
    }
```

---

### 3.6. Reporting DB (`fruitstore_reporting_db`) — Read Model Thống kê & Báo cáo
**Service sở hữu:** `reporting-service`

| Bảng | Khóa chính & Unique | Các cột chính | Mục đích |
|---|---|---|---|
| `daily_sales_summary` | `report_date DATE PK` | `total_orders INT`, `pos_orders INT`, `online_orders INT`, `gross_revenue NUMERIC(14,2)`, `discount_total NUMERIC(14,2)`, `net_revenue NUMERIC(14,2)`, `updated_at TIMESTAMPTZ` | Biểu đồ doanh thu theo ngày/tháng trên Admin Dashboard |
| `product_sales_summary` | `(report_date, product_id) PK` | `product_name VARCHAR(200)`, `unit VARCHAR(20)`, `quantity_sold NUMERIC(10,3)`, `revenue NUMERIC(14,2)`, `estimated_cogs NUMERIC(14,2)` | Top trái cây bán chạy & lợi nhuận gộp ước tính |
| `wastage_summary` | `(report_date, product_id) PK` | `product_name VARCHAR(200)`, `expired_qty NUMERIC(10,3)`, `damaged_qty NUMERIC(10,3)`, `total_loss_cost NUMERIC(14,2)` | Báo cáo tỷ lệ hao hụt/hư hỏng trái cây theo ngày |
| `sync_checkpoints` | `source_service VARCHAR(50) PK` | `last_synced_at TIMESTAMPTZ`, `status VARCHAR(20)` | Theo dõi tiến độ đồng bộ dữ liệu từ Order/Inventory sang Reporting |

---

### 3.7. Chatbot DB (`fruitstore_chatbot_db`) — Mở rộng ở Sprint 5
**Service sở hữu:** `chatbot-service`

| Bảng | Các cột chính | Ghi chú |
|---|---|---|
| `conversations` | `id UUID PK`, `user_id UUID NULL`, `session_id VARCHAR(100)`, `title VARCHAR(200)`, `created_at TIMESTAMPTZ` | Hỗ trợ cả khách vãng lai (`session_id`) và khách đã đăng nhập (`user_id`) |
| `messages` | `id UUID PK`, `conversation_id UUID FK`, `role VARCHAR(20)` (`user`/`assistant`/`tool`), `content TEXT`, `created_at TIMESTAMPTZ` | Lưu lịch sử chat |
| `tool_execution_logs` | `id UUID PK`, `message_id UUID FK`, `tool_name VARCHAR(100)`, `arguments JSONB`, `response_summary JSONB`, `duration_ms INT`, `status VARCHAR(20)` | Minh chứng rõ ràng cho hội đồng chấm đồ án thấy AI đã gọi `search_products()`, `check_stock()` qua SOA như thế nào |
| `chat_feedback` | `id UUID PK`, `message_id UUID FK`, `rating SMALLINT` (`1` hoặc `-1`), `comment TEXT` | Đánh giá chất lượng câu trả lời |

---

## PHẦN 4. Kế Hoạch Tự Động Hóa Tạo Database Trong Dự Án

Để cả nhóm chỉ cần gõ **1 lệnh `docker compose up -d`** là có sẵn toàn bộ 6 (hoặc 7) database cùng tài khoản phân quyền riêng biệt, cấu trúc thư mục và script sẽ được tổ chức như sau:

### 4.1. Cấu trúc thư mục Database & Migration trong Monorepo
```text
d:\fruit-store-management\
├── infrastructure/
│   └── postgres/
│       └── init/
│           └── 01-init-multiple-dbs.sql    # Tự động tạo 6 DB + 6 User riêng khi khởi chạy container lần đầu
├── backend/
│   ├── shared/                             # (Tùy chọn) Các tiện ích chuẩn hóa lỗi, logging, JWT verify
│   └── services/
│       ├── auth-service/
│       │   ├── alembic.ini
│       │   ├── alembic/
│       │   │   ├── env.py
│       │   │   └── versions/
│       │   └── app/db/{session.py, base.py, seed.py}
│       ├── catalog-service/
│       │   ├── alembic.ini
│       │   └── ...
│       ├── inventory-service/
│       ├── order-service/
│       ├── payment-service/
│       └── reporting-service/
├── storage/
│   └── products/                           # Docker Volume lưu ảnh trái cây (.webp, .jpg)
└── docker-compose.yml
```

### 4.2. Script khởi tạo PostgreSQL (`01-init-multiple-dbs.sql`)
Khi container `postgres:16-alpine` chạy lần đầu, file trong `/docker-entrypoint-initdb.d/01-init-multiple-dbs.sql` sẽ thực thi:
1. Tạo 6 Role: `auth_user`, `catalog_user`, `inventory_user`, `order_user`, `payment_user`, `reporting_user` (và `chatbot_user`).
2. Tạo 6 Database: `fruitstore_auth_db`, `fruitstore_catalog_db`, `fruitstore_inventory_db`, `fruitstore_order_db`, `fruitstore_payment_db`, `fruitstore_reporting_db`.
3. Thu hồi quyền mặc định (`REVOKE ALL ON DATABASE ... FROM PUBLIC`) và chỉ cấp quyền `ALL PRIVILEGES` trên từng DB cho đúng user sở hữu nó.

### 4.3. Quản lý Migration độc lập bằng Alembic + SQLAlchemy 2.0 (Async)
Mỗi service FastAPI có một bộ `alembic/` hoàn toàn độc lập:
- Sử dụng driver bất đồng bộ **`psycopg` (v3)** hoặc **`asyncpg`**:
  ```env
  DATABASE_URL=postgresql+psycopg://inventory_user:inv_secret@postgres:5432/fruitstore_inventory_db
  ```
- Khi container của từng service khởi động trong Docker Compose, entrypoint sẽ chạy:
  ```bash
  alembic upgrade head && python -m app.db.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

---

## PHẦN 5. Lộ Trình Thực Hiện Tạo Database Theo Từng Sprint

| Giai đoạn | Hạng mục công việc Database | Kết quả kiểm tra (Verification) |
|---|---|---|
| **Bước 1 (Sprint 1 - Tuần 1)** | • Viết `docker-compose.yml` cho PostgreSQL 16 + script `01-init-multiple-dbs.sql`.<br>• Tạo migration cho **Auth DB** (`users`, `roles`, `user_roles`, `refresh_tokens`) + seed 5 roles.<br>• Tạo migration cho **Catalog DB** (`categories`, `products`, `product_images`, `price_history`) + seed 10 loại trái cây mẫu kèm ảnh trong `storage/products/`. | • Kết nối thử bằng `auth_user` sang `fruitstore_catalog_db` → báo lỗi `permission denied` (đạt chuẩn cô lập SOA).<br>• API `GET /api/v1/products` trả về danh sách trái cây + link ảnh. |
| **Bước 2 (Sprint 2 - Tuần 3)** | • Tạo migration cho **Inventory DB** (`suppliers`, `purchase_orders`, `purchase_items`, `stock_lots`, `reservations`, `reservation_items`, `stock_movements`).<br>• Viết hàm giao dịch (Transaction) chọn lô theo **FEFO** có `SELECT ... FOR UPDATE`.<br>• Tạo seed 3 nhà cung cấp + 15 lô trái cây (có lô còn hạn dài, lô sắp hết hạn trong 2 ngày, lô đã hết hạn). | • Test nhập kho tạo lô mới.<br>• Test truy vấn `/inventory/expiring?days=3` trả về đúng lô chuối/xoài sắp hết hạn.<br>• Test cố tình trừ kho âm → PostgreSQL chặn bằng `CHECK constraint`. |
| **Bước 3 (Sprint 3 - Tuần 5)** | • Tạo migration cho **Order DB** (`customers`, `customer_addresses`, `orders`, `order_items`, `order_status_history`).<br>• Tạo migration cho **Payment DB** (`payments`, `refunds`, `payment_events`).<br>• Viết luồng phối hợp Đặt hàng → Giữ lô (`reservations`) → Thanh toán → Xuất kho (`SALE_OUT`) / Giải phóng lô (`RELEASED`). | • Chạy bài test 2 request mua cùng lúc số kg xoài cuối cùng → chỉ 1 đơn thành công.<br>• Gửi lặp cùng `Idempotency-Key` → không tạo 2 đơn hay trừ kho 2 lần. |
| **Bước 4 (Sprint 4 - Tuần 7)** | • Tạo migration cho **Reporting DB** (`daily_sales_summary`, `product_sales_summary`, `wastage_summary`, `sync_checkpoints`).<br>• Viết job/endpoint tổng hợp dữ liệu từ Order API & Inventory API về Reporting DB. | • Tắt thử `reporting-service` → POS và đặt hàng vẫn chạy bình thường.<br>• Bật lại → Dashboard hiển thị đúng doanh thu và lượng hao hụt. |
| **Bước 5 (Mở rộng - Sprint 5)** | • Tạo migration cho **Chatbot DB** (`conversations`, `messages`, `tool_execution_logs`, `chat_feedback`). | • Hỏi chatbot "Còn xoài cát Hòa Lộc không?" → bảng `tool_execution_logs` ghi nhận lệnh gọi sang Catalog & Inventory API. |

---

## PHẦN 6. Bước Tiếp Theo Đề Xuất

Tôi sẽ lưu bản kế hoạch thiết kế Database này trực tiếp vào thư mục dự án của bạn tại `d:\fruit-store-management\ke_hoach_database_soa.md`.  
Nếu bạn muốn bắt tay vào triển khai ngay, tôi có thể tạo sẵn cho bạn bộ `docker-compose.yml` và file `infrastructure/postgres/init/01-init-multiple-dbs.sql` để khởi chạy toàn bộ các database này.

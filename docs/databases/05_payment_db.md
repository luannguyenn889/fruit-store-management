# 05. Cơ Sở Dữ Liệu Dịch Vụ Thanh Toán — Payment DB (`fruitstore_payment_db`)

## 1. Thông tin chung
- **Dịch vụ sở hữu:** `payment-service`
- **Tên Database:** `fruitstore_payment_db`
- **DB User:** `payment_user`
- **Chuỗi kết nối (FastAPI SQLAlchemy Async):**
  ```env
  DATABASE_URL=postgresql+psycopg://payment_user:payment_pass@postgres:5432/fruitstore_payment_db
  ```
- **Trách nhiệm dữ liệu:**
  - Quản lý các giao dịch thanh toán (`payments`) cho từng `order_id` (tiền mặt tại POS, chuyển khoản QR, ví điện tử mô phỏng).
  - Đảm bảo **Idempotency** tuyệt đối khi nhận callback/webhook thanh toán để không bao giờ xác nhận thanh toán lặp hoặc trừ kho 2 lần.
  - Quản lý lịch sử hoàn tiền (`refunds`) và nhật ký sự kiện thanh toán (`payment_events`).

---

## 2. Sơ đồ quan hệ thực thể (ERD)

```mermaid
erDiagram
    payments ||--o{ refunds : "hoàn tiền"
    payments ||--o{ payment_events : "ghi sự kiện"

    payments {
        UUID id PK
        UUID order_id "Logic ref -> Order DB"
        VARCHAR(40) order_code
        NUMERIC(14_2) amount
        VARCHAR(30) method "CASH | BANK_QR | VNPAY_MOCK | MOMO_MOCK"
        VARCHAR(20) status "PENDING | SUCCEEDED | FAILED | REFUNDED"
        VARCHAR(100) idempotency_key UK
        VARCHAR(150) provider_transaction_id UK
        TIMESTAMPTZ paid_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    refunds {
        UUID id PK
        UUID payment_id FK
        NUMERIC(14_2) amount
        VARCHAR(20) status "PENDING | SUCCEEDED | FAILED"
        VARCHAR(100) idempotency_key UK
        TEXT reason
        UUID requested_by_user_id "Logic ref -> Auth DB"
        TIMESTAMPTZ refunded_at
        TIMESTAMPTZ created_at
    }
    payment_events {
        UUID id PK
        UUID payment_id FK
        VARCHAR(50) event_type "CREATED | CALLBACK_RECEIVED | SUCCEEDED | FAILED"
        VARCHAR(150) provider_event_id UK
        JSONB raw_payload
        TIMESTAMPTZ created_at
    }
```

---

## 3. Đặc tả chi tiết các bảng (Data Dictionary)

### 3.1. Bảng `payments` (Giao dịch thanh toán)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID giao dịch thanh toán |
| `order_id` | `UUID` | `NOT NULL` | — | Tham chiếu logic tới `orders.id` (Order DB) |
| `order_code` | `VARCHAR(40)` | `NOT NULL` | — | Mã đơn hàng (để đối soát nội dung chuyển khoản) |
| `amount` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (> 0)` | — | Số tiền thanh toán (VNĐ) |
| `method` | `VARCHAR(30)` | `NOT NULL, CHECK` | — | `'CASH'`, `'BANK_QR'`, `'VNPAY_MOCK'`, `'MOMO_MOCK'` |
| `status` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'PENDING'` | `'PENDING'`, `'SUCCEEDED'`, `'FAILED'`, `'REFUNDED'` |
| `idempotency_key` | `VARCHAR(100)` | `NOT NULL, UNIQUE` | — | Khóa chống tạo giao dịch trùng |
| `provider_transaction_id` | `VARCHAR(150)` | `UNIQUE, NULL` | `NULL` | Mã giao dịch từ cổng thanh toán/ngân hàng |
| `paid_at` | `TIMESTAMPTZ` | `NULL` | `NULL` | Thời điểm hoàn tất thu tiền |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm khởi tạo |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật |

### 3.2. Bảng `refunds` (Giao dịch hoàn tiền)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID hoàn tiền |
| `payment_id` | `UUID` | `NOT NULL, FK -> payments(id) ON DELETE RESTRICT` | — | Giao dịch gốc |
| `amount` | `NUMERIC(14, 2)` | `NOT NULL, CHECK (> 0)` | — | Số tiền hoàn |
| `status` | `VARCHAR(20)` | `NOT NULL, CHECK` | `'PENDING'` | `'PENDING'`, `'SUCCEEDED'`, `'FAILED'` |
| `idempotency_key` | `VARCHAR(100)` | `NOT NULL, UNIQUE` | — | Chống hoàn tiền lặp |
| `reason` | `TEXT` | `NOT NULL` | — | Lý do hoàn tiền |
| `requested_by_user_id` | `UUID` | `NULL` | `NULL` | Nhân viên/Quản lý thực hiện |
| `refunded_at` | `TIMESTAMPTZ` | `NULL` | `NULL` | Thời điểm hoàn thành công |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm tạo yêu cầu |

### 3.3. Bảng `payment_events` (Nhật ký sự kiện & Callback)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY` | `gen_random_uuid()` | ID sự kiện |
| `payment_id` | `UUID` | `NOT NULL, FK -> payments(id) ON DELETE CASCADE` | — | Giao dịch liên quan |
| `event_type` | `VARCHAR(50)` | `NOT NULL` | — | `'CREATED'`, `'CALLBACK_RECEIVED'`, `'SUCCEEDED'`, `'FAILED'` |
| `provider_event_id` | `VARCHAR(150)` | `UNIQUE, NULL` | `NULL` | Chống xử lý lặp cùng 1 webhook từ cổng thanh toán |
| `raw_payload` | `JSONB` | `NULL` | `NULL` | Dữ liệu JSON nhận được |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm ghi nhận |

---

## 4. Mã lệnh DDL chuẩn PostgreSQL 16

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
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

-- Đảm bảo 1 đơn hàng tại 1 thời điểm chỉ có tối đa 1 giao dịch SUCCEEDED
CREATE UNIQUE INDEX uq_payments_order_succeeded
    ON payments(order_id) WHERE status = 'SUCCEEDED';

CREATE TABLE refunds (
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

CREATE TABLE payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    provider_event_id VARCHAR(150) UNIQUE,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status_created ON payments(status, created_at DESC);
```


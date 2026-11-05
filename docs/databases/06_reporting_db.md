# 06. Cơ Sở Dữ Liệu Dịch Vụ Báo Cáo — Reporting DB (`fruitstore_reporting_db`)

## 1. Thông tin chung
- **Dịch vụ sở hữu:** `reporting-service`
- **Tên Database:** `fruitstore_reporting_db`
- **DB User:** `reporting_user`
- **Chuỗi kết nối (FastAPI SQLAlchemy Async):**
  ```env
  DATABASE_URL=postgresql+psycopg://reporting_user:reporting_pass@postgres:5432/fruitstore_reporting_db
  ```
- **Trách nhiệm dữ liệu:**
  - Lưu trữ các bảng tổng hợp (**Read Model / Projections**) phục vụ biểu đồ doanh thu, sản phẩm bán chạy, tồn kho và tỷ lệ hao hụt trái cây trên Admin Dashboard.
  - **Không truy vấn trực tiếp** vào Order DB hay Inventory DB; dữ liệu được đồng bộ định kỳ hoặc cập nhật qua API/Webhook nội bộ từ các dịch vụ nghiệp vụ.
  - Nếu `reporting-service` tạm dừng để bảo trì, các luồng bán hàng POS và đặt hàng Online vẫn hoạt động bình thường.

---

## 2. Sơ đồ cấu trúc bảng (ERD)

```mermaid
erDiagram
    daily_sales_summary {
        DATE report_date PK
        INT total_orders
        INT pos_orders
        INT online_orders
        INT cancelled_orders
        NUMERIC(14_2) gross_revenue
        NUMERIC(14_2) discount_total
        NUMERIC(14_2) net_revenue
        TIMESTAMPTZ updated_at
    }
    product_sales_summary {
        DATE report_date PK
        UUID product_id PK
        VARCHAR(50) product_sku
        VARCHAR(200) product_name
        VARCHAR(20) unit
        NUMERIC(10_3) quantity_sold
        NUMERIC(14_2) revenue
        NUMERIC(14_2) estimated_cogs
        TIMESTAMPTZ updated_at
    }
    wastage_summary {
        DATE report_date PK
        UUID product_id PK
        VARCHAR(200) product_name
        VARCHAR(20) unit
        NUMERIC(10_3) expired_quantity
        NUMERIC(10_3) damaged_quantity
        NUMERIC(14_2) total_loss_cost
        TIMESTAMPTZ updated_at
    }
    inventory_snapshots {
        DATE snapshot_date PK
        UUID product_id PK
        VARCHAR(200) product_name
        NUMERIC(10_3) total_remaining
        NUMERIC(10_3) total_reserved
        NUMERIC(10_3) expiring_soon_qty
        NUMERIC(14_2) inventory_value
    }
    sync_checkpoints {
        VARCHAR(50) source_service PK
        TIMESTAMPTZ last_synced_at
        VARCHAR(20) status
        TEXT last_error
    }
```

---

## 3. Đặc tả chi tiết các bảng (Data Dictionary)

### 3.1. Bảng `daily_sales_summary` (Tổng hợp doanh thu theo ngày)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `report_date` | `DATE` | `PRIMARY KEY` | — | Ngày báo cáo |
| `total_orders` | `INT` | `NOT NULL` | `0` | Tổng số đơn hoàn tất trong ngày |
| `pos_orders` | `INT` | `NOT NULL` | `0` | Số đơn bán tại quầy POS |
| `online_orders` | `INT` | `NOT NULL` | `0` | Số đơn đặt trực tuyến |
| `cancelled_orders` | `INT` | `NOT NULL` | `0` | Số đơn bị hủy |
| `gross_revenue` | `NUMERIC(14, 2)` | `NOT NULL` | `0` | Tổng doanh thu trước giảm giá |
| `discount_total` | `NUMERIC(14, 2)` | `NOT NULL` | `0` | Tổng chiết khấu |
| `net_revenue` | `NUMERIC(14, 2)` | `NOT NULL` | `0` | Doanh thu thuần thực thu |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Lần tổng hợp gần nhất |

### 3.2. Bảng `product_sales_summary` (Thống kê sản phẩm bán chạy)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `report_date` | `DATE` | `PK (cùng product_id)` | — | Ngày bán |
| `product_id` | `UUID` | `PK (cùng report_date)` | — | ID sản phẩm |
| `product_sku` | `VARCHAR(50)` | `NOT NULL` | — | Mã SKU |
| `product_name` | `VARCHAR(200)` | `NOT NULL` | — | Tên trái cây |
| `unit` | `VARCHAR(20)` | `NOT NULL` | `'kg'` | Đơn vị tính |
| `quantity_sold` | `NUMERIC(10, 3)` | `NOT NULL` | `0` | Tổng khối lượng đã bán |
| `revenue` | `NUMERIC(14, 2)` | `NOT NULL` | `0` | Doanh thu từ sản phẩm này |
| `estimated_cogs` | `NUMERIC(14, 2)` | `NOT NULL` | `0` | Giá vốn hàng bán (tính từ các lô xuất FEFO) |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật |

### 3.3. Bảng `wastage_summary` (Báo cáo hao hụt & hủy trái cây hỏng/hết hạn)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mặc định | Mô tả |
|---|---|---|---|---|
| `report_date` | `DATE` | `PK (cùng product_id)` | — | Ngày ghi nhận hao hụt |
| `product_id` | `UUID` | `PK (cùng report_date)` | — | ID sản phẩm |
| `product_name` | `VARCHAR(200)` | `NOT NULL` | — | Tên trái cây |
| `unit` | `VARCHAR(20)` | `NOT NULL` | `'kg'` | Đơn vị tính |
| `expired_quantity` | `NUMERIC(10, 3)` | `NOT NULL` | `0` | Khối lượng hủy do quá hạn sử dụng (`WASTE_EXPIRED`) |
| `damaged_quantity` | `NUMERIC(10, 3)` | `NOT NULL` | `0` | Khối lượng hủy do dập hỏng (`WASTE_DAMAGED`) |
| `total_loss_cost` | `NUMERIC(14, 2)` | `NOT NULL` | `0` | Tổng giá trị vốn bị thiệt hại (VNĐ) |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | `NOW()` | Thời điểm cập nhật |

---

## 4. Mã lệnh DDL chuẩn PostgreSQL 16

```sql
CREATE TABLE daily_sales_summary (
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

CREATE TABLE product_sales_summary (
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

CREATE TABLE wastage_summary (
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

CREATE TABLE inventory_snapshots (
    snapshot_date DATE NOT NULL,
    product_id UUID NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    total_remaining NUMERIC(10, 3) NOT NULL DEFAULT 0,
    total_reserved NUMERIC(10, 3) NOT NULL DEFAULT 0,
    expiring_soon_qty NUMERIC(10, 3) NOT NULL DEFAULT 0,
    inventory_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_date, product_id)
);

CREATE TABLE sync_checkpoints (
    source_service VARCHAR(50) PRIMARY KEY,
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'IDLE',
    last_error TEXT
);

CREATE INDEX idx_product_sales_date_rev ON product_sales_summary(report_date, revenue DESC);
```


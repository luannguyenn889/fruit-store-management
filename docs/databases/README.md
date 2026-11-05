# Tổng Quan Hệ Thống Cơ Sở Dữ Liệu Theo Dịch Vụ (SOA)

Hệ thống **FruitStore Management System** áp dụng mô hình **Database-per-Service** trên nền tảng **PostgreSQL 16**. Mỗi dịch vụ sở hữu một cơ sở dữ liệu độc lập, tài khoản kết nối riêng và quản lý migration riêng bằng **Alembic**.

## Danh sách file mã nguồn SQL Schema (Thực thi trực tiếp)

Tất cả các file script `.sql` đã được tách riêng để bạn có thể mở trong **pgAdmin 4** hoặc **psql** và thực thi trực tiếp:

* **[00_init_all_databases.sql](./00_init_all_databases.sql)**: Lệnh tạo 7 cơ sở dữ liệu độc lập.
* **[01_auth_schema.sql](./01_auth_schema.sql)**: Bảng `roles`, `users`, `user_roles`, `refresh_tokens`, indexes và seed roles.
* **[02_catalog_schema.sql](./02_catalog_schema.sql)**: Bảng `categories`, `products`, `product_images`, `price_history`, indexes tìm kiếm.
* **[03_inventory_schema.sql](./03_inventory_schema.sql)**: Bảng `suppliers`, `purchase_orders`, `purchase_items`, `stock_lots`, `reservations`, `reservation_items`, `stock_movements`, index FEFO.
* **[04_order_schema.sql](./04_order_schema.sql)**: Bảng `customers`, `customer_addresses`, `orders`, `order_items`, `order_status_history`.
* **[05_payment_schema.sql](./05_payment_schema.sql)**: Bảng `payments`, `refunds`, `payment_events`.
* **[06_reporting_schema.sql](./06_reporting_schema.sql)**: Bảng `daily_sales_summary`, `product_sales_summary`, `wastage_summary`, `inventory_snapshots`, `sync_checkpoints`.
* **[07_chatbot_schema.sql](./07_chatbot_schema.sql)**: Bảng `conversations`, `messages`, `tool_execution_logs`, `chat_feedback`.

## Danh sách tài liệu CSDL chi tiết theo từng dịch vụ

1. **[01_auth_db.md](./01_auth_db.md) — Auth Service (`fruitstore_auth_db`)**
   - Quản lý người dùng, phân quyền (RBAC) và phiên đăng nhập (Refresh Token).
   - Các bảng: `users`, `roles`, `user_roles`, `refresh_tokens`.
2. **[02_catalog_db.md](./02_catalog_db.md) — Catalog Service (`fruitstore_catalog_db`)**
   - Quản lý danh mục trái cây, thông tin sản phẩm, đơn vị tính, điều kiện bảo quản, hình ảnh và lịch sử giá.
   - Các bảng: `categories`, `products`, `product_images`, `price_history`.
3. **[03_inventory_db.md](./03_inventory_db.md) — Inventory Service (`fruitstore_inventory_db`)**
   - Quản lý nhà cung cấp, phiếu nhập kho, lô trái cây theo hạn sử dụng (FEFO), giữ hàng (Reservation) và lịch sử biến động/hao hụt.
   - Các bảng: `suppliers`, `purchase_orders`, `purchase_items`, `stock_lots`, `reservations`, `reservation_items`, `stock_movements`.
4. **[04_order_db.md](./04_order_db.md) — Order Service (`fruitstore_order_db`)**
   - Quản lý hồ sơ khách hàng, địa chỉ giao hàng, đơn hàng (POS & Online), chi tiết đơn (snapshot giá/tên) và lịch sử trạng thái.
   - Các bảng: `customers`, `customer_addresses`, `orders`, `order_items`, `order_status_history`.
5. **[05_payment_db.md](./05_payment_db.md) — Payment Service (`fruitstore_payment_db`)**
   - Quản lý giao dịch thanh toán (tiền mặt, QR, ví điện tử mô phỏng), hoàn tiền và sự kiện webhook/callback.
   - Các bảng: `payments`, `refunds`, `payment_events`.
6. **[06_reporting_db.md](./06_reporting_db.md) — Reporting Service (`fruitstore_reporting_db`)**
   - Lưu trữ mô hình đọc (Read Model) tổng hợp doanh thu, sản phẩm bán chạy, tồn kho và hao hụt trái cây.
   - Các bảng: `daily_sales_summary`, `product_sales_summary`, `inventory_summary`, `wastage_summary`, `sync_checkpoints`.
7. **[07_chatbot_db.md](./07_chatbot_db.md) — AI Chatbot Service (`fruitstore_chatbot_db` - Mở rộng)**
   - Lưu trữ lịch sử hội thoại tư vấn khách hàng, log gọi công cụ (Function Calling) tới các service khác và đánh giá phản hồi.
   - Các bảng: `conversations`, `messages`, `tool_execution_logs`, `chat_feedback`.

---

## Bảng tổng hợp kết nối & phân quyền PostgreSQL

| STT | Dịch vụ (FastAPI) | Tên Database | DB User sở hữu | Port nội bộ Service |
|---|---|---|---|---|
| 1 | `auth-service` | `fruitstore_auth_db` | `auth_user` | `8001` |
| 2 | `catalog-service` | `fruitstore_catalog_db` | `catalog_user` | `8002` |
| 3 | `inventory-service` | `fruitstore_inventory_db` | `inventory_user` | `8003` |
| 4 | `order-service` | `fruitstore_order_db` | `order_user` | `8004` |
| 5 | `payment-service` | `fruitstore_payment_db` | `payment_user` | `8005` |
| 6 | `reporting-service` | `fruitstore_reporting_db` | `reporting_user` | `8006` |
| 7 | `chatbot-service` | `fruitstore_chatbot_db` | `chatbot_user` | `8007` |

## Quy ước kiểu dữ liệu chuẩn toàn hệ thống

- **Khóa chính (Primary Key):** `UUID` (sinh tự động bằng `gen_random_uuid()` của PostgreSQL 16).
- **Tham chiếu liên dịch vụ (Cross-service Reference):** Lưu bằng `UUID` (ví dụ `product_id`, `order_id`, `user_id`), **tuyệt đối không tạo khóa ngoại (FOREIGN KEY) xuyên qua database khác**.
- **Tiền tệ (VNĐ):** `NUMERIC(14, 2)` — không dùng `FLOAT`/`REAL` để tránh sai số làm tròn.
- **Khối lượng trái cây (kg):** `NUMERIC(10, 3)` — hỗ trợ cân lẻ đến từng gram (ví dụ `0.250` kg, `2.500` kg).
- **Thời gian:** `TIMESTAMPTZ` (UTC).


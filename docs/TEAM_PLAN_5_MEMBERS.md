# Kế Hoạch Triển Khai & Phân Chia Nhiệm Vụ Cho 5 Thành Viên — FruitStore SOA (Theo Cách B)

> **Hiện trạng đã hoàn thành (Tuần 1):**
> - **API Gateway (`:8000`)**, **Auth Service (`:8001`)**, **Catalog Service (`:8002`)** đã chạy ổn định, có Alembic migration riêng, seed data và bộ test E2E.
> - **Frontend Angular (`:4200`)** đã có: Đăng nhập/Đăng ký, Dashboard tổng quan, và Quản lý Danh mục & Sản phẩm (`/catalog`).
>
> **Chiến lược Cách B:** Cả **5 thành viên tập trung làm dứt điểm `Inventory Service (:8003)` + Giao diện Kho FEFO & Nhập hàng NCC** trong Sprint 1 để có hệ thống chạy thật ngay, sau đó mới chuyển sang `Order Service` & `Payment Service` ở Sprint 2.
> Mọi quy tắc code, nhánh Git và commit tuân thủ [`CODING_CONVENTION.md`](../CODING_CONVENTION.md).

---

## 1. Sprint 1 (Hiện Tại): Hoàn Thành Trọn Vẹn `Inventory Service (:8003)` & UI Kho

### Thứ tự khởi động (Chống Xung Đột File)
- **Ngày 1:** **Thành viên 1** dựng khung `backend/services/inventory-service`, chạy Alembic migration `0001_init_inventory`, mở route `/api/v1/inventory/*` trên Gateway và merge vào nhánh `develop`.
- **Từ Ngày 2 trở đi:** Thành viên 2, 3, 4, 5 cùng tách nhánh `feature/*` từ `develop` để làm song song 4 phần **không trùng file**.

### Phân Công Chi Tiết 5 Thành Viên (Sprint 1)

| Thành viên | Nhiệm vụ chính | File / Thư mục sở hữu | Nhánh Git & Commit mẫu |
|---|---|---|---|
| **Thành viên 1**<br/>*(Tech Lead & Hạ tầng)* | - Khởi tạo khung `inventory-service` (`:8003`, `fruitstore_inventory_db`).<br/>- Viết ORM models + Alembic `0001_init_inventory.py` từ [`03_inventory_schema.sql`](./databases/03_inventory_schema.sql).<br/>- Mở route proxy `/api/v1/inventory/*` trong Gateway (`:8000`).<br/>- Cập nhật `run_backend.bat` & review PR merge vào `develop`. | `backend/services/inventory-service/app/{main.py,core/,db/,models/}`<br/>`backend/services/inventory-service/alembic/`<br/>`backend/gateway/app/main.py`<br/>`run_backend.bat` | Nhánh: `feature/inventory-setup`<br/>Commit: `feat(inventory): khởi tạo khung service, alembic migration và gateway route` |
| **Thành viên 2**<br/>*(Nhà cung cấp & Nhập hàng)* | - Backend CRUD **Nhà cung cấp (`suppliers`)**.<br/>- Backend **Phiếu nhập kho (`purchase_orders`, `purchase_items`)**.<br/>- Xác nhận nhập kho (`POST /purchase-orders/{id}/receive`): gọi `catalog-service` kiểm tra `product_id`, tự động sinh lô `stock_lots` và ghi biến động `IMPORT` vào `stock_movements`. | `app/schemas/procurement.py`<br/>`app/repositories/procurement_repository.py`<br/>`app/services/procurement_service.py`<br/>`app/api/v1/procurement.py` | Nhánh: `feature/inventory-procurement`<br/>Commit: `feat(inventory): thêm API nhà cung cấp và xác nhận nhập kho sinh lô` |
| **Thành viên 3**<br/>*(Lô hàng FEFO & Hao hụt)* | - Backend xem tồn kho theo sản phẩm & từng lô (`stock_lots`), lọc lô **sắp hết hạn / hết hạn**.<br/>- Thuật toán **FEFO (`reservations`, `reservation_items`)**: giữ/trừ/nhả kho bằng `SELECT ... FOR UPDATE`, chọn lô còn hạn có `expiry_date` gần nhất.<br/>- API **Hao hụt / Hủy hàng hỏng / Kiểm kê** (`stock_movements`, bắt buộc lý do). | `app/schemas/lot.py`<br/>`app/repositories/lot_repository.py`<br/>`app/services/lot_service.py`<br/>`app/api/v1/lots.py` | Nhánh: `feature/inventory-fefo-wastage`<br/>Commit: `feat(inventory): cài đặt thuật toán giữ hàng FEFO và ghi nhận hao hụt` |
| **Thành viên 4**<br/>*(Frontend Angular Kho)* | - Tạo `InventoryService` (`frontend/src/app/core/services/inventory.service.ts`) gọi qua Gateway `:8000`.<br/>- Màn hình **Tồn kho & Lô hàng FEFO (`/inventory`)**: cảnh báo cận hạn/hết hạn, xem biến động, thao tác hủy/kiểm kê có xác nhận & lý do.<br/>- Màn hình **Nhập hàng NCC (`/procurement`)**: tạo phiếu nhập nhiều dòng, xác nhận nhập kho. | `frontend/src/app/core/services/inventory.service.ts`<br/>`frontend/src/app/features/inventory/`<br/>`frontend/src/app/features/procurement/`<br/>*(Nhờ TV1 nối route vào `app.routes.ts`)* | Nhánh: `feature/fe-inventory-procurement`<br/>Commit: `feat(frontend): xây dựng màn hình tồn kho FEFO và phiếu nhập NCC` |
| **Thành viên 5**<br/>*(Seed Data & Kiểm thử QA)* | - Viết `app/scripts/seed.py` tạo NCC mẫu, phiếu nhập và các lô trái cây (còn hạn xa, cận hạn 2 ngày, đã hết hạn).<br/>- Viết **Unit/API Test (`pytest`)**: kiểm chứng Alembic rollback, FEFO chọn đúng lô hết hạn trước, chặn xuất lô hết hạn, hủy hàng không lý do trả `422`, RBAC `WAREHOUSE`/`MANAGER`.<br/>- Viết **E2E Test** qua Gateway (`test_inventory_via_gateway.py`). | `backend/services/inventory-service/app/scripts/seed.py`<br/>`backend/services/inventory-service/tests/test_inventory_api.py`<br/>`backend/tests/e2e/test_inventory_via_gateway.py` | Nhánh: `test/inventory-seed-and-e2e`<br/>Commit: `test(inventory): bổ sung seed data, unit test FEFO và E2E qua gateway` |

---

## 2. Sprint 2 (Sau Khi Xong Inventory): Bán Hàng (POS & Online), Thanh Toán & Báo Cáo

Sau khi toàn bộ luồng Kho & FEFO chạy ổn định và merge xong vào `develop`, nhóm chuyển sang ghép nối bán hàng:

1. **Thành viên 1:** **Order Service (`:8004`, `fruitstore_order_db`)** — Tạo đơn POS & Online, snapshot giá từ Catalog, gọi `inventory-service` giữ/trừ kho FEFO.
2. **Thành viên 2:** Mở rộng **Inventory + Order**: Xử lý hoàn kho khi hủy đơn, cập nhật trang Quản lý Đơn hàng (`/orders`).
3. **Thành viên 3:** **Payment Service (`:8005`, `fruitstore_payment_db`)** + Màn hình **Bán hàng tại quầy POS (`/pos`)** & Giao dịch (`/payments`).
4. **Thành viên 4:** **Reporting Service (`:8006`, `fruitstore_reporting_db`)** + Nối dữ liệu thật cho **Dashboard (`/dashboard`)** & Báo cáo Doanh thu/Hao hụt.
5. **Thành viên 5:** **Storefront Khách hàng (`/shop`, Giỏ hàng, Checkout)** + **AI Chatbot Service (`:8007`)** + Test E2E toàn chuỗi.

---

## 3. Quy Tắc Phối Hợp Hàng Ngày (Tránh Conflict Tuyệt Đối)

1. **Không sửa chéo file ngoài bảng phân công:** Trong Sprint 1, Thành viên 2 chỉ sửa các file `procurement*`, Thành viên 3 chỉ sửa `lot*`, Thành viên 4 chỉ sửa `frontend/src/app/features/{inventory,procurement}`, Thành viên 5 chỉ sửa `seed.py` & `tests/`.
2. **File dùng chung (`app/main.py`, `app.routes.ts`, `sidebar`):** Giao cho **Thành viên 1** gắn router/menu sau khi các thành viên khác gửi PR hoặc tự cập nhật theo thứ tự đã thống nhất.
3. **Kiểm tra trước khi mở PR:**
   - Backend: chạy `pytest` của `inventory-service` đạt 100%.
   - Frontend: chạy `npx tsc --noEmit` đạt 0 lỗi và đối chiếu checklist mục 17 trong [`UI_UX_DESIGN_RULES_FruitStore.md`](../UI_UX_DESIGN_RULES_FruitStore.md).

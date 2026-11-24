# Quy Chuẩn Lập Trình & Quy Trình Git (Coding Convention) — FruitStore Management System

> **Mục đích:** Tài liệu thống nhất quy tắc viết code, tổ chức thư mục, thiết kế API/Database, comment tiếng Việt và quy trình Git/Commit cho cả **5 thành viên** nhằm tránh xung đột code (merge conflict), giữ kiến trúc SOA sạch và dễ bảo trì.
>
> **Tài liệu liên quan:**
> - Giao diện & Thẩm mỹ: [`FRONTEND_DESIGN_RULES.md`](./FRONTEND_DESIGN_RULES.md)
> - Quy chuẩn UI/UX & Angular: [`UI_UX_DESIGN_RULES_FruitStore.md`](./UI_UX_DESIGN_RULES_FruitStore.md)
> - Thiết kế Database SOA: [`docs/databases/README.md`](./docs/databases/README.md)

---

## 1. Quy Trình Git, Nhánh (Branching) & Commit Chuẩn

### 1.1. Mô hình nhánh Git (Git Flow tinh gọn cho 5 thành viên)
- **`main`**: Nhánh ổn định, chỉ chứa code đã chạy test đạt và sẵn sàng demo/báo cáo. **Cấm push trực tiếp lên `main`**.
- **`develop`**: Nhánh tích hợp chung của cả nhóm. Mọi tính năng mới đều tạo nhánh từ `develop` và merge về `develop` qua Pull Request (PR).
- **Nhánh tính năng (`feature/*`)**:
  - Quy tắc đặt tên: `feature/<tên-service-hoặc-module>-<mô-tả-ngắn>` (chữ thường, nối bằng dấu gạch ngang `-`).
  - Ví dụ theo từng thành viên:
    - `feature/inventory-suppliers-po`
    - `feature/inventory-fefo-reservations`
    - `feature/order-pos-checkout`
    - `feature/payment-qr-idempotency`
    - `feature/reporting-sales-dashboard`
    - `feature/fe-pos-screen`
    - `feature/chatbot-tool-calling`
- **Nhánh sửa lỗi (`fix/*`)**: `fix/<module>-<lỗi>` (ví dụ: `fix/auth-google-clock-skew`).
- **Nhánh tài liệu/cấu hình (`docs/*`, `chore/*`)**: `docs/readme-setup`, `chore/docker-compose`.

### 1.2. Quy tắc Commit (Conventional Commits)
Mỗi commit chỉ làm **một việc rõ ràng**, viết theo cấu trúc:

```text
<type>(<scope>): <mô tả ngắn gọn bằng tiếng Việt có dấu, viết thường chữ đầu>

[Phần thân tùy chọn - giải thích TẠI SAO thay đổi hoặc liệt kê các ý chính]
```

- **Các `<type>` được phép dùng:**
  - `feat`: Thêm chức năng mới (API, màn hình, bảng DB).
  - `fix`: Sửa lỗi (bug logic, lỗi UI, lỗi bảo mật).
  - `refactor`: Tái cấu trúc code nhưng không đổi hành vi nghiệp vụ.
  - `docs`: Cập nhật tài liệu (`.md`, `README.md`, schema doc).
  - `test`: Thêm hoặc sửa unit test / E2E test.
  - `chore`: Cập nhật config, `.env.example`, script `.bat`, dependencies.
  - `style`: Định dạng code (spacing, lint), không sửa logic.
- **Các `<scope>` chuẩn của dự án:**
  - `gateway`, `auth`, `catalog`, `inventory`, `order`, `payment`, `reporting`, `chatbot`, `frontend`, `db`, `e2e`.
- **Ví dụ Commit ĐÚNG:**
  - `feat(inventory): thêm API nhập hàng NCC và sinh lô stock_lots`
  - `fix(order): khóa dòng tồn kho khi tạo đơn POS đồng thời`
  - `feat(frontend): xây dựng màn hình tồn kho và cảnh báo lô cận hạn FEFO`
  - `test(inventory): kiểm thử thuật toán FEFO và hủy hàng hỏng`
- **Ví dụ Commit SAI (Cần tránh):**
  - `update code`, `fix bug`, `done`, `abc`, `sua lai file` (không rõ scope và nội dung).
  - Commit gom cả 3 service khác nhau + sửa frontend vào chung 1 commit khổng lồ.

### 1.3. Quy tắc Pull Request (PR) & Chống Xung Đột (Conflict)
1. **Không tự ý sửa file thuộc service của thành viên khác** nếu chưa trao đổi. Nếu cần dùng API từ service khác, chỉ gọi qua **HTTP API Gateway** (hoặc thống nhất DTO contract trước).
2. Trước khi tạo PR vào `develop`:
   - Chạy `git pull origin develop` (hoặc `rebase`) để giải quyết xung đột tại máy cá nhân.
   - Chạy `pytest` của service mình phụ trách (Backend) hoặc `npx tsc --noEmit` (Frontend) phải **Pass 100%**.
   - **Không commit** file `.env` chứa mật khẩu thật, thư mục `.venv/`, `node_modules/`, `__pycache__/`, `.db` test tạm. (Chỉ commit `.env.example`).
3. Mỗi PR cần ít nhất **1 thành viên khác (hoặc Tech Lead) review** trước khi bấm Merge.

---

## 2. Quy Chuẩn Backend (Python 3.13 / FastAPI / SOA)

### 2.1. Kiến trúc phân tầng bắt buộc (`NFR-M01`)
Mỗi microservice (`auth-service`, `catalog-service`, `inventory-service`, `order-service`, `payment-service`, `reporting-service`, `chatbot-service`) **phải giữ nguyên cấu trúc 4 tầng**:

```text
services/<service-name>/
├── alembic/                  # Migration độc lập (NFR-M02)
├── alembic.ini
├── app/
│   ├── main.py               # Khởi tạo FastAPI, /health (SELECT 1), đăng ký router
│   ├── core/                 # config.py, deps.py (X-Internal-Key, RBAC), exceptions.py
│   ├── db/                   # base.py, session.py (SQLAlchemy 2.0 Async)
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic v2 DTOs (request/response)
│   ├── repositories/         # CHỈ chứa truy vấn SQLAlchemy, KHÔNG chứa logic nghiệp vụ
│   ├── services/             # CHỈ chứa logic nghiệp vụ & kiểm tra điều kiện
│   ├── api/v1/               # CHỈ parse request, gọi service và trả DTO
│   └── scripts/seed.py       # Seed dữ liệu mẫu idempotent
├── tests/                    # Pytest + pytest-asyncio
├── .env.example
└── pytest.ini
```

### 2.2. Quy tắc Comment Tiếng Việt Bắt Buộc
Mọi file Python tạo mới hoặc chỉnh sửa phải có:
1. **Module Docstring ở đầu file** ghi rõ `Module:` và `Nhiệm vụ:`.
2. **Docstring tiếng Việt** cho mọi class và function/endpoint chính.

```python
"""
Module: app.services.inventory_service
Nhiệm vụ: Xử lý nghiệp vụ nhập kho NCC, phân bổ lô hàng theo FEFO
          và ghi nhận biến động tồn kho (`stock_movements`).
"""
```

### 2.3. Quy tắc Dữ liệu & An toàn Giao dịch (`NFR-K04`, `NFR-S08`)
- **Database-per-Service:** Tuyệt đối **không import code** hay **JOIN/Foreign Key** sang database của service khác. Giao tiếp liên service thực hiện qua HTTP API.
- **Kiểu dữ liệu chuẩn:**
  - Khóa chính: `UUID` (`Uuid(as_uuid=True)`), không dùng `SERIAL`/`INT` tự tăng cho thực thể nghiệp vụ chính.
  - Tiền tệ (VNĐ): `Numeric(14, 2)` trong DB và `Decimal` trong Python, serialize JSON thành chuỗi `"65000.00"`. **Cấm dùng `float` cho tiền**.
  - Khối lượng / Số lượng: `Numeric(10, 3)` trong DB và `Decimal` trong Python (hỗ trợ cân lẻ như `2.500 kg`).
  - Thời gian: `DateTime(timezone=True)` lưu UTC (`datetime.now(timezone.utc)`).
- **Chống Race Condition:** Các thao tác trừ tồn kho, giữ hàng (`reservation`), đổi giá hoặc thanh toán bắt buộc dùng transaction và khóa dòng `SELECT ... FOR UPDATE` (`with_for_update()`).
- **Định dạng lỗi thống nhất:** Mọi lỗi nghiệp vụ ném `AppError(status_code, code, message, details)` để trả JSON chuẩn:
  ```json
  { "code": "INSUFFICIENT_STOCK", "message": "Số lượng tồn kho khả dụng không đủ.", "details": {} }
  ```
- **Bảo mật nội bộ (`NFR-S03`):** Mọi router nghiệp vụ trong service đều phải gắn `Depends(verify_internal_key)` và phân quyền bằng `Depends(require_roles(...))` đọc từ header `X-User-Id`, `X-User-Role` do API Gateway truyền xuống.

### 2.4. Quy tắc Alembic Migration (`NFR-M02`)
- **Cấm dùng `Base.metadata.create_all()`** trong code chạy thật (`app/main.py`).
- Mọi thay đổi bảng phải tạo file migration Alembic mới và viết đủ cả hai hàm `upgrade()` lẫn `downgrade()` để rollback độc lập.

---

## 3. Quy Chuẩn Frontend (Angular 21 / TypeScript)

Tuân thủ song song [`FRONTEND_DESIGN_RULES.md`](./FRONTEND_DESIGN_RULES.md) và [`UI_UX_DESIGN_RULES_FruitStore.md`](./UI_UX_DESIGN_RULES_FruitStore.md):

1. **Cấu trúc module:**
   - Gọi API qua service riêng trong `src/app/core/services/<tên>.service.ts`, dùng URL đi qua **API Gateway (`http://localhost:8000/api/v1/...`)**, không gọi thẳng port 8001–8007.
   - Không dùng `any` tùy tiện; khai báo đầy đủ TypeScript `interface`/`type` cho DTO.
   - Dùng Angular Standalone Component + Signals (`signal`, `computed`).
2. **Comment tiếng Việt:** Đầu mỗi file `.ts`, `.html`, `.css` phải có header comment nêu rõ `Module:` và `Nhiệm vụ:`.
3. **Ngôn ngữ & Đơn vị nghiệp vụ:**
   - 100% tiếng Việt có dấu tự nhiên, rõ ràng.
   - Giá bán luôn đi kèm đơn vị: `65.000 ₫/kg`, `145.000 ₫/hộp`, `58.000 ₫/quả`.
   - Không làm giả số liệu thành công trước khi API trả về `200/201`; mọi màn hình danh sách bắt buộc có đủ 4 trạng thái: **Loading, Empty, Error (có nút Thử lại), Data**.
4. **Màu sắc & Design Tokens:**
   - White-first (`#FFFFFF` card, `#F7F9F7` nền, `#DDE5DF` viền `1px`, `#246B45`/`#2F855A` màu thương hiệu). Không tự ý thêm gradient sặc sỡ hoặc shadow nặng.

---

## 4. Checklist Tự Kiểm Tra Trước Khi Đẩy Code (Push/PR)

- [ ] Code đặt đúng thư mục service / feature được phân công.
- [ ] Tất cả file mới/sửa đều có comment tiếng Việt giải thích nhiệm vụ module.
- [ ] Không có khóa ngoại/truy vấn chéo DB; không dùng `float` cho tiền tệ.
- [ ] Đã viết test cho happy-path và các lỗi nghiệp vụ chính (403, 404, 409, 422).
- [ ] Commit đúng định dạng `<type>(<scope>): <mô tả tiếng Việt>`.
- [ ] Không lọt file `.env`, `.venv`, `node_modules` vào commit.

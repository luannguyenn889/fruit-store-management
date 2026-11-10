-- =============================================================================
-- MODULE: 00_init_all_databases.sql
-- NHIỆM VỤ: Khởi tạo các Database độc lập và DB Roles riêng biệt cho từng
--           microservice theo nguyên tắc Database-per-Service (NFR-S08).
--           Thu hồi quyền kết nối mặc định (REVOKE CONNECT FROM PUBLIC) để đảm bảo
--           một service không thể truy cập trực tiếp database của service khác.
-- HƯỚNG DẪN:
--   1. Mở pgAdmin 4 hoặc psql (đăng nhập bằng superuser 'postgres').
--   2. Chọn Query Tool tại database mặc định 'postgres' và thực thi phần 1 & 2.
--   3. Đổi các mật khẩu 'CHANGE_ME_*' tương ứng với file .env của từng service.
--   4. Kết nối vào từng DB mới tạo bằng 'postgres' và chạy lệnh:
--        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
--      Sau đó chạy Alembic migration của từng service (`alembic upgrade head`).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. TẠO DB ROLES RIÊNG CHO TỪNG SERVICE (NFR-S08)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'auth_user') THEN
        CREATE ROLE auth_user LOGIN PASSWORD 'CHANGE_ME_auth';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'catalog_user') THEN
        CREATE ROLE catalog_user LOGIN PASSWORD 'CHANGE_ME_catalog';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'inventory_user') THEN
        CREATE ROLE inventory_user LOGIN PASSWORD 'CHANGE_ME_inventory';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'order_user') THEN
        CREATE ROLE order_user LOGIN PASSWORD 'CHANGE_ME_order';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'payment_user') THEN
        CREATE ROLE payment_user LOGIN PASSWORD 'CHANGE_ME_payment';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'reporting_user') THEN
        CREATE ROLE reporting_user LOGIN PASSWORD 'CHANGE_ME_reporting';
    END IF;
END
$$;

-- -----------------------------------------------------------------------------
-- 2. TẠO DATABASE ĐỘC LẬP & GÁN CHỦ SỞ HỮU (OWNER) CHO TỪNG ROLE
-- (Lưu ý: Trong pgAdmin Query Tool, chạy cụm CREATE DATABASE riêng nếu báo lỗi transaction block)
-- -----------------------------------------------------------------------------
CREATE DATABASE fruitstore_auth_db      OWNER auth_user;
CREATE DATABASE fruitstore_catalog_db   OWNER catalog_user;
CREATE DATABASE fruitstore_inventory_db OWNER inventory_user;
CREATE DATABASE fruitstore_order_db     OWNER order_user;
CREATE DATABASE fruitstore_payment_db   OWNER payment_user;
CREATE DATABASE fruitstore_reporting_db OWNER reporting_user;

-- -----------------------------------------------------------------------------
-- 3. CÔ LẬP QUYỀN KẾT NỐI GIỮA CÁC DATABASE (NFR-S08)
-- Thu hồi quyền CONNECT của nhóm PUBLIC để catalog_user không thể vào auth_db và ngược lại
-- -----------------------------------------------------------------------------
REVOKE CONNECT ON DATABASE fruitstore_auth_db      FROM PUBLIC;
REVOKE CONNECT ON DATABASE fruitstore_catalog_db   FROM PUBLIC;
REVOKE CONNECT ON DATABASE fruitstore_inventory_db FROM PUBLIC;
REVOKE CONNECT ON DATABASE fruitstore_order_db     FROM PUBLIC;
REVOKE CONNECT ON DATABASE fruitstore_payment_db   FROM PUBLIC;
REVOKE CONNECT ON DATABASE fruitstore_reporting_db FROM PUBLIC;

GRANT CONNECT ON DATABASE fruitstore_auth_db      TO auth_user;
GRANT CONNECT ON DATABASE fruitstore_catalog_db   TO catalog_user;
GRANT CONNECT ON DATABASE fruitstore_inventory_db TO inventory_user;
GRANT CONNECT ON DATABASE fruitstore_order_db     TO order_user;
GRANT CONNECT ON DATABASE fruitstore_payment_db   TO payment_user;
GRANT CONNECT ON DATABASE fruitstore_reporting_db TO reporting_user;

-- =============================================================================
-- 4. BƯỚC TIẾP THEO (CHẠY TRÊN TỪNG DATABASE):
-- Kết nối vào 'fruitstore_auth_db' và 'fruitstore_catalog_db' với quyền superuser:
--   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
--   GRANT ALL ON SCHEMA public TO auth_user;      -- (trong fruitstore_auth_db)
--   GRANT ALL ON SCHEMA public TO catalog_user;   -- (trong fruitstore_catalog_db)
-- Nguồn sự thật của bảng dữ liệu là Alembic migration trong từng service!
-- =============================================================================

-- =============================================================================
-- SCRIPT KHỞI TẠO TẤT CẢ DATABASE CHO HỆ THỐNG FRUITSTORE (SOA)
-- Hướng dẫn: Mở pgAdmin 4 hoặc psql (kết nối với tài khoản postgres), 
--            chọn Query Tool ở database 'postgres' mặc định và chạy file này.
-- =============================================================================

-- 1. Tạo các Database độc lập cho từng dịch vụ
CREATE DATABASE fruitstore_auth_db;
CREATE DATABASE fruitstore_catalog_db;
CREATE DATABASE fruitstore_inventory_db;
CREATE DATABASE fruitstore_order_db;
CREATE DATABASE fruitstore_payment_db;
CREATE DATABASE fruitstore_reporting_db;
CREATE DATABASE fruitstore_chatbot_db;

-- =============================================================================
-- SAU KHI TẠO XONG CÁC DATABASE Ở TRÊN:
-- Kết nối vào từng Database tương ứng để chạy schema DDL:
-- 1. Vào 'fruitstore_auth_db'      -> Chạy file: 01_auth_schema.sql
-- 2. Vào 'fruitstore_catalog_db'   -> Chạy file: 02_catalog_schema.sql
-- 3. Vào 'fruitstore_inventory_db' -> Chạy file: 03_inventory_schema.sql
-- 4. Vào 'fruitstore_order_db'     -> Chạy file: 04_order_schema.sql
-- 5. Vào 'fruitstore_payment_db'   -> Chạy file: 05_payment_schema.sql
-- 6. Vào 'fruitstore_reporting_db' -> Chạy file: 06_reporting_schema.sql
-- 7. Vào 'fruitstore_chatbot_db'   -> Chạy file: 07_chatbot_schema.sql
-- =============================================================================


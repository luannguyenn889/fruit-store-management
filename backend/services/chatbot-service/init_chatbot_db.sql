-- =============================================================================
-- SCRIPT KHỞI TẠO CƠ SỞ DỮ LIỆU CÔ LẬP CHO CHATBOT SERVICE (NFR-S08)
-- Chạy bằng quyền superuser `postgres` trong pgAdmin 4 hoặc psql:
--   Bước 1: Tạo role & database (chạy trên database `postgres`)
-- =============================================================================
-- CREATE USER chatbot_user WITH PASSWORD 'CHANGE_ME_chatbot';
-- CREATE DATABASE fruitstore_chatbot_db OWNER chatbot_user;
-- REVOKE CONNECT ON DATABASE fruitstore_chatbot_db FROM PUBLIC;
-- GRANT CONNECT ON DATABASE fruitstore_chatbot_db TO chatbot_user;

-- Bước 2: Chạy bên trong database `fruitstore_chatbot_db`:
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
GRANT ALL ON SCHEMA public TO chatbot_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chatbot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chatbot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO chatbot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO chatbot_user;

-- =============================================================================
-- SCRIPT PHÂN QUYỀN SCHEMA CHO INVENTORY SERVICE (NFR-S08)
-- Chạy bằng quyền superuser `postgres` trong Query Tool của pgAdmin 4 (hoặc psql)
-- TẠI DATABASE `fruitstore_inventory_db`:
--   (Lưu ý: `docs/databases/00_init_all_databases.sql` đã tạo role `inventory_user`
--    và database `fruitstore_inventory_db`, chỉ cần cấp quyền schema public như
--    hướng dẫn ở README.md cho auth_user và catalog_user.)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
GRANT ALL ON SCHEMA public TO inventory_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO inventory_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO inventory_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO inventory_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO inventory_user;

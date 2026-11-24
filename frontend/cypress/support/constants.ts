/**
 * Module: cypress/support/constants.ts
 * Nhiệm vụ: Khai báo tập trung URL API Gateway và các tài khoản mẫu kiểm thử E2E
 *           (tương thích Cypress 16+, thay thế `Cypress.env()` đã bị loại bỏ từ v16.0.0).
 */

export const TEST_CONFIG = {
  apiUrl: 'http://localhost:8000/api/v1',
  adminEmail: 'admin@fruitstore.com',
  adminPassword: 'admin123',
  managerEmail: 'manager@fruitstore.com',
  managerPassword: 'Manager@123',
  staffEmail: 'staff@fruitstore.com',
  staffPassword: 'Staff@123',
};

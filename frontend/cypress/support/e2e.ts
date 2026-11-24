/**
 * Module: cypress/support/e2e.ts
 * Nhiệm vụ: Điểm nạp toàn cục cho mọi bài test Cypress E2E (đăng ký custom commands
 *           và xử lý ngoại lệ không mong muốn từ script Google Identity bên thứ 3).
 */

import './commands';

// Bỏ qua lỗi từ Google Identity script ngoài mạng khi chạy kiểm thử E2E cô lập
Cypress.on('uncaught:exception', err => {
  if (
    err.message.includes('google') ||
    err.message.includes('gsi') ||
    err.message.includes('ResizeObserver')
  ) {
    return false;
  }
  return undefined;
});

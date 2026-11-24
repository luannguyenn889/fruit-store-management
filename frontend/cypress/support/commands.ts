/**
 * Module: cypress/support/commands.ts
 * Nhiệm vụ: Định nghĩa các lệnh dùng chung (Custom Commands) cho bộ kiểm thử Cypress E2E:
 *           - `cy.loginByApi(email, password)`: Đăng nhập nhanh qua API Gateway và lưu token vào localStorage.
 *           - `cy.loginByUi(email, password)`: Thao tác đăng nhập trực tiếp trên màn hình `/login`.
 *           - `cy.clearAuthSession()`: Xóa sạch phiên đăng nhập cục bộ trước khi chạy test case mới.
 */

import { TEST_CONFIG } from './constants';

declare global {
  namespace Cypress {
    interface Chainable {
      /** Đăng nhập nhanh bằng API Gateway và nạp phiên vào localStorage */
      loginByApi(email: string, password: string): Chainable<void>;
      /** Đăng nhập trực tiếp thông qua biểu mẫu UI tại /login */
      loginByUi(email: string, password: string): Chainable<void>;
      /** Xóa phiên đăng nhập trong localStorage */
      clearAuthSession(): Chainable<void>;
    }
  }
}

Cypress.Commands.add('clearAuthSession', () => {
  cy.window().then(win => {
    win.localStorage.removeItem('fruitstore_access_token');
    win.localStorage.removeItem('fruitstore_refresh_token');
    win.localStorage.removeItem('fruitstore_user');
  });
});

Cypress.Commands.add('loginByApi', (email: string, password: string) => {
  cy.request({
    method: 'POST',
    url: `${TEST_CONFIG.apiUrl}/auth/login`,
    body: { email, password },
  }).then(resp => {
    expect(resp.status).to.eq(200);
    cy.visit('/login');
    cy.window().then(win => {
      win.localStorage.setItem('fruitstore_access_token', resp.body.access_token);
      if (resp.body.refresh_token) {
        win.localStorage.setItem('fruitstore_refresh_token', resp.body.refresh_token);
      }
      win.localStorage.setItem('fruitstore_user', JSON.stringify(resp.body.user));
    });
  });
});

Cypress.Commands.add('loginByUi', (email: string, password: string) => {
  cy.visit('/login');
  cy.get('input[name="contact"]').clear().type(email);
  cy.get('input[name="password"]').clear().type(password);
  cy.get('button[type="submit"]').click();
});

export {};

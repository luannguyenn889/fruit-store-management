/**
 * Module: cypress/e2e/03_users_profile.cy.ts
 * Nhiệm vụ: Kiểm thử E2E chức năng Hồ sơ cá nhân (`PATCH /auth/me`), Đổi mật khẩu
 *           (`POST /auth/change-password`) tại `/profile` (FR-A04) và `roleGuard` chặn `CUSTOMER`
 *           truy cập khu vực quản trị (`/dashboard`, `/catalog`, `/users`).
 *           Sử dụng tài khoản tạo riêng cho phiên test để không ảnh hưởng tài khoản mẫu.
 */

import { TEST_CONFIG } from '../support/constants';

describe('FR-A04 - Hồ sơ cá nhân & Đổi mật khẩu (/profile)', () => {
  const uniqueEmail = `e2e_profile_${Date.now()}@fruitstore.com`;
  const initialPassword = 'Profile@123';
  const updatedPassword = 'NewProfile@456';

  before(() => {
    cy.request({
      method: 'POST',
      url: `${TEST_CONFIG.apiUrl}/auth/register`,
      body: {
        email: uniqueEmail,
        full_name: 'Khách Hàng Test Hồ Sơ',
        password: initialPassword,
      },
    }).its('status').should('eq', 201);
  });

  it('TC_FR-A04_01: Cập nhật họ tên và số điện thoại cá nhân thành công và giữ nguyên sau F5', () => {
    const uniquePhone = `09${String(Date.now()).slice(-8)}`;
    cy.loginByApi(uniqueEmail, initialPassword);
    cy.visit('/profile');

    // Tài khoản CUSTOMER tự mở tab Hồ sơ cá nhân
    cy.get('#profile-name').clear().type('Khách Hàng Đã Cập Nhật');
    cy.get('#profile-phone').clear().type(uniquePhone);
    cy.contains('button', 'Lưu thông tin').click();

    cy.contains('Đã cập nhật thông tin hồ sơ cá nhân thành công.').should('be.visible');
    cy.reload();
    cy.get('#profile-name').should('have.value', 'Khách Hàng Đã Cập Nhật');
    cy.get('#profile-phone').should('have.value', uniquePhone);
  });

  it('TC_FR-A04_02: Cập nhật họ tên dưới 2 ký tự hiển thị lỗi validation', () => {
    cy.loginByApi(uniqueEmail, initialPassword);
    cy.visit('/profile');

    cy.get('#profile-name').clear().type('A');
    cy.contains('button', 'Lưu thông tin').click();
    cy.contains('Họ và tên phải có tối thiểu 2 ký tự.').should('be.visible');
  });

  it('TC_FR-A04_03: Đổi mật khẩu với mật khẩu hiện tại không đúng (400)', () => {
    cy.loginByApi(uniqueEmail, initialPassword);
    cy.visit('/profile');

    cy.get('#curr-pwd').type('SaiMatKhauCu@1');
    cy.get('#new-pwd').type(updatedPassword);
    cy.get('#confirm-pwd').type(updatedPassword);
    cy.contains('button', 'Cập nhật mật khẩu').click();

    cy.contains('Mật khẩu hiện tại không chính xác.').should('be.visible');
  });

  it('TC_FR-A04_04: Đổi mật khẩu khi mật khẩu xác nhận không khớp', () => {
    cy.loginByApi(uniqueEmail, initialPassword);
    cy.visit('/profile');

    cy.get('#curr-pwd').type(initialPassword);
    cy.get('#new-pwd').type(updatedPassword);
    cy.get('#confirm-pwd').type('KhongKhop@999');
    cy.contains('button', 'Cập nhật mật khẩu').click();

    cy.contains('Mật khẩu xác nhận không khớp với mật khẩu mới.').should('be.visible');
  });

  it('TC_FR-A04_05: Đổi mật khẩu thành công và đăng nhập lại bằng mật khẩu mới', () => {
    cy.loginByApi(uniqueEmail, initialPassword);
    cy.visit('/profile');

    cy.get('#curr-pwd').type(initialPassword);
    cy.get('#new-pwd').type(updatedPassword);
    cy.get('#confirm-pwd').type(updatedPassword);
    cy.contains('button', 'Cập nhật mật khẩu').click();

    cy.contains('Đã đổi mật khẩu thành công.').should('be.visible');

    // Đăng xuất và đăng nhập lại bằng mật khẩu mới
    cy.get('button.logout-icon-btn').click();
    cy.url().should('include', '/login');
    cy.loginByUi(uniqueEmail, updatedPassword);
    cy.url({ timeout: 15000 }).should('include', '/shop');
  });

  it('TC_FR-A04_06: Tài khoản CUSTOMER bị roleGuard chuyển hướng về /shop khi vào khu vực quản trị', () => {
    cy.loginByApi(uniqueEmail, updatedPassword);

    cy.visit('/dashboard');
    cy.url({ timeout: 15000 }).should('include', '/shop');

    cy.visit('/catalog');
    cy.url({ timeout: 15000 }).should('include', '/shop');

    cy.visit('/users');
    cy.url({ timeout: 15000 }).should('include', '/shop');

    cy.contains('h1', 'Trái cây tươi chọn lọc mỗi ngày').should('be.visible');
  });
});

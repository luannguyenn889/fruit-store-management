/**
 * Module: cypress/e2e/04_users_admin.cy.ts
 * Nhiệm vụ: Kiểm thử E2E Quản trị Nhân sự & Phân quyền RBAC dành riêng cho ADMIN (FR-A05)
 *           tại `/users`. Ánh xạ 1-1 với TC_FR-A05_01 .. TC_FR-A05_06 trong CSV.
 */

import { TEST_CONFIG } from '../support/constants';

describe('FR-A05 - Quản trị Nhân sự & Phân quyền RBAC (/users)', () => {
  const newStaffEmail = `e2e_kho_${Date.now()}@fruitstore.com`;
  const newStaffPassword = 'KhoUser@123';
  const newStaffName = 'Phạm Thủ Kho E2E';

  it('TC_FR-A05_01: Tài khoản MANAGER (không có quyền ADMIN) không truy cập được danh sách nhân sự', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/users');

    cy.contains('button[role="tab"]', 'Quản trị Nhân sự & Phân quyền').click();
    cy.contains('Chức năng chỉ dành cho Quản trị viên (ADMIN)').should('be.visible');
  });

  it('TC_FR-A05_02: ADMIN xem danh sách tài khoản, tìm kiếm theo email và lọc theo vai trò', () => {
    cy.loginByApi(TEST_CONFIG.adminEmail, TEST_CONFIG.adminPassword);
    cy.visit('/users');

    cy.contains('h2', 'Danh sách tài khoản').should('be.visible');
    cy.get('#user-search-input').type('manager@fruitstore.com');
    cy.contains('button', 'Tìm kiếm').click();
    cy.contains('td', 'manager@fruitstore.com').should('be.visible');

    cy.contains('button', 'Đặt lại').click();
    cy.get('#user-role-filter').select('STAFF');
    cy.contains('td', 'staff@fruitstore.com').should('be.visible');
  });

  it('TC_FR-A05_03: ADMIN tạo tài khoản nhân sự mới với vai trò WAREHOUSE', () => {
    cy.loginByApi(TEST_CONFIG.adminEmail, TEST_CONFIG.adminPassword);
    cy.visit('/users');

    cy.contains('button', '+ Tạo tài khoản nhân sự').click();
    cy.get('#new-user-name').type(newStaffName);
    cy.get('#new-user-email').type(newStaffEmail);
    cy.get('#new-user-pwd').type(newStaffPassword);

    // Bỏ chọn STAFF mặc định, chọn WAREHOUSE
    cy.contains('label.role-checkbox-item', 'STAFF').find('input[type="checkbox"]').uncheck();
    cy.contains('label.role-checkbox-item', 'WAREHOUSE').find('input[type="checkbox"]').check();

    cy.get('.modal-panel button[type="submit"]').click();
    cy.contains(`Đã tạo tài khoản "${newStaffName}"`).should('be.visible');
    cy.contains('tr', newStaffEmail).should('be.visible').and('contain.text', 'Nhân viên kho');
  });

  it('TC_FR-A05_04: ADMIN cập nhật phân quyền cho nhân sự sang STAFF + WAREHOUSE', () => {
    cy.loginByApi(TEST_CONFIG.adminEmail, TEST_CONFIG.adminPassword);
    cy.visit('/users');

    cy.get('#user-search-input').type(newStaffEmail);
    cy.contains('button', 'Tìm kiếm').click();
    cy.contains('tr', newStaffEmail).contains('button', 'Phân quyền').click();

    cy.get('.modal-panel').contains('label.role-checkbox-item', 'STAFF').find('input').check();
    cy.contains('button', 'Lưu phân quyền').click();

    cy.contains(`Đã cập nhật vai trò cho tài khoản "${newStaffName}"`).should('be.visible');
    cy.contains('tr', newStaffEmail)
      .should('contain.text', 'Nhân viên bán hàng')
      .and('contain.text', 'Nhân viên kho');
  });

  it('TC_FR-A05_05: ADMIN khóa tài khoản có xác nhận và tài khoản bị khóa không thể đăng nhập (403)', () => {
    cy.loginByApi(TEST_CONFIG.adminEmail, TEST_CONFIG.adminPassword);
    cy.visit('/users');

    cy.get('#user-search-input').type(newStaffEmail);
    cy.contains('button', 'Tìm kiếm').click();
    cy.contains('tr', newStaffEmail).contains('button', 'Khóa').click();

    cy.contains('Xác nhận khóa tài khoản').should('be.visible');
    cy.get('.modal-panel').contains('button', 'Xác nhận').click();
    cy.contains('tr', newStaffEmail).should('contain.text', 'Đã khóa');

    // Đăng xuất và thử đăng nhập bằng tài khoản vừa khóa -> bị từ chối 403
    cy.get('button.logout-icon-btn').click();
    cy.url().should('include', '/login');
    cy.loginByUi(newStaffEmail, newStaffPassword);
    cy.contains("trạng thái 'LOCKED'").should('be.visible');
  });

  it('TC_FR-A05_06: ADMIN mở khóa tài khoản và tài khoản đăng nhập lại được bình thường', () => {
    cy.loginByApi(TEST_CONFIG.adminEmail, TEST_CONFIG.adminPassword);
    cy.visit('/users');

    cy.get('#user-search-input').type(newStaffEmail);
    cy.contains('button', 'Tìm kiếm').click();
    cy.contains('tr', newStaffEmail).contains('button', 'Mở khóa').click();

    cy.contains('Xác nhận mở khóa tài khoản').should('be.visible');
    cy.get('.modal-panel').contains('button', 'Xác nhận').click();
    cy.contains('tr', newStaffEmail).should('contain.text', 'Đang hoạt động');

    cy.get('button.logout-icon-btn').click();
    cy.url().should('include', '/login');
    cy.loginByUi(newStaffEmail, newStaffPassword);
    cy.url({ timeout: 15000 }).should('include', '/dashboard');
  });
});

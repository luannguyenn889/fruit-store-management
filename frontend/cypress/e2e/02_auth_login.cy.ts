/**
 * Module: cypress/e2e/02_auth_login.cy.ts
 * Nhiệm vụ: Kiểm thử E2E nhóm Đăng nhập, Gia hạn phiên Refresh Token (FR-A02)
 *           và Đăng xuất thu hồi phiên / Bảo vệ Route (FR-A03).
 *           Ánh xạ 1-1 với TC_FR-A02_01..11 và TC_FR-A03_01..02 trong CSV.
 */

import { TEST_CONFIG } from '../support/constants';

describe('FR-A02 & FR-A03 - Đăng nhập, Refresh Token & Đăng xuất', () => {
  beforeEach(() => {
    cy.visit('/login');
    cy.clearAuthSession();
  });

  it('TC_FR-A02_01: Đăng nhập thành công với tài khoản Manager và lưu Access + Refresh Token', () => {
    cy.loginByUi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.url({ timeout: 15000 }).should('include', '/dashboard');
    cy.window().then(win => {
      expect(win.localStorage.getItem('fruitstore_access_token')).to.be.a('string').and.not.be.empty;
      expect(win.localStorage.getItem('fruitstore_refresh_token')).to.be.a('string').and.not.be.empty;
    });
  });

  it('TC_FR-A02_02: Đăng nhập với mật khẩu không chính xác (401)', () => {
    cy.loginByUi(TEST_CONFIG.managerEmail, 'WrongPass@999');
    cy.contains('Email/số điện thoại hoặc mật khẩu không chính xác.').should('be.visible');
    cy.url().should('include', '/login');
  });

  it('TC_FR-A02_03: Đăng nhập với tài khoản chưa đăng ký (401)', () => {
    cy.loginByUi('khongtontai@fruitstore.com', 'Manager@123');
    cy.contains('Email/số điện thoại hoặc mật khẩu không chính xác.').should('be.visible');
    cy.url().should('include', '/login');
  });

  it('TC_FR-A02_04: Đăng nhập khi bỏ trống thông tin tài khoản hoặc mật khẩu', () => {
    cy.get('input[name="contact"]').clear();
    cy.get('input[name="password"]').clear();
    cy.get('button[type="submit"]').click();

    cy.contains('Vui lòng nhập đầy đủ email/số điện thoại và mật khẩu.').should('be.visible');
    cy.url().should('include', '/login');
  });

  it('TC_FR-A02_05: Đăng nhập bằng email có khoảng trắng ở đầu và cuối', () => {
    cy.loginByUi(`  ${TEST_CONFIG.managerEmail}  `, TEST_CONFIG.managerPassword);
    cy.url({ timeout: 15000 }).should('include', '/dashboard');
  });

  it('TC_FR-A02_06: Đăng nhập bằng phím Enter tại trường Mật khẩu', () => {
    cy.get('input[name="contact"]').clear().type(TEST_CONFIG.managerEmail);
    cy.get('input[name="password"]').clear().type(`${TEST_CONFIG.managerPassword}{enter}`);
    cy.url({ timeout: 15000 }).should('include', '/dashboard');
  });

  it('TC_FR-A02_07: Kiểm tra chức năng ẩn/hiện mật khẩu tại màn hình Đăng nhập', () => {
    cy.get('input[name="password"]').should('have.attr', 'type', 'password');
    cy.get('button.suffix-toggle-btn').click();
    cy.get('input[name="password"]').should('have.attr', 'type', 'text');
    cy.get('button.suffix-toggle-btn').click();
    cy.get('input[name="password"]').should('have.attr', 'type', 'password');
  });

  it('TC_FR-A02_08: Kiểm tra nút Đăng nhập bị disabled khi đang gửi yêu cầu xác thực', () => {
    cy.intercept('POST', '**/api/v1/auth/login', {
      delay: 600,
      statusCode: 401,
      body: { code: 'INVALID_CREDENTIALS', message: 'Email/số điện thoại hoặc mật khẩu không chính xác.' },
    }).as('slowLogin');

    cy.loginByUi(TEST_CONFIG.managerEmail, 'WrongPass@123');
    cy.get('button[type="submit"]').should('be.disabled').and('contain.text', 'Đang xác thực...');
    cy.wait('@slowLogin');
    cy.get('button[type="submit"]').should('not.be.disabled');
  });

  it('TC_FR-A02_09: Đăng nhập thất bại khi mất kết nối máy chủ Backend', () => {
    cy.intercept('POST', '**/api/v1/auth/login', { forceNetworkError: true }).as('netErr');

    cy.loginByUi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.wait('@netErr');
    cy.contains('Email/số điện thoại hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại.').should(
      'be.visible'
    );
  });

  it('TC_FR-A02_10: Điều hướng về trang Đăng nhập từ trang Đăng ký', () => {
    cy.visit('/register');
    cy.contains('a', 'Đăng nhập ngay').click();
    cy.url().should('include', '/login');
    cy.contains('h1', 'Đăng nhập hệ thống').should('be.visible');
  });

  it('TC_FR-A02_11: Tự động gọi /auth/refresh gia hạn Access Token khi gặp 401 từ API được bảo vệ', () => {
    cy.loginByApi(TEST_CONFIG.adminEmail, TEST_CONFIG.adminPassword);
    // Gán Access Token hỏng để giả lập token hết hạn nhưng giữ nguyên Refresh Token thật
    cy.window().then(win => {
      win.localStorage.setItem('fruitstore_access_token', 'expired.invalid.token');
    });

    cy.intercept('POST', '**/api/v1/auth/refresh').as('refreshCall');
    cy.visit('/users');
    cy.wait('@refreshCall').its('response.statusCode').should('eq', 200);
    cy.contains('h2', 'Danh sách tài khoản').should('be.visible');
  });

  it('TC_FR-A03_01: Đăng xuất gọi POST /auth/logout, xóa phiên và điều hướng về /login', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/dashboard');
    cy.intercept('POST', '**/api/v1/auth/logout').as('logoutCall');

    cy.get('button.logout-icon-btn').click();
    cy.wait('@logoutCall').its('response.statusCode').should('eq', 200);
    cy.url().should('include', '/login');
    cy.window().then(win => {
      expect(win.localStorage.getItem('fruitstore_access_token')).to.be.null;
      expect(win.localStorage.getItem('fruitstore_refresh_token')).to.be.null;
    });
  });

  it('TC_FR-A03_02: AuthGuard chặn truy cập thẳng vào /dashboard, /catalog, /users khi chưa đăng nhập', () => {
    cy.visit('/dashboard');
    cy.url().should('include', '/login');

    cy.visit('/catalog');
    cy.url().should('include', '/login');

    cy.visit('/users');
    cy.url().should('include', '/login');
  });
});

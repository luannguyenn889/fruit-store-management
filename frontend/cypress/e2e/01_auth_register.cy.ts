/**
 * Module: cypress/e2e/01_auth_register.cy.ts
 * Nhiệm vụ: Kiểm thử E2E nhóm chức năng Đăng ký tài khoản công khai (FR-A01) tại `/register`.
 *           Ánh xạ 1-1 với các mã TC_FR-A01_01 .. TC_FR-A01_11 trong `E2E_TestCases_FruitStore.csv`.
 */

import { TEST_CONFIG } from '../support/constants';

describe('FR-A01 - Đăng ký tài khoản công khai (/register)', () => {
  beforeEach(() => {
    cy.visit('/register');
    cy.clearAuthSession();
  });

  it('TC_FR-A01_01: Đăng ký tài khoản với thông tin hợp lệ và tự động gán vai trò CUSTOMER', () => {
    const uniqueEmail = `e2e_reg_${Date.now()}@fruitstore.com`;

    cy.get('input[name="fullName"]').type('Nguyễn Văn Kiểm Thử');
    cy.get('input[name="contact"]').type(uniqueEmail);
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@123');
    cy.get('input[name="agreeTerms"]').should('be.checked');
    cy.get('button[type="submit"]').click();

    cy.url({ timeout: 15000 }).should('include', '/shop');
    cy.window().then(win => {
      const userRaw = win.localStorage.getItem('fruitstore_user');
      expect(userRaw).to.not.be.null;
      const user = JSON.parse(userRaw!);
      expect(user.email).to.eq(uniqueEmail);
      const roleCodes = user.roles.map((r: any) => r.code);
      expect(roleCodes).to.deep.eq(['CUSTOMER']);
    });
  });

  it('TC_FR-A01_02: Đăng ký khi bỏ trống Họ và tên', () => {
    cy.get('input[name="contact"]').type('test_empty_name@fruitstore.com');
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@123');
    cy.get('button[type="submit"]').click();

    cy.contains('Vui lòng nhập họ và tên đầy đủ.').should('be.visible');
    cy.url().should('include', '/register');
  });

  it('TC_FR-A01_03: Đăng ký khi bỏ trống Email hoặc Số điện thoại', () => {
    cy.get('input[name="fullName"]').type('Nguyễn Văn B');
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@123');
    cy.get('button[type="submit"]').click();

    cy.contains('Vui lòng nhập địa chỉ email hoặc số điện thoại.').should('be.visible');
    cy.url().should('include', '/register');
  });

  it('TC_FR-A01_04: Đăng ký với mật khẩu ngắn hơn 6 ký tự', () => {
    cy.get('input[name="fullName"]').type('Nguyễn Văn C');
    cy.get('input[name="contact"]').type('shortpwd@fruitstore.com');
    cy.get('input[name="password"]').type('12345');
    cy.get('input[name="confirmPassword"]').type('12345');
    cy.get('button[type="submit"]').click();

    cy.contains('Mật khẩu phải có tối thiểu 6 ký tự.').should('be.visible');
    cy.url().should('include', '/register');
  });

  it('TC_FR-A01_05: Đăng ký khi xác nhận mật khẩu không trùng khớp', () => {
    cy.get('input[name="fullName"]').type('Nguyễn Văn D');
    cy.get('input[name="contact"]').type('mismatch@fruitstore.com');
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@999');
    cy.get('button[type="submit"]').click();

    cy.contains('Mật khẩu xác nhận không khớp. Vui lòng nhập lại.').should('be.visible');
    cy.url().should('include', '/register');
  });

  it('TC_FR-A01_06: Đăng ký khi bỏ chọn đồng ý Điều khoản dịch vụ', () => {
    cy.get('input[name="fullName"]').type('Nguyễn Văn E');
    cy.get('input[name="contact"]').type('noterms@fruitstore.com');
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@123');
    cy.get('input[name="agreeTerms"]').uncheck();
    cy.get('button[type="submit"]').click();

    cy.contains('Bạn cần đồng ý với Điều khoản dịch vụ và Chính sách bảo mật để tiếp tục.').should(
      'be.visible'
    );
  });

  it('TC_FR-A01_07: Đăng ký với email đã tồn tại trong hệ thống (409)', () => {
    cy.get('input[name="fullName"]').type('Người Dùng Trùng Email');
    cy.get('input[name="contact"]').type(TEST_CONFIG.managerEmail);
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@123');
    cy.get('button[type="submit"]').click();

    cy.contains('Địa chỉ email này đã được đăng ký').should('be.visible');
    cy.url().should('include', '/register');
  });

  it('TC_FR-A01_08: Kiểm tra chức năng ẩn/hiện mật khẩu ở cả 2 trường Mật khẩu và Xác nhận', () => {
    cy.get('input[name="password"]').type('Test@123').should('have.attr', 'type', 'password');
    cy.get('input[name="password"]').parent().find('button.suffix-toggle-btn').click();
    cy.get('input[name="password"]').should('have.attr', 'type', 'text');
    cy.get('input[name="password"]').parent().find('button.suffix-toggle-btn').click();
    cy.get('input[name="password"]').should('have.attr', 'type', 'password');

    cy.get('input[name="confirmPassword"]')
      .type('Test@123')
      .should('have.attr', 'type', 'password');
    cy.get('input[name="confirmPassword"]').parent().find('button.suffix-toggle-btn').click();
    cy.get('input[name="confirmPassword"]').should('have.attr', 'type', 'text');
  });

  it('TC_FR-A01_09: Điều hướng đến trang Đăng ký từ trang Đăng nhập', () => {
    cy.visit('/login');
    cy.contains('a', 'Đăng ký tài khoản mới').click();
    cy.url().should('include', '/register');
    cy.contains('h1', 'Tạo tài khoản mới').should('be.visible');
  });

  it('TC_FR-A01_10: Kiểm tra nút Đăng ký bị vô hiệu hóa (disabled) khi đang gửi yêu cầu', () => {
    cy.intercept('POST', '**/api/v1/auth/register', {
      delay: 600,
      statusCode: 409,
      body: { code: 'EMAIL_ALREADY_EXISTS', message: 'Địa chỉ email này đã được đăng ký.' },
    }).as('slowRegister');

    cy.get('input[name="fullName"]').type('Nguyễn Văn F');
    cy.get('input[name="contact"]').type('delay_check@fruitstore.com');
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@123');
    cy.get('button[type="submit"]').click();

    cy.get('button[type="submit"]').should('be.disabled').and('contain.text', 'Đang xử lý...');
    cy.wait('@slowRegister');
    cy.get('button[type="submit"]').should('not.be.disabled');
  });

  it('TC_FR-A01_11: Đăng ký thất bại khi mất kết nối máy chủ Backend', () => {
    cy.intercept('POST', '**/api/v1/auth/register', { forceNetworkError: true }).as('netErr');

    cy.get('input[name="fullName"]').type('Nguyễn Văn G');
    cy.get('input[name="contact"]').type('offline_reg@fruitstore.com');
    cy.get('input[name="password"]').type('Test@123');
    cy.get('input[name="confirmPassword"]').type('Test@123');
    cy.get('button[type="submit"]').click();

    cy.wait('@netErr');
    cy.contains('Không thể đăng ký tài khoản. Vui lòng kiểm tra lại thông tin đã nhập.').should(
      'be.visible'
    );
  });
});

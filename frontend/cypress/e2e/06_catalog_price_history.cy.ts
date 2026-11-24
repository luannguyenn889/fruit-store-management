/**
 * Module: cypress/e2e/06_catalog_price_history.cy.ts
 * Nhiệm vụ: Kiểm thử E2E quy trình Đổi đơn giá nguyên tử & Lịch sử đơn giá bất biến
 *           (`PriceHistory` - FR-B06, BR-07) trên `/catalog`.
 */

import { TEST_CONFIG } from '../support/constants';

describe('FR-B06 - Cập nhật Đơn giá & Lịch sử Giá (PriceHistory)', () => {
  const ts = Date.now();
  const sku = `PRICE-E2E-${String(ts).slice(-5)}`;
  const prodName = `Nhãn xuồng E2E ${String(ts).slice(-4)}`;

  before(() => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');
    cy.get('.cat-pill-group').should('have.length.at.least', 1);

    // Tạo sản phẩm riêng để kiểm thử đổi giá sạch và độc lập
    cy.contains('button', '+ Thêm sản phẩm mới').click();
    cy.get('#prod-sku-input').type(sku);
    cy.get('#prod-name-input').type(prodName);
    cy.get('#prod-unit-select').select('kg');
    cy.get('#prod-price-input').clear().type('60000');
    cy.get('#prod-origin-input').type('Vũng Tàu');
    cy.get('.modal-panel button[type="submit"]').click();
    cy.contains('tr', sku).should('be.visible');
  });

  it('TC_FR-B06_01: Đổi đơn giá hợp lệ kèm lý do và kiểm tra dòng PriceHistory Giá cũ -> Giá mới', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('tr', sku).contains('button', 'Đổi giá & Lịch sử').click();
    cy.get('#new-price-input').clear().type('68000');
    cy.get('#price-reason-input').type('Điều chỉnh giá mùa vụ E2E');
    cy.contains('button', 'Xác nhận đổi giá & Ghi lịch sử').click();

    cy.contains('68.000 ₫/kg').should('be.visible');
    cy.get('.history-table-wrap')
      .should('contain.text', '60.000 ₫/kg')
      .and('contain.text', '68.000 ₫/kg')
      .and('contain.text', 'Điều chỉnh giá mùa vụ E2E');
  });

  it('TC_FR-B06_02: Đổi đơn giá trùng với đơn giá hiện tại bị chặn', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('tr', sku).contains('button', 'Đổi giá & Lịch sử').click();
    cy.get('#new-price-input').clear().type('68000');
    cy.get('#price-reason-input').type('Thử nhập trùng giá');
    cy.contains('button', 'Xác nhận đổi giá & Ghi lịch sử').click();

    cy.contains('Đơn giá mới trùng với đơn giá hiện tại.').should('be.visible');
  });

  it('TC_FR-B06_03: Đổi đơn giá khi bỏ trống lý do điều chỉnh bị chặn', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('tr', sku).contains('button', 'Đổi giá & Lịch sử').click();
    cy.get('#new-price-input').clear().type('72000');
    cy.get('#price-reason-input').clear();
    cy.contains('button', 'Xác nhận đổi giá & Ghi lịch sử').click();

    cy.contains('Vui lòng nhập lý do điều chỉnh giá').should('be.visible');
  });

  it('TC_FR-B06_04: Đơn giá mới và lịch sử PriceHistory vẫn lưu bền vững sau khi tải lại trang (F5)', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.reload();
    cy.contains('tr', sku).should('contain.text', '68.000 ₫');
    cy.contains('tr', sku).contains('button', 'Đổi giá & Lịch sử').click();
    cy.get('.history-table-wrap').should('contain.text', 'Điều chỉnh giá mùa vụ E2E');
  });
});

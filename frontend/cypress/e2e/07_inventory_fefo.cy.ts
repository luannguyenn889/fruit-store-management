/**
 * Module: cypress/e2e/07_inventory_fefo.cy.ts
 * Nhiệm vụ: Kiểm thử E2E phân hệ Kho FEFO & Nhập hàng NCC (`/inventory`, `/procurement`)
 *           tương thích Cypress 16.2.1 (sử dụng `TEST_CONFIG` và `cy.loginByApi`).
 */

import { TEST_CONFIG } from '../support/constants';

describe('FR-C01..C09 - Quản lý Kho FEFO & Nhập hàng NCC (Cypress 16.2.1)', () => {
  it('TC_INV_01: Trang /inventory hiển thị KPI tồn kho, các tab FEFO/Sổ cái và menu kho đã mở khóa', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/inventory');

    cy.contains('h1', 'Tồn kho & Quản lý Lô hàng FEFO').should('be.visible');
    cy.contains('Tổng tồn khả dụng').should('be.visible');
    cy.contains('a.nav-item', 'Tồn kho & Lô hàng FEFO').should('not.have.class', 'disabled');
    cy.contains('a.nav-item', 'Nhập hàng NCC').should('not.have.class', 'disabled');

    cy.contains('button.tab-btn', 'Tồn kho theo Sản phẩm').click();
    cy.contains('button.tab-btn', 'Sổ cái biến động (Chỉ đọc)').click();
    cy.contains('button.tab-btn', 'Danh sách Lô hàng FEFO').click();
  });

  it('TC_INV_02: Lọc lô hàng theo trạng thái trên /inventory và xử lý lỗi 502 từ Inventory Service', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/inventory');

    cy.get('#lot-status-filter').select('NEAR_EXPIRY');
    cy.get('#lot-status-filter').should('have.value', 'NEAR_EXPIRY');
    cy.get('#lot-status-filter').select('');

    cy.intercept('GET', '**/api/v1/inventory/lots*', {
      statusCode: 502,
      body: {
        code: 'UPSTREAM_UNAVAILABLE',
        message: "Dịch vụ 'inventory-service' hiện không phản hồi.",
      },
    }).as('inventoryDown');

    cy.contains('button', 'Làm mới dữ liệu').click();
    cy.wait('@inventoryDown');
    cy.contains("Dịch vụ 'inventory-service' hiện không phản hồi.").should('be.visible');
  });

  it('TC_INV_03: Trang /procurement hiển thị tab Phiếu nhập kho, Nhà cung cấp và mở modal Lập phiếu nhập mới', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/procurement');

    cy.contains('h1', 'Nhà cung cấp & Nhập hàng NCC').should('be.visible');
    cy.get('#po-status-filter').select('RECEIVED');
    cy.get('#po-status-filter').should('have.value', 'RECEIVED');
    cy.get('#po-status-filter').select('');

    cy.contains('button.tab-btn', 'Nhà cung cấp').click();
    cy.contains('button', '+ Thêm nhà cung cấp').should('be.visible');

    cy.contains('button.tab-btn', 'Phiếu nhập kho').click();
    cy.contains('button', '+ Lập phiếu nhập mới').click();
    cy.get('#po-supplier-filter').should('exist');
  });
});

/**
 * Module: cypress/e2e/05_catalog_products.cy.ts
 * Nhiệm vụ: Kiểm thử E2E nhóm Danh mục, Sản phẩm & Dashboard dữ liệu thật (FR-B01, FR-B03,
 *           FR-B04, FR-B05, FR-B08) tại `/dashboard` và `/catalog`.
 */

import { TEST_CONFIG } from '../support/constants';

describe('FR-B01, B03, B04, B05, B08 - Dashboard & Quản lý Danh mục / Sản phẩm', () => {
  const ts = Date.now();
  const tempCatName = `Danh mục E2E ${ts}`;
  const tempSku = `E2E-FRT-${String(ts).slice(-5)}`;
  const tempProductName = `Chôm chôm nhãn E2E ${String(ts).slice(-4)}`;

  it('TC_FR-B01_01: Trang Dashboard hiển thị dữ liệu thật từ Catalog Service và làm mờ mục chưa triển khai', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/dashboard');

    cy.contains('SẢN PHẨM TRONG CATALOG').should('be.visible');
    cy.contains('DANH MỤC TRÁI CÂY').should('be.visible');
    cy.contains('Chưa có dữ liệu doanh thu để hiển thị').should('be.visible');
    cy.contains('a.nav-item.disabled', 'Bán hàng tại quầy POS').should('exist');
    cy.contains('a.nav-item', 'Danh mục Sản phẩm').should('not.have.class', 'disabled');
    cy.contains('a.nav-item', 'Cấu hình & Nhân sự').should('not.have.class', 'disabled');
  });

  it('TC_FR-B01_02: Tìm kiếm sản phẩm theo mã SKU và đặt lại bộ lọc trên /catalog', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.get('#search-sku-input').type('XOAI-HL-01');
    cy.contains('button', 'Tìm kiếm').click();
    cy.contains('td', 'XOAI-HL-01').should('be.visible');

    cy.contains('button', 'Đặt lại').click();
    cy.get('#search-sku-input').should('have.value', '');
    cy.get('table.catalog-table tbody tr').its('length').should('be.gte', 1);
  });

  it('TC_FR-B01_03: Lọc sản phẩm theo trạng thái kinh doanh ACTIVE', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.get('#filter-status-select').select('ACTIVE');
    cy.get('table.catalog-table tbody tr').should('have.length.at.least', 1);
    cy.get('table.catalog-table tbody tr').each($row => {
      cy.wrap($row).should('contain.text', 'Đang kinh doanh');
    });
  });

  it('TC_FR-B01_04: Hiển thị trạng thái lỗi trung thực và nút Thử tải lại khi Catalog Service trả 502', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.intercept('GET', '**/api/v1/catalog/products*', {
      statusCode: 502,
      body: {
        code: 'UPSTREAM_UNAVAILABLE',
        message: "Dịch vụ 'catalog-service' hiện không phản hồi.",
      },
    }).as('catalogDown');

    cy.visit('/catalog');
    cy.wait('@catalogDown');
    cy.contains('Chưa tải được dữ liệu sản phẩm').should('be.visible');
    cy.contains('button', 'Thử tải lại').should('be.visible');
  });

  it('TC_FR-B03_01: Manager tạo danh mục mới hợp lệ và xóa danh mục rỗng thành công', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('button', '+ Thêm danh mục').click();
    cy.get('#cat-name-input').type(tempCatName);
    cy.get('#cat-desc-input').type('Danh mục tạo tự động bởi Cypress E2E');
    cy.contains('button', 'Lưu danh mục').click();

    cy.contains(`Đã tạo danh mục "${tempCatName}" thành công.`).should('be.visible');
    cy.contains('.cat-pill-group', tempCatName).should('be.visible');

    // Xóa danh mục rỗng vừa tạo
    cy.contains('.cat-pill-group', tempCatName).find('button.cat-pill-delete').click();
    cy.contains('Xác nhận thực hiện').click();
    cy.contains('Đã xóa danh mục thành công.').should('be.visible');
  });

  it('TC_FR-B03_02: Tạo danh mục với tên dưới 2 ký tự hiển thị lỗi validation', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('button', '+ Thêm danh mục').click();
    cy.get('#cat-name-input').type('X');
    cy.contains('button', 'Lưu danh mục').click();
    cy.contains('Tên danh mục phải có tối thiểu 2 ký tự.').should('be.visible');
  });

  it('TC_FR-B03_03: Xóa danh mục đang chứa sản phẩm bị chặn với lỗi 409 CATEGORY_HAS_PRODUCTS', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('.cat-pill-group', 'Trái cây nội địa').find('button.cat-pill-delete').click();
    cy.contains('Xác nhận thực hiện').click();
    cy.contains('Không thể xóa danh mục').should('be.visible');
  });

  it('TC_FR-B04_01: Manager thêm sản phẩm mới với đơn vị hộp, bảo quản mát 2-8°C và hạn dùng gợi ý', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');
    cy.get('.cat-pill-group').should('have.length.at.least', 1);

    cy.contains('button', '+ Thêm sản phẩm mới').click();
    cy.get('#prod-sku-input').type(tempSku);
    cy.get('#prod-name-input').type(tempProductName);
    cy.get('#prod-unit-select').select('hop');
    cy.get('#prod-price-input').clear().type('75000');
    cy.get('#prod-origin-input').type('Chợ Lách, Bến Tre');
    cy.get('#prod-shelf-input').clear().type('5');
    cy.get('#prod-storage-select').select('COOL_2_8C');
    cy.get('.modal-panel button[type="submit"]').click();

    cy.contains(`Đã thêm sản phẩm "${tempProductName}"`).should('be.visible');
    cy.contains('tr', tempSku)
      .should('be.visible')
      .and('contain.text', '75.000 ₫')
      .and('contain.text', '/hộp')
      .and('contain.text', 'Mát 2–8°C')
      .and('contain.text', '5 ngày');
  });

  it('TC_FR-B04_02: Tạo sản phẩm trùng mã SKU đã tồn tại trả lỗi 409', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');
    cy.get('.cat-pill-group').should('have.length.at.least', 1);

    cy.contains('button', '+ Thêm sản phẩm mới').click();
    cy.get('#prod-sku-input').type(tempSku);
    cy.get('#prod-name-input').type('Sản phẩm trùng SKU');
    cy.get('#prod-price-input').clear().type('50000');
    cy.get('.modal-panel button[type="submit"]').click();

    cy.contains(`Mã SKU '${tempSku}' đã tồn tại`).should('be.visible');
  });

  it('TC_FR-B04_03: Tạo sản phẩm với đơn giá âm hiển thị lỗi validation', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');
    cy.get('.cat-pill-group').should('have.length.at.least', 1);

    cy.contains('button', '+ Thêm sản phẩm mới').click();
    cy.get('#prod-sku-input').type(`NEG-${String(ts).slice(-4)}`);
    cy.get('#prod-name-input').type('Sản phẩm giá âm');
    cy.get('#prod-price-input').clear().type('-5000');
    cy.get('.modal-panel button[type="submit"]').click();

    cy.contains('Đơn giá khởi tạo không hợp lệ').should('be.visible');
  });

  it('TC_FR-B04_04: Manager cập nhật thông tin sản phẩm (PATCH) - khóa ô SKU và Đơn giá', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('tr', tempSku).contains('button', 'Sửa').click();
    cy.get('#prod-sku-input').should('be.disabled');
    cy.get('#prod-price-input').should('be.disabled');
    cy.get('#prod-origin-input').clear().type('Cái Mơn, Bến Tre');
    cy.get('.modal-panel button[type="submit"]').click();

    cy.contains(`Đã cập nhật thông tin sản phẩm "${tempProductName}"`).should('be.visible');
    cy.contains('tr', tempSku).should('contain.text', 'Cái Mơn, Bến Tre');
  });

  it('TC_FR-B05_01: Manager ngừng kinh doanh sản phẩm (INACTIVE) có modal xác nhận', () => {
    cy.loginByApi(TEST_CONFIG.managerEmail, TEST_CONFIG.managerPassword);
    cy.visit('/catalog');

    cy.contains('tr', tempSku).contains('button', 'Ngừng bán').click();
    cy.contains(`Ngừng kinh doanh "${tempProductName}"`).should('be.visible');
    cy.contains('button', 'Xác nhận thực hiện').click();

    cy.contains('tr', tempSku).should('contain.text', 'Ngừng kinh doanh');
  });

  it('TC_FR-B05_02: Nhân viên STAFF vào /catalog chỉ được xem danh sách và lịch sử giá', () => {
    cy.loginByApi(TEST_CONFIG.staffEmail, TEST_CONFIG.staffPassword);
    cy.visit('/catalog');

    cy.contains('button', '+ Thêm sản phẩm mới').should('not.exist');
    cy.contains('button', '+ Thêm danh mục').should('not.exist');
    cy.get('table.catalog-table tbody tr')
      .first()
      .should('contain.text', 'Lịch sử giá')
      .and('not.contain.text', 'Ngừng bán');
  });
});

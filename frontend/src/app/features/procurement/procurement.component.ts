/**
 * Module: features/procurement/procurement.component.ts
 * Nhiệm vụ: Màn hình Quản lý Nhà cung cấp & Nhập hàng NCC (`/procurement`).
 *           - Hai tab: Nhà cung cấp (CRUD, tìm kiếm, lọc trạng thái, phân trang)
 *             và Phiếu nhập kho (lập phiếu nhiều dòng từ CatalogService, tự tính tổng,
 *             xem chi tiết, xác nhận nhập kho nguyên tử RECEIVED, hủy phiếu DRAFT).
 *           - Tuân thủ Skeleton Loading, Pagination, ToastService, không `alert()`.
 */

import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminLayoutComponent } from '../../core/layout/admin-layout/admin-layout.component';
import { AuthService } from '../../core/services/auth.service';
import { CatalogService, Product } from '../../core/services/catalog.service';
import {
  InventoryService,
  PurchaseItemCreatePayload,
  PurchaseOrder,
  Supplier
} from '../../core/services/inventory.service';
import { ToastService } from '../../core/services/toast.service';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';

export type ProcurementTab = 'purchase-orders' | 'suppliers';

export interface DraftPurchaseLine {
  product_id: string;
  quantity_ordered: string;
  unit_cost: string;
  expected_expiry_date: string;
}

@Component({
  selector: 'app-procurement',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AdminLayoutComponent,
    SkeletonLoaderComponent,
    PaginationComponent
  ],
  templateUrl: './procurement.component.html',
  styleUrls: ['./procurement.component.css']
})
export class ProcurementComponent implements OnInit {
  canManageProcurement = computed(() =>
    this.authService.hasRole('WAREHOUSE', 'MANAGER', 'ADMIN')
  );

  activeTab = signal<ProcurementTab>('purchase-orders');

  // Danh sách sản phẩm thật từ CatalogService
  products = signal<Product[]>([]);
  productMap = computed(() => {
    const map = new Map<string, Product>();
    for (const p of this.products()) {
      map.set(p.id, p);
    }
    return map;
  });

  // ===========================================================================
  // TAB 1: NHÀ CUNG CẤP (SUPPLIERS)
  // ===========================================================================
  suppliers = signal<Supplier[]>([]);
  activeSuppliers = signal<Supplier[]>([]);
  totalSuppliers = signal(0);
  suppliersPage = signal(1);
  suppliersPageSize = signal(20);
  suppliersTotalPages = signal(1);
  isLoadingSuppliers = signal(false);
  suppliersError = signal('');

  supplierSearchQuery = '';
  supplierActiveFilter = '';

  // Modal Tạo / Sửa NCC
  showSupplierModal = signal(false);
  isEditingSupplier = signal(false);
  editingSupplierId = signal<string | null>(null);
  isSavingSupplier = signal(false);

  formSupplierCode = '';
  formSupplierName = '';
  formSupplierPhone = '';
  formSupplierAddress = '';
  formSupplierActive = true;

  // ===========================================================================
  // TAB 2: PHIẾU NHẬP KHO (PURCHASE ORDERS)
  // ===========================================================================
  purchaseOrders = signal<PurchaseOrder[]>([]);
  totalPOs = signal(0);
  poPage = signal(1);
  poPageSize = signal(20);
  poTotalPages = signal(1);
  isLoadingPOs = signal(false);
  poError = signal('');

  poStatusFilter = '';
  poSupplierFilter = '';
  poFromDate = '';
  poToDate = '';

  // Modal Xem chi tiết Phiếu nhập
  showPODetailModal = signal(false);
  selectedPO = signal<PurchaseOrder | null>(null);
  isLoadingPODetail = signal(false);

  // Modal Lập Phiếu nhập mới
  showCreatePOModal = signal(false);
  isSavingPO = signal(false);
  poSupplierId = '';
  poLines: DraftPurchaseLine[] = [];

  // Modal Xác nhận Nhập kho / Hủy phiếu
  showConfirmModal = signal(false);
  confirmAction = signal<'receive' | 'cancel' | null>(null);
  confirmTargetPO = signal<PurchaseOrder | null>(null);
  confirmReceivedDate = '';
  isProcessingConfirm = signal(false);

  constructor(
    public authService: AuthService,
    private inventoryService: InventoryService,
    private catalogService: CatalogService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.loadCatalogProducts();
    this.loadActiveSuppliers();
    this.loadPurchaseOrders(1);
    this.loadSuppliers(1);
  }

  switchTab(tab: ProcurementTab): void {
    this.activeTab.set(tab);
  }

  loadCatalogProducts(): void {
    this.catalogService.getProducts({ page: 1, size: 100, status: 'ACTIVE' }).subscribe({
      next: res => this.products.set(res.items),
      error: () => {
        // Bỏ qua nếu catalog tạm thời lỗi; người dùng vẫn có thể tải lại
      }
    });
  }

  loadActiveSuppliers(): void {
    this.inventoryService.getSuppliers({ is_active: true, page: 1, limit: 100 }).subscribe({
      next: res => this.activeSuppliers.set(res.items),
      error: () => {}
    });
  }

  // ===========================================================================
  // QUẢN LÝ NHÀ CUNG CẤP
  // ===========================================================================
  loadSuppliers(page = 1): void {
    this.isLoadingSuppliers.set(true);
    this.suppliersError.set('');
    this.suppliersPage.set(page);

    const isActiveParam =
      this.supplierActiveFilter === ''
        ? null
        : this.supplierActiveFilter === 'true';

    this.inventoryService
      .getSuppliers({
        q: this.supplierSearchQuery,
        is_active: isActiveParam,
        page,
        limit: this.suppliersPageSize()
      })
      .subscribe({
        next: res => {
          this.suppliers.set(res.items);
          this.totalSuppliers.set(res.total);
          this.suppliersTotalPages.set(Math.max(1, res.pages));
          this.isLoadingSuppliers.set(false);
        },
        error: err => {
          this.suppliersError.set(
            err?.error?.message || err?.error?.detail || 'Không thể tải danh sách nhà cung cấp.'
          );
          this.isLoadingSuppliers.set(false);
        }
      });
  }

  applySupplierFilters(): void {
    this.loadSuppliers(1);
  }

  resetSupplierFilters(): void {
    this.supplierSearchQuery = '';
    this.supplierActiveFilter = '';
    this.loadSuppliers(1);
  }

  openCreateSupplierModal(): void {
    this.isEditingSupplier.set(false);
    this.editingSupplierId.set(null);
    this.formSupplierCode = '';
    this.formSupplierName = '';
    this.formSupplierPhone = '';
    this.formSupplierAddress = '';
    this.formSupplierActive = true;
    this.showSupplierModal.set(true);
  }

  openEditSupplierModal(supplier: Supplier): void {
    this.isEditingSupplier.set(true);
    this.editingSupplierId.set(supplier.id);
    this.formSupplierCode = supplier.code;
    this.formSupplierName = supplier.name;
    this.formSupplierPhone = supplier.phone || '';
    this.formSupplierAddress = supplier.address || '';
    this.formSupplierActive = supplier.is_active;
    this.showSupplierModal.set(true);
  }

  closeSupplierModal(): void {
    if (this.isSavingSupplier()) return;
    this.showSupplierModal.set(false);
  }

  submitSupplier(): void {
    const cleanName = this.formSupplierName.trim();
    if (!cleanName) {
      this.toastService.warning('Vui lòng nhập tên nhà cung cấp.');
      return;
    }

    const cleanCode = this.formSupplierCode.trim().toUpperCase();
    if (cleanCode && !/^NCC-[A-Z0-9][A-Z0-9_-]*$/.test(cleanCode)) {
      this.toastService.warning('Mã nhà cung cấp phải bắt đầu bằng NCC- (ví dụ: NCC-001).');
      return;
    }

    this.isSavingSupplier.set(true);

    if (this.isEditingSupplier() && this.editingSupplierId()) {
      this.inventoryService
        .updateSupplier(this.editingSupplierId()!, {
          code: cleanCode || undefined,
          name: cleanName,
          phone: this.formSupplierPhone.trim() || undefined,
          address: this.formSupplierAddress.trim() || undefined,
          is_active: this.formSupplierActive
        })
        .subscribe({
          next: updated => {
            this.isSavingSupplier.set(false);
            this.showSupplierModal.set(false);
            this.toastService.success(`Đã cập nhật nhà cung cấp ${updated.code}.`);
            this.loadSuppliers(this.suppliersPage());
            this.loadActiveSuppliers();
          },
          error: err => {
            this.isSavingSupplier.set(false);
            this.toastService.error(this.extractErrorMessage(err, 'Không thể cập nhật nhà cung cấp.'));
          }
        });
    } else {
      this.inventoryService
        .createSupplier({
          code: cleanCode || undefined,
          name: cleanName,
          phone: this.formSupplierPhone.trim() || undefined,
          address: this.formSupplierAddress.trim() || undefined,
          is_active: this.formSupplierActive
        })
        .subscribe({
          next: created => {
            this.isSavingSupplier.set(false);
            this.showSupplierModal.set(false);
            this.toastService.success(`Đã thêm nhà cung cấp ${created.code} - ${created.name}.`);
            this.loadSuppliers(1);
            this.loadActiveSuppliers();
          },
          error: err => {
            this.isSavingSupplier.set(false);
            this.toastService.error(this.extractErrorMessage(err, 'Không thể tạo nhà cung cấp mới.'));
          }
        });
    }
  }

  // ===========================================================================
  // QUẢN LÝ PHIẾU NHẬP KHO
  // ===========================================================================
  loadPurchaseOrders(page = 1): void {
    this.isLoadingPOs.set(true);
    this.poError.set('');
    this.poPage.set(page);

    this.inventoryService
      .getPurchaseOrders({
        status: this.poStatusFilter || undefined,
        supplier_id: this.poSupplierFilter || undefined,
        from_date: this.poFromDate || undefined,
        to_date: this.poToDate || undefined,
        page,
        limit: this.poPageSize()
      })
      .subscribe({
        next: res => {
          this.purchaseOrders.set(res.items);
          this.totalPOs.set(res.total);
          this.poTotalPages.set(Math.max(1, res.pages));
          this.isLoadingPOs.set(false);
        },
        error: err => {
          this.poError.set(
            err?.error?.message || err?.error?.detail || 'Không thể tải danh sách phiếu nhập kho.'
          );
          this.isLoadingPOs.set(false);
        }
      });
  }

  applyPOFilters(): void {
    this.loadPurchaseOrders(1);
  }

  resetPOFilters(): void {
    this.poStatusFilter = '';
    this.poSupplierFilter = '';
    this.poFromDate = '';
    this.poToDate = '';
    this.loadPurchaseOrders(1);
  }

  openPODetailModal(po: PurchaseOrder): void {
    this.selectedPO.set(po);
    this.showPODetailModal.set(true);
    this.isLoadingPODetail.set(true);

    this.inventoryService.getPurchaseOrderById(po.id).subscribe({
      next: detail => {
        this.selectedPO.set(detail);
        this.isLoadingPODetail.set(false);
      },
      error: () => {
        this.isLoadingPODetail.set(false);
      }
    });
  }

  closePODetailModal(): void {
    this.showPODetailModal.set(false);
    this.selectedPO.set(null);
  }

  // ===========================================================================
  // LẬP PHIẾU NHẬP KHO MỚI (FR-C02)
  // ===========================================================================
  openCreatePOModal(): void {
    this.poSupplierId = this.activeSuppliers()[0]?.id || '';
    this.poLines = [this.createEmptyLine()];
    this.showCreatePOModal.set(true);
  }

  closeCreatePOModal(): void {
    if (this.isSavingPO()) return;
    this.showCreatePOModal.set(false);
  }

  createEmptyLine(): DraftPurchaseLine {
    return {
      product_id: '',
      quantity_ordered: '10.000',
      unit_cost: '0',
      expected_expiry_date: this.getDefaultExpiryDate(7)
    };
  }

  addPOLine(): void {
    this.poLines = [...this.poLines, this.createEmptyLine()];
  }

  removePOLine(index: number): void {
    if (this.poLines.length <= 1) {
      this.toastService.warning('Phiếu nhập phải có ít nhất 1 dòng sản phẩm.');
      return;
    }
    this.poLines = this.poLines.filter((_, idx) => idx !== index);
  }

  onProductLineChange(index: number): void {
    const line = this.poLines[index];
    const prod = this.productMap().get(line.product_id);
    if (prod) {
      line.expected_expiry_date = this.getDefaultExpiryDate(prod.default_shelf_life_days || 7);
    }
  }

  computeLineTotal(line: DraftPurchaseLine): number {
    const qty = Number(line.quantity_ordered);
    const cost = Number(line.unit_cost);
    if (Number.isNaN(qty) || Number.isNaN(cost) || qty < 0 || cost < 0) return 0;
    return qty * cost;
  }

  computePOGrandTotal(): number {
    return this.poLines.reduce((sum, line) => sum + this.computeLineTotal(line), 0);
  }

  submitCreatePO(): void {
    if (!this.poSupplierId) {
      this.toastService.warning('Vui lòng chọn nhà cung cấp.');
      return;
    }

    const itemsPayload: PurchaseItemCreatePayload[] = [];
    for (let i = 0; i < this.poLines.length; i++) {
      const line = this.poLines[i];
      if (!line.product_id) {
        this.toastService.warning(`Dòng ${i + 1}: Vui lòng chọn sản phẩm.`);
        return;
      }
      const qty = Number(line.quantity_ordered);
      if (!line.quantity_ordered || Number.isNaN(qty) || qty <= 0) {
        this.toastService.warning(`Dòng ${i + 1}: Số lượng đặt nhập phải lớn hơn 0.`);
        return;
      }
      const cost = Number(line.unit_cost);
      if (line.unit_cost === '' || Number.isNaN(cost) || cost < 0) {
        this.toastService.warning(`Dòng ${i + 1}: Đơn giá vốn không được âm.`);
        return;
      }

      itemsPayload.push({
        product_id: line.product_id,
        quantity_ordered: String(line.quantity_ordered).trim(),
        unit_cost: String(line.unit_cost).trim(),
        expected_expiry_date: line.expected_expiry_date || undefined
      });
    }

    this.isSavingPO.set(true);
    this.inventoryService
      .createPurchaseOrder({
        supplier_id: this.poSupplierId,
        items: itemsPayload
      })
      .subscribe({
        next: created => {
          this.isSavingPO.set(false);
          this.showCreatePOModal.set(false);
          this.toastService.success(
            `Đã lập phiếu nhập nháp ${created.po_number} (${created.items.length} dòng).`
          );
          this.loadPurchaseOrders(1);
        },
        error: err => {
          this.isSavingPO.set(false);
          this.toastService.error(this.extractErrorMessage(err, 'Không thể lập phiếu nhập kho.'));
        }
      });
  }

  // ===========================================================================
  // XÁC NHẬN NHẬP KHO (RECEIVE) & HỦY PHIẾU (CANCEL)
  // ===========================================================================
  openReceiveConfirm(po: PurchaseOrder): void {
    this.confirmAction.set('receive');
    this.confirmTargetPO.set(po);
    this.confirmReceivedDate = new Date().toISOString().slice(0, 10);
    this.showConfirmModal.set(true);
  }

  openCancelConfirm(po: PurchaseOrder): void {
    this.confirmAction.set('cancel');
    this.confirmTargetPO.set(po);
    this.showConfirmModal.set(true);
  }

  closeConfirmModal(): void {
    if (this.isProcessingConfirm()) return;
    this.showConfirmModal.set(false);
    this.confirmTargetPO.set(null);
    this.confirmAction.set(null);
  }

  executeConfirmAction(): void {
    const po = this.confirmTargetPO();
    const action = this.confirmAction();
    if (!po || !action || this.isProcessingConfirm()) return;

    this.isProcessingConfirm.set(true);

    if (action === 'receive') {
      this.inventoryService
        .receivePurchaseOrder(po.id, {
          received_date: this.confirmReceivedDate || undefined
        })
        .subscribe({
          next: res => {
            this.isProcessingConfirm.set(false);
            this.showConfirmModal.set(false);
            this.toastService.success(
              `Đã nhập kho phiếu ${res.purchase_order.po_number} và sinh ${res.created_lots.length} lô hàng FEFO mới.`
            );
            this.loadPurchaseOrders(this.poPage());
            if (this.selectedPO()?.id === po.id) {
              this.selectedPO.set(res.purchase_order);
            }
          },
          error: err => {
            this.isProcessingConfirm.set(false);
            this.toastService.error(
              this.extractErrorMessage(err, 'Không thể xác nhận nhập kho phiếu này.')
            );
          }
        });
    } else {
      this.inventoryService.cancelPurchaseOrder(po.id).subscribe({
        next: updated => {
          this.isProcessingConfirm.set(false);
          this.showConfirmModal.set(false);
          this.toastService.success(`Đã hủy phiếu nhập ${updated.po_number}.`);
          this.loadPurchaseOrders(this.poPage());
          if (this.selectedPO()?.id === po.id) {
            this.selectedPO.set(updated);
          }
        },
        error: err => {
          this.isProcessingConfirm.set(false);
          this.toastService.error(this.extractErrorMessage(err, 'Không thể hủy phiếu nhập.'));
        }
      });
    }
  }

  // ===========================================================================
  // TIỆN ÍCH ĐỊNH DẠNG
  // ===========================================================================
  getProductName(productId: string): string {
    const prod = this.productMap().get(productId);
    return prod ? `${prod.name} (${prod.sku})` : `SP #${productId.slice(0, 8)}`;
  }

  formatPOStatusLabel(status: string): string {
    switch (status) {
      case 'DRAFT':
        return 'Phiếu nháp';
      case 'RECEIVED':
        return 'Đã nhập kho';
      case 'CANCELLED':
        return 'Đã hủy';
      default:
        return status;
    }
  }

  formatVnd(value: string | number | null | undefined): string {
    const num = Number(value ?? 0);
    if (Number.isNaN(num)) return '0 đ';
    return `${Math.round(num).toLocaleString('vi-VN')} đ`;
  }

  formatQty(value: string | number | null | undefined): string {
    const num = Number(value ?? 0);
    if (Number.isNaN(num)) return '0';
    return num.toLocaleString('vi-VN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3
    });
  }

  private getDefaultExpiryDate(daysFromToday: number): string {
    const d = new Date();
    d.setDate(d.getDate() + Math.max(1, daysFromToday));
    return d.toISOString().slice(0, 10);
  }

  private extractErrorMessage(err: any, fallback: string): string {
    if (err?.status === 409) {
      return err?.error?.message || err?.error?.detail || 'Mã nhà cung cấp đã tồn tại trong hệ thống.';
    }
    return err?.error?.message || err?.error?.detail || fallback;
  }
}

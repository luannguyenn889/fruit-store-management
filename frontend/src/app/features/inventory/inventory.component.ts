/**
 * Module: features/inventory/inventory.component.ts
 * Nhiệm vụ: Màn hình Quản lý Tồn kho & Lô hàng FEFO (`/inventory`).
 *           - Tổng hợp tồn kho theo sản phẩm (`GET /stock/summary`) và cảnh báo lô cận hạn/quá hạn.
 *           - Danh sách lô hàng FEFO kèm bộ lọc (sản phẩm, trạng thái, hạn dùng) và phân trang.
 *           - Sổ cái biến động kho chỉ đọc (`GET /movements`) với bộ lọc & phân trang.
 *           - Modal Ghi nhận hao hụt (`POST /lots/{id}/wastage`) & Điều chỉnh kiểm kê (`POST /lots/{id}/adjust`)
 *             có bước xác nhận trước khi lưu, chặn số âm và phản hồi bằng `ToastService`.
 */

import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminLayoutComponent } from '../../core/layout/admin-layout/admin-layout.component';
import { AuthService } from '../../core/services/auth.service';
import { CatalogService, Product } from '../../core/services/catalog.service';
import {
  ExpiringLotsResponse,
  InventoryService,
  StockLot,
  StockMovement,
  StockSummaryResponse,
  WastageReasonType
} from '../../core/services/inventory.service';
import { ToastService } from '../../core/services/toast.service';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';

export type InventoryTab = 'lots' | 'summary' | 'movements';
export type LotActionMode = 'wastage' | 'adjust';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AdminLayoutComponent,
    SkeletonLoaderComponent,
    PaginationComponent
  ],
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.css']
})
export class InventoryComponent implements OnInit {
  // Phân quyền: WAREHOUSE, MANAGER, ADMIN được ghi hao hụt/điều chỉnh; STAFF chỉ đọc
  canWriteInventory = computed(() =>
    this.authService.hasRole('WAREHOUSE', 'MANAGER', 'ADMIN')
  );

  // Tab đang chọn
  activeTab = signal<InventoryTab>('lots');

  // Danh sách sản phẩm từ CatalogService để hiển thị tên/SKU thay cho UUID
  products = signal<Product[]>([]);
  productMap = computed(() => {
    const map = new Map<string, Product>();
    for (const p of this.products()) {
      map.set(p.id, p);
    }
    return map;
  });

  // Dữ liệu tổng hợp tồn kho & cảnh báo hạn dùng
  stockSummary = signal<StockSummaryResponse | null>(null);
  isLoadingSummary = signal(false);
  summaryError = signal('');

  expiringData = signal<ExpiringLotsResponse | null>(null);

  // Dữ liệu bảng Lô hàng FEFO
  lots = signal<StockLot[]>([]);
  totalLots = signal(0);
  lotsPage = signal(1);
  lotsPageSize = signal(20);
  lotsTotalPages = signal(1);
  isLoadingLots = signal(false);
  lotsError = signal('');

  // Bộ lọc Lô hàng
  filterProductId = '';
  filterStatus = '';
  filterExpiry = '';

  // Dữ liệu Sổ cái biến động (chỉ đọc)
  movements = signal<StockMovement[]>([]);
  totalMovements = signal(0);
  movementsPage = signal(1);
  movementsPageSize = signal(20);
  movementsTotalPages = signal(1);
  isLoadingMovements = signal(false);
  movementsError = signal('');

  // Bộ lọc Sổ cái
  movementProductId = '';
  movementType = '';
  movementFromDate = '';
  movementToDate = '';

  // Modal Hao hụt / Điều chỉnh kiểm kê
  showLotActionModal = signal(false);
  lotActionMode = signal<LotActionMode>('wastage');
  selectedLot = signal<StockLot | null>(null);
  confirmStep = signal(false);
  isSubmittingAction = signal(false);

  // Trường form Hao hụt
  wastageQuantity = '';
  wastageReasonType: WastageReasonType = 'WASTE_DAMAGED';
  wastageNote = '';

  // Trường form Điều chỉnh kiểm kê
  adjustActualQuantity = '';
  adjustReason = '';

  constructor(
    public authService: AuthService,
    private inventoryService: InventoryService,
    private catalogService: CatalogService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.loadCatalogProducts();
    this.refreshAll();
  }

  refreshAll(): void {
    this.loadStockSummary();
    this.loadExpiringLots();
    this.loadLots(1);
    if (this.activeTab() === 'movements') {
      this.loadMovements(1);
    }
  }

  switchTab(tab: InventoryTab): void {
    this.activeTab.set(tab);
    if (tab === 'movements' && this.movements().length === 0 && !this.isLoadingMovements()) {
      this.loadMovements(1);
    }
    if (tab === 'summary' && !this.stockSummary() && !this.isLoadingSummary()) {
      this.loadStockSummary();
    }
  }

  loadCatalogProducts(): void {
    this.catalogService.getProducts({ page: 1, size: 100 }).subscribe({
      next: res => this.products.set(res.items),
      error: () => {
        // Không chặn luồng chính nếu catalog tạm chậm; UI vẫn hiển thị fallback ID ngắn
      }
    });
  }

  loadStockSummary(): void {
    this.isLoadingSummary.set(true);
    this.summaryError.set('');
    this.inventoryService.getStockSummary().subscribe({
      next: res => {
        this.stockSummary.set(res);
        this.isLoadingSummary.set(false);
      },
      error: err => {
        this.summaryError.set(
          err?.error?.message || err?.error?.detail || 'Không thể tải tổng hợp tồn kho.'
        );
        this.isLoadingSummary.set(false);
      }
    });
  }

  loadExpiringLots(): void {
    this.inventoryService.getExpiringLots(3).subscribe({
      next: res => this.expiringData.set(res),
      error: () => {
        // Bỏ qua lỗi phụ ở banner cảnh báo nếu bảng chính đã xử lý lỗi
      }
    });
  }

  loadLots(page = 1): void {
    this.isLoadingLots.set(true);
    this.lotsError.set('');
    this.lotsPage.set(page);

    // Nếu người dùng chọn lọc nhanh theo hạn dùng, ánh xạ sang tham số phù hợp
    if (this.filterExpiry === 'NEAR_EXPIRY_3D' || this.filterExpiry === 'EXPIRED_ONLY') {
      this.inventoryService.getExpiringLots(3).subscribe({
        next: res => {
          const rawList =
            this.filterExpiry === 'NEAR_EXPIRY_3D'
              ? res.near_expiry_lots
              : res.expired_lots;
          const filtered = rawList.filter(lot => {
            if (this.filterProductId && lot.product_id !== this.filterProductId) {
              return false;
            }
            if (this.filterStatus && lot.status !== this.filterStatus) {
              return false;
            }
            return true;
          });
          this.lots.set(filtered);
          this.totalLots.set(filtered.length);
          this.lotsTotalPages.set(1);
          this.isLoadingLots.set(false);
        },
        error: err => {
          this.lotsError.set(
            err?.error?.message || err?.error?.detail || 'Không thể tải danh sách lô sắp hết hạn.'
          );
          this.isLoadingLots.set(false);
        }
      });
      return;
    }

    this.inventoryService
      .getLots({
        product_id: this.filterProductId || undefined,
        status: this.filterStatus || undefined,
        page,
        limit: this.lotsPageSize()
      })
      .subscribe({
        next: res => {
          this.lots.set(res.items);
          this.totalLots.set(res.total);
          this.lotsTotalPages.set(Math.max(1, res.pages));
          this.isLoadingLots.set(false);
        },
        error: err => {
          this.lotsError.set(
            err?.error?.message || err?.error?.detail || 'Không thể tải danh sách lô hàng FEFO.'
          );
          this.isLoadingLots.set(false);
        }
      });
  }

  applyLotFilters(): void {
    this.loadLots(1);
  }

  resetLotFilters(): void {
    this.filterProductId = '';
    this.filterStatus = '';
    this.filterExpiry = '';
    this.loadLots(1);
  }

  loadMovements(page = 1): void {
    this.isLoadingMovements.set(true);
    this.movementsError.set('');
    this.movementsPage.set(page);

    this.inventoryService
      .getMovements({
        product_id: this.movementProductId || undefined,
        movement_type: this.movementType || undefined,
        from_date: this.movementFromDate || undefined,
        to_date: this.movementToDate || undefined,
        page,
        limit: this.movementsPageSize()
      })
      .subscribe({
        next: res => {
          this.movements.set(res.items);
          this.totalMovements.set(res.total);
          this.movementsTotalPages.set(Math.max(1, res.pages));
          this.isLoadingMovements.set(false);
        },
        error: err => {
          this.movementsError.set(
            err?.error?.message || err?.error?.detail || 'Không thể tải sổ cái biến động kho.'
          );
          this.isLoadingMovements.set(false);
        }
      });
  }

  applyMovementFilters(): void {
    this.loadMovements(1);
  }

  resetMovementFilters(): void {
    this.movementProductId = '';
    this.movementType = '';
    this.movementFromDate = '';
    this.movementToDate = '';
    this.loadMovements(1);
  }

  // ===========================================================================
  // MODAL HAO HỤT / ĐIỀU CHỈNH KIỂM KÊ (FR-C07, FR-C08, BR-02)
  // ===========================================================================
  openLotActionModal(lot: StockLot, mode: LotActionMode): void {
    this.selectedLot.set(lot);
    this.lotActionMode.set(mode);
    this.confirmStep.set(false);
    this.isSubmittingAction.set(false);

    if (mode === 'wastage') {
      this.wastageQuantity = '';
      this.wastageReasonType = lot.is_expired ? 'WASTE_EXPIRED' : 'WASTE_DAMAGED';
      this.wastageNote = '';
    } else {
      this.adjustActualQuantity = lot.quantity_remaining;
      this.adjustReason = '';
    }

    this.showLotActionModal.set(true);
  }

  closeLotActionModal(): void {
    if (this.isSubmittingAction()) return;
    this.showLotActionModal.set(false);
    this.selectedLot.set(null);
    this.confirmStep.set(false);
  }

  proceedToConfirmStep(): void {
    const lot = this.selectedLot();
    if (!lot) return;

    if (this.lotActionMode() === 'wastage') {
      const qty = Number(this.wastageQuantity);
      if (!this.wastageQuantity || Number.isNaN(qty) || qty <= 0) {
        this.toastService.warning('Số lượng hao hụt phải lớn hơn 0.');
        return;
      }
      const available = Number(lot.available_quantity);
      if (qty > available) {
        this.toastService.warning(
          `Số lượng hao hụt (${qty}) vượt quá tồn khả dụng của lô (${available} kg).`
        );
        return;
      }
      if (!this.wastageReasonType) {
        this.toastService.warning('Vui lòng chọn lý do hao hụt.');
        return;
      }
      if (!this.wastageNote.trim()) {
        this.toastService.warning('Vui lòng nhập ghi chú chi tiết cho phiếu hao hụt.');
        return;
      }
    } else {
      const actual = Number(this.adjustActualQuantity);
      if (this.adjustActualQuantity === '' || Number.isNaN(actual) || actual < 0) {
        this.toastService.warning('Số lượng thực tế sau kiểm kê không được âm.');
        return;
      }
      const reserved = Number(lot.quantity_reserved);
      if (actual < reserved) {
        this.toastService.warning(
          `Số lượng thực tế (${actual}) không thể nhỏ hơn lượng đang giữ (${reserved}).`
        );
        return;
      }
      if (!this.adjustReason.trim()) {
        this.toastService.warning('Vui lòng nhập lý do điều chỉnh kiểm kê.');
        return;
      }
    }

    this.confirmStep.set(true);
  }

  backToEditStep(): void {
    this.confirmStep.set(false);
  }

  submitLotAction(): void {
    const lot = this.selectedLot();
    if (!lot || this.isSubmittingAction()) return;

    this.isSubmittingAction.set(true);

    if (this.lotActionMode() === 'wastage') {
      this.inventoryService
        .recordWastage(lot.id, {
          quantity: String(this.wastageQuantity).trim(),
          reason_type: this.wastageReasonType,
          note: this.wastageNote.trim()
        })
        .subscribe({
          next: updated => {
            this.isSubmittingAction.set(false);
            this.showLotActionModal.set(false);
            this.toastService.success(
              `Đã ghi nhận hao hụt cho lô ${updated.lot_code}. Tồn còn lại: ${this.formatQty(updated.quantity_remaining)}.`
            );
            this.refreshAll();
          },
          error: err => {
            this.isSubmittingAction.set(false);
            this.toastService.error(
              err?.error?.message || err?.error?.detail || 'Không thể ghi nhận hao hụt lô hàng.'
            );
          }
        });
    } else {
      this.inventoryService
        .adjustStock(lot.id, {
          actual_quantity: String(this.adjustActualQuantity).trim(),
          reason: this.adjustReason.trim()
        })
        .subscribe({
          next: updated => {
            this.isSubmittingAction.set(false);
            this.showLotActionModal.set(false);
            this.toastService.success(
              `Đã điều chỉnh kiểm kê lô ${updated.lot_code}. Tồn mới: ${this.formatQty(updated.quantity_remaining)}.`
            );
            this.refreshAll();
          },
          error: err => {
            this.isSubmittingAction.set(false);
            this.toastService.error(
              err?.error?.message || err?.error?.detail || 'Không thể điều chỉnh kiểm kê lô hàng.'
            );
          }
        });
    }
  }

  // ===========================================================================
  // HÀM ĐỊNH DẠNG HIỂN THỊ TIẾNG VIỆT
  // ===========================================================================
  getProductName(productId: string): string {
    const prod = this.productMap().get(productId);
    return prod ? prod.name : `SP #${productId.slice(0, 8)}`;
  }

  getProductSku(productId: string): string {
    return this.productMap().get(productId)?.sku || '';
  }

  getProductUnit(productId: string): string {
    const unit = this.productMap().get(productId)?.unit;
    if (unit === 'hop') return 'hộp';
    if (unit === 'qua') return 'quả';
    return 'kg';
  }

  formatQty(value: string | number | null | undefined): string {
    const num = Number(value ?? 0);
    if (Number.isNaN(num)) return '0';
    return num.toLocaleString('vi-VN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3
    });
  }

  formatVnd(value: string | number | null | undefined): string {
    const num = Number(value ?? 0);
    if (Number.isNaN(num)) return '0 đ';
    return `${Math.round(num).toLocaleString('vi-VN')} đ`;
  }

  formatLotStatusLabel(status: string): string {
    switch (status) {
      case 'AVAILABLE':
        return 'Còn hạn';
      case 'NEAR_EXPIRY':
        return 'Cận hạn';
      case 'EXPIRED':
        return 'Đã hết hạn';
      case 'DEPLETED':
        return 'Đã hết hàng';
      default:
        return status;
    }
  }

  formatExpiryCountdown(lot: StockLot): string {
    if (lot.is_expired || lot.days_until_expiry < 0) {
      const overdue = Math.abs(lot.days_until_expiry);
      return overdue === 0 ? 'Hết hạn hôm nay' : `Quá hạn ${overdue} ngày`;
    }
    if (lot.days_until_expiry === 0) return 'Hết hạn hôm nay';
    return `Còn ${lot.days_until_expiry} ngày`;
  }

  formatMovementTypeLabel(type: string): string {
    switch (type) {
      case 'IN':
        return 'Nhập kho';
      case 'SALE_OUT':
        return 'Xuất bán';
      case 'RESERVE':
        return 'Giữ hàng';
      case 'RELEASE':
        return 'Hoàn giữ';
      case 'WASTE_EXPIRED':
        return 'Hao hụt hết hạn';
      case 'WASTE_DAMAGED':
        return 'Hao hụt hư hỏng';
      case 'ADJUSTMENT':
        return 'Điều chỉnh kiểm kê';
      default:
        return type;
    }
  }

  isPositiveMovement(quantityChange: string): boolean {
    return Number(quantityChange) > 0;
  }
}

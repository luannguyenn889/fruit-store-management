/**
 * Module: features/catalog/catalog.component.ts
 * Nhiệm vụ: Màn hình Quản lý Danh mục, Sản phẩm Trái cây & Lịch sử Đơn giá (Catalog Management UI).
 *           Tuân thủ nghiêm ngặt `FRONTEND_DESIGN_RULES.md` và `UI_UX_DESIGN_RULES_FruitStore.md`:
 *           - Dùng `ToastService` toàn cục cho phản hồi thành công/lỗi thay thế hộp alert nội tuyến.
 *           - Dùng `SkeletonLoaderComponent` cho trạng thái đang tải bảng sản phẩm và lịch sử giá.
 *           - Tách biệt hoàn toàn thao tác "Sửa thông tin sản phẩm" (`PATCH`) với "Điều chỉnh đơn giá"
 *             (`POST /products/{id}/price`) để đảm bảo mọi biến động giá đều lưu vết `PriceHistory`.
 */

import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, User } from '../../core/services/auth.service';
import {
  CatalogService,
  Category,
  PriceHistoryRecord,
  Product,
  ProductStatus,
  ProductUnit,
  StorageCondition
} from '../../core/services/catalog.service';
import { ToastService } from '../../core/services/toast.service';
import { AdminLayoutComponent } from '../../core/layout/admin-layout/admin-layout.component';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';

@Component({
  selector: 'app-catalog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AdminLayoutComponent,
    SkeletonLoaderComponent,
    PaginationComponent
  ],
  templateUrl: './catalog.component.html',
  styleUrls: ['./catalog.component.css']
})
export class CatalogComponent implements OnInit {
  // Trạng thái người dùng & phân quyền
  currentUser = signal<User | null>(null);
  canManageCatalog = computed(() =>
    this.authService.hasRole('MANAGER', 'ADMIN')
  );

  // Dữ liệu Danh mục & Sản phẩm từ Backend
  categories = signal<Category[]>([]);
  products = signal<Product[]>([]);
  totalProducts = signal(0);
  currentPage = signal(1);
  pageSize = signal(20);
  totalPages = signal(1);

  // Bộ lọc tìm kiếm đặt sát bảng dữ liệu
  searchQuery = '';
  selectedCategoryId = '';
  selectedStatus = '';

  // Trạng thái bất đồng bộ trung thực (Honest UI)
  isLoading = signal(false);
  loadError = signal('');

  // Modal Tạo Danh Mục
  showCategoryModal = signal(false);
  isSavingCategory = signal(false);
  newCategoryName = '';
  newCategoryDesc = '';

  // Modal Thêm / Sửa Sản Phẩm
  showProductModal = signal(false);
  isEditingProduct = signal(false);
  editingProductId = signal<string | null>(null);
  isSavingProduct = signal(false);

  formCategoryId = '';
  formSku = '';
  formName = '';
  formUnit: ProductUnit = 'kg';
  formPrice = '65000';
  formOrigin = '';
  formShelfLifeDays = 7;
  formStorageCondition: StorageCondition = 'COOL_2_8C';
  formStatus: ProductStatus = 'ACTIVE';
  formDescription = '';

  // Hình ảnh đại diện sản phẩm (FR-B07)
  selectedImageFile = signal<File | null>(null);
  imagePreviewUrl = signal<string | null>(null);
  isDeletingImage = signal(false);

  // Modal Điều chỉnh Đơn giá & Lịch sử Giá (PriceHistory - FR-B06, BR-07)
  showPriceModal = signal(false);
  selectedProductForPrice = signal<Product | null>(null);
  newPriceInput = '';
  priceReasonInput = '';
  isSavingPrice = signal(false);
  priceHistoryList = signal<PriceHistoryRecord[]>([]);
  isLoadingHistory = signal(false);

  // Modal Xác nhận thao tác quan trọng (Xóa danh mục / Ngừng kinh doanh sản phẩm)
  showConfirmModal = signal(false);
  confirmTitle = signal('');
  confirmDescription = signal('');
  confirmActionType = signal<'deactivate_product' | 'delete_category' | null>(null);
  confirmTargetId = signal<string | null>(null);
  isConfirmProcessing = signal(false);

  constructor(
    public authService: AuthService,
    private catalogService: CatalogService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.currentUser.set(this.authService.currentUser());
    this.loadInitialData();
  }

  /** Tải đồng bộ danh sách danh mục và bảng sản phẩm từ API Gateway */
  loadInitialData(): void {
    this.loadCategories();
    this.loadProducts(1);
  }

  loadCategories(): void {
    this.catalogService.getCategories().subscribe({
      next: cats => this.categories.set(cats),
      error: () => {
        // Lỗi kết nối sẽ được hiển thị tập trung ở vùng trạng thái bảng sản phẩm
      }
    });
  }

  loadProducts(page = 1): void {
    this.isLoading.set(true);
    this.loadError.set('');
    this.currentPage.set(page);

    this.catalogService
      .getProducts({
        page,
        size: this.pageSize(),
        q: this.searchQuery,
        category_id: this.selectedCategoryId || undefined,
        status: this.selectedStatus || undefined
      })
      .subscribe({
        next: res => {
          this.products.set(res.items);
          this.totalProducts.set(res.total);
          this.totalPages.set(res.pages);
          this.isLoading.set(false);
        },
        error: err => {
          this.isLoading.set(false);
          const msg =
            err.error?.message ||
            'Chưa thể tải dữ liệu sản phẩm từ máy chủ (API Gateway :8000 / Catalog Service :8002). Vui lòng kiểm tra kết nối backend và thử lại.';
          this.loadError.set(msg);
          this.toastService.error(msg);
        }
      });
  }

  /** Thực thi lọc khi người dùng thay đổi điều kiện tìm kiếm */
  applyFilters(): void {
    this.loadProducts(1);
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.selectedCategoryId = '';
    this.selectedStatus = '';
    this.loadProducts(1);
  }

  // ===========================================================================
  // 1. QUẢN LÝ DANH MỤC (CATEGORY CRUD - FR-B03)
  // ===========================================================================
  openCategoryModal(): void {
    this.newCategoryName = '';
    this.newCategoryDesc = '';
    this.showCategoryModal.set(true);
  }

  closeCategoryModal(): void {
    this.showCategoryModal.set(false);
  }

  submitCreateCategory(): void {
    if (!this.newCategoryName.trim() || this.newCategoryName.trim().length < 2) {
      this.toastService.error('Tên danh mục phải có tối thiểu 2 ký tự.');
      return;
    }

    this.isSavingCategory.set(true);
    this.catalogService
      .createCategory({
        name: this.newCategoryName.trim(),
        description: this.newCategoryDesc.trim() || undefined,
        is_active: true
      })
      .subscribe({
        next: created => {
          this.isSavingCategory.set(false);
          this.showCategoryModal.set(false);
          this.loadCategories();
          this.toastService.success(`Đã tạo danh mục "${created.name}" thành công.`);
        },
        error: err => {
          this.isSavingCategory.set(false);
          this.toastService.error(
            err.error?.message ||
              'Không thể tạo danh mục. Vui lòng kiểm tra quyền hạn hoặc tên danh mục.'
          );
        }
      });
  }

  confirmDeleteCategory(cat: Category): void {
    this.confirmTitle.set(`Xóa danh mục "${cat.name}"`);
    this.confirmDescription.set(
      `Bạn đang yêu cầu xóa danh mục "${cat.name}". Hệ thống chỉ cho phép xóa nếu danh mục này chưa chứa bất kỳ sản phẩm nào (FR-B03).`
    );
    this.confirmActionType.set('delete_category');
    this.confirmTargetId.set(cat.id);
    this.showConfirmModal.set(true);
  }

  // ===========================================================================
  // 2. QUẢN LÝ SẢN PHẨM (PRODUCT CREATE / PATCH / DEACTIVATE)
  // ===========================================================================
  openCreateProductModal(): void {
    this.isEditingProduct.set(false);
    this.editingProductId.set(null);

    const firstCat = this.categories()[0];
    this.formCategoryId = this.selectedCategoryId || (firstCat ? firstCat.id : '');
    this.formSku = '';
    this.formName = '';
    this.formUnit = 'kg';
    this.formPrice = '65000';
    this.formOrigin = '';
    this.formShelfLifeDays = 7;
    this.formStorageCondition = 'COOL_2_8C';
    this.formStatus = 'ACTIVE';
    this.formDescription = '';
    this.selectedImageFile.set(null);
    this.imagePreviewUrl.set(null);

    this.showProductModal.set(true);
  }

  openEditProductModal(product: Product): void {
    this.isEditingProduct.set(true);
    this.editingProductId.set(product.id);

    this.formCategoryId = product.category_id;
    this.formSku = product.sku;
    this.formName = product.name;
    this.formUnit = product.unit;
    this.formPrice = product.price;
    this.formOrigin = product.origin || '';
    this.formShelfLifeDays = product.default_shelf_life_days;
    this.formStorageCondition = product.storage_condition;
    this.formStatus = product.status;
    this.formDescription = product.description || '';
    this.selectedImageFile.set(null);
    this.imagePreviewUrl.set(this.getProductThumbUrl(product));

    this.showProductModal.set(true);
  }

  closeProductModal(): void {
    this.selectedImageFile.set(null);
    this.imagePreviewUrl.set(null);
    this.showProductModal.set(false);
  }

  getProductThumbUrl(product: Product): string | null {
    const primary = product.images?.find(i => i.is_primary) ?? product.images?.[0];
    return this.catalogService.resolveProductImageUrl(primary?.image_url);
  }

  onImageFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const allowedTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
    const allowedExt = /\.(jpe?g|png|webp)$/i;
    if (!allowedTypes.has(file.type) && !allowedExt.test(file.name)) {
      this.toastService.error('Chỉ chấp nhận ảnh định dạng .webp, .jpg, .jpeg hoặc .png.');
      input.value = '';
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.toastService.error('Dung lượng ảnh tối đa là 5 MB.');
      input.value = '';
      return;
    }

    this.selectedImageFile.set(file);
    const reader = new FileReader();
    reader.onload = () => {
      this.imagePreviewUrl.set(typeof reader.result === 'string' ? reader.result : null);
    };
    reader.readAsDataURL(file);
  }

  removeProductImageInModal(): void {
    if (this.selectedImageFile()) {
      this.selectedImageFile.set(null);
      const targetId = this.editingProductId();
      const existing = targetId ? this.products().find(p => p.id === targetId) : null;
      this.imagePreviewUrl.set(existing ? this.getProductThumbUrl(existing) : null);
      return;
    }

    const targetId = this.editingProductId();
    if (!targetId) return;

    this.isDeletingImage.set(true);
    this.catalogService.deleteProductImage(targetId).subscribe({
      next: () => {
        this.isDeletingImage.set(false);
        this.imagePreviewUrl.set(null);
        this.loadProducts(this.currentPage());
        this.toastService.success('Đã xóa ảnh đại diện của sản phẩm.');
      },
      error: err => {
        this.isDeletingImage.set(false);
        this.toastService.error(err.error?.message || 'Không thể xóa ảnh sản phẩm.');
      }
    });
  }

  private finalizeProductSave(product: Product, successMessage: string): void {
    const file = this.selectedImageFile();
    if (!file) {
      this.isSavingProduct.set(false);
      this.closeProductModal();
      this.loadProducts(this.currentPage());
      this.toastService.success(successMessage);
      return;
    }

    this.catalogService.uploadProductImage(product.id, file).subscribe({
      next: () => {
        this.isSavingProduct.set(false);
        this.closeProductModal();
        this.loadProducts(this.currentPage());
        this.toastService.success(`${successMessage} (kèm ảnh minh họa).`);
      },
      error: err => {
        this.isSavingProduct.set(false);
        this.closeProductModal();
        this.loadProducts(this.currentPage());
        this.toastService.warning(
          `${successMessage}, nhưng tải ảnh thất bại: ${err.error?.message || 'Vui lòng thử lại.'}`
        );
      }
    });
  }

  submitProductForm(): void {
    if (!this.formCategoryId) {
      this.toastService.error('Vui lòng chọn danh mục trái cây trước khi lưu.');
      return;
    }
    if (!this.formName.trim() || this.formName.trim().length < 2) {
      this.toastService.error('Tên sản phẩm phải có từ 2 ký tự trở lên.');
      return;
    }
    if (!this.isEditingProduct() && (!this.formSku.trim() || this.formSku.trim().length < 2)) {
      this.toastService.error('Vui lòng nhập mã SKU duy nhất (ví dụ: XOAI-HL-01).');
      return;
    }
    if (this.formShelfLifeDays <= 0) {
      this.toastService.error('Hạn sử dụng gợi ý phải lớn hơn 0 ngày.');
      return;
    }

    if (!this.isEditingProduct()) {
      const numericPrice = Number(this.formPrice);
      if (Number.isNaN(numericPrice) || numericPrice < 0) {
        this.toastService.error('Đơn giá khởi tạo không hợp lệ (phải là số >= 0).');
        return;
      }

      this.isSavingProduct.set(true);
      this.catalogService
        .createProduct({
          category_id: this.formCategoryId,
          sku: this.formSku.trim().toUpperCase(),
          name: this.formName.trim(),
          unit: this.formUnit,
          price: numericPrice.toFixed(2),
          origin: this.formOrigin.trim() || undefined,
          default_shelf_life_days: Number(this.formShelfLifeDays),
          storage_condition: this.formStorageCondition,
          description: this.formDescription.trim() || undefined,
          status: this.formStatus
        })
        .subscribe({
          next: created => {
            this.finalizeProductSave(
              created,
              `Đã thêm sản phẩm "${created.name}" (${created.sku}) thành công.`
            );
          },
          error: err => {
            this.isSavingProduct.set(false);
            this.toastService.error(
              err.error?.message ||
                'Không thể thêm sản phẩm. Vui lòng kiểm tra mã SKU hoặc dữ liệu đã nhập.'
            );
          }
        });
    } else {
      const targetId = this.editingProductId();
      if (!targetId) return;

      this.isSavingProduct.set(true);
      this.catalogService
        .updateProduct(targetId, {
          category_id: this.formCategoryId,
          name: this.formName.trim(),
          unit: this.formUnit,
          origin: this.formOrigin.trim() || undefined,
          default_shelf_life_days: Number(this.formShelfLifeDays),
          storage_condition: this.formStorageCondition,
          description: this.formDescription.trim() || undefined,
          status: this.formStatus
        })
        .subscribe({
          next: updated => {
            this.finalizeProductSave(
              updated,
              `Đã cập nhật thông tin sản phẩm "${updated.name}".`
            );
          },
          error: err => {
            this.isSavingProduct.set(false);
            this.toastService.error(
              err.error?.message || 'Cập nhật thông tin sản phẩm không thành công.'
            );
          }
        });
    }
  }

  confirmDeactivateProduct(product: Product): void {
    this.confirmTitle.set(`Ngừng kinh doanh "${product.name}"`);
    this.confirmDescription.set(
      `Sản phẩm "${product.name}" (SKU: ${product.sku}) sẽ chuyển sang trạng thái "Ngừng kinh doanh" (INACTIVE) và không xuất hiện khi tạo đơn hàng mới, nhưng vẫn giữ nguyên lịch sử đơn hàng & tồn kho cũ (FR-B05).`
    );
    this.confirmActionType.set('deactivate_product');
    this.confirmTargetId.set(product.id);
    this.showConfirmModal.set(true);
  }

  closeConfirmModal(): void {
    this.showConfirmModal.set(false);
    this.confirmActionType.set(null);
    this.confirmTargetId.set(null);
  }

  executeConfirmedAction(): void {
    const action = this.confirmActionType();
    const targetId = this.confirmTargetId();
    if (!action || !targetId) return;

    this.isConfirmProcessing.set(true);
    if (action === 'deactivate_product') {
      this.catalogService.deactivateProduct(targetId).subscribe({
        next: updated => {
          this.isConfirmProcessing.set(false);
          this.closeConfirmModal();
          this.loadProducts(this.currentPage());
          this.toastService.success(
            `Đã chuyển "${updated.name}" sang trạng thái Ngừng kinh doanh.`
          );
        },
        error: err => {
          this.isConfirmProcessing.set(false);
          this.closeConfirmModal();
          this.toastService.error(
            err.error?.message || 'Không thể ngừng kinh doanh sản phẩm.'
          );
        }
      });
    } else if (action === 'delete_category') {
      this.catalogService.deleteCategory(targetId).subscribe({
        next: () => {
          this.isConfirmProcessing.set(false);
          this.closeConfirmModal();
          if (this.selectedCategoryId === targetId) {
            this.selectedCategoryId = '';
          }
          this.loadCategories();
          this.loadProducts(1);
          this.toastService.success('Đã xóa danh mục thành công.');
        },
        error: err => {
          this.isConfirmProcessing.set(false);
          this.closeConfirmModal();
          this.toastService.error(
            err.error?.message ||
              'Không thể xóa danh mục vì danh mục vẫn đang chứa sản phẩm.'
          );
        }
      });
    }
  }

  // ===========================================================================
  // 3. ĐIỀU CHỈNH ĐƠN GIÁ & XEM PRICE HISTORY (FR-B06, BR-07)
  // ===========================================================================
  openPriceModal(product: Product): void {
    this.selectedProductForPrice.set(product);
    this.newPriceInput = String(Math.round(Number(product.price)));
    this.priceReasonInput = '';
    this.showPriceModal.set(true);
    this.fetchPriceHistory(product.id);
  }

  closePriceModal(): void {
    this.showPriceModal.set(false);
    this.selectedProductForPrice.set(null);
    this.priceHistoryList.set([]);
  }

  fetchPriceHistory(productId: string): void {
    this.isLoadingHistory.set(true);
    this.catalogService.getPriceHistory(productId).subscribe({
      next: records => {
        this.priceHistoryList.set(records);
        this.isLoadingHistory.set(false);
      },
      error: () => {
        this.isLoadingHistory.set(false);
      }
    });
  }

  submitPriceUpdate(): void {
    const product = this.selectedProductForPrice();
    if (!product) return;

    const parsedPrice = Number(this.newPriceInput);
    if (Number.isNaN(parsedPrice) || parsedPrice < 0) {
      this.toastService.error('Đơn giá mới phải là số lớn hơn hoặc bằng 0.');
      return;
    }

    if (parsedPrice === Number(product.price)) {
      this.toastService.error(
        'Đơn giá mới trùng với đơn giá hiện tại. Vui lòng nhập mức giá khác.'
      );
      return;
    }

    if (!this.priceReasonInput.trim()) {
      this.toastService.error(
        'Vui lòng nhập lý do điều chỉnh giá (ví dụ: Giá mùa vụ, Khuyến mãi cuối tuần).'
      );
      return;
    }

    this.isSavingPrice.set(true);
    this.catalogService
      .updateProductPrice(product.id, {
        new_price: parsedPrice.toFixed(2),
        reason: this.priceReasonInput.trim()
      })
      .subscribe({
        next: updated => {
          this.isSavingPrice.set(false);
          this.selectedProductForPrice.set(updated);
          this.priceReasonInput = '';
          this.fetchPriceHistory(updated.id);
          this.loadProducts(this.currentPage());
          this.toastService.success(
            `Đã cập nhật giá "${updated.name}" thành ${this.formatVnd(updated.price)}/${this.formatUnitLabel(updated.unit)} và ghi nhận lịch sử giá.`
          );
        },
        error: err => {
          this.isSavingPrice.set(false);
          this.toastService.error(
            err.error?.message || 'Không thể cập nhật đơn giá sản phẩm.'
          );
        }
      });
  }

  // ===========================================================================
  // 4. HÀM TIỆN ÍCH ĐỊNH DẠNG HIỂN THỊ CHUẨN NGHIỆP VỤ VIỆT NAM
  // ===========================================================================
  /** Định dạng số tiền sang chuẩn Việt Nam, ví dụ `"65000.00"` -> `"65.000 ₫"` */
  formatVnd(priceStr: string | number): string {
    const num = Number(priceStr);
    if (Number.isNaN(num)) return '0 ₫';
    return `${num.toLocaleString('vi-VN')} ₫`;
  }

  /** Chuyển mã đơn vị (`kg`, `hop`, `qua`) sang nhãn tiếng Việt có dấu */
  formatUnitLabel(unit: ProductUnit | string): string {
    switch (unit) {
      case 'kg':
        return 'kg';
      case 'hop':
        return 'hộp';
      case 'qua':
        return 'quả';
      default:
        return unit;
    }
  }

  /** Chuyển mã điều kiện bảo quản sang nhãn nghiệp vụ rõ nghĩa */
  formatStorageLabel(cond: StorageCondition | string): string {
    switch (cond) {
      case 'COOL_2_8C':
        return 'Mát 2–8°C';
      case 'COOL_8_12C':
        return 'Mát 8–12°C';
      case 'AMBIENT':
        return 'Nhiệt độ phòng';
      default:
        return cond;
    }
  }

  /** Chuyển mã trạng thái sản phẩm sang nhãn tiếng Việt */
  formatStatusLabel(status: ProductStatus | string): string {
    switch (status) {
      case 'ACTIVE':
        return 'Đang kinh doanh';
      case 'INACTIVE':
        return 'Ngừng kinh doanh';
      case 'OUT_OF_SEASON':
        return 'Tạm hết mùa';
      default:
        return status;
    }
  }

  logout(): void {
    this.authService.logout();
  }
}

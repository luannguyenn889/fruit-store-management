/**
 * Module: features/shop/shop.component.ts
 * Nhiệm vụ: Trang Cửa hàng trực tuyến (Storefront) dành cho Khách hàng (`/shop`).
 *           - Hiển thị danh mục trái cây đang kích hoạt (`is_active = true`) và sản phẩm đang bán (`ACTIVE`).
 *           - Hỗ trợ tìm kiếm theo tên/SKU/xuất xứ, lọc theo danh mục, phân trang và xem chi tiết sản phẩm.
 *           - Trung thực với trạng thái phát triển: hiển thị thông báo rõ tính năng Giỏ hàng/Đặt hàng
 *             đang chờ hoàn thiện ở giai đoạn tiếp theo (không tạo số liệu hoặc chức năng giả).
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  CatalogService,
  Category,
  Product,
  StorageCondition
} from '../../core/services/catalog.service';
import { StorefrontLayoutComponent } from '../../core/layout/storefront-layout/storefront-layout.component';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';

@Component({
  selector: 'app-shop',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    StorefrontLayoutComponent,
    SkeletonLoaderComponent,
    PaginationComponent
  ],
  templateUrl: './shop.component.html',
  styleUrls: ['./shop.component.css']
})
export class ShopComponent implements OnInit {
  categories = signal<Category[]>([]);
  products = signal<Product[]>([]);
  totalProducts = signal(0);
  currentPage = signal(1);
  pageSize = signal(12);
  totalPages = signal(1);

  searchQuery = '';
  selectedCategoryId = signal<string>('');

  isLoading = signal(false);
  loadError = signal('');

  selectedProduct = signal<Product | null>(null);

  constructor(private catalogService: CatalogService) {}

  ngOnInit(): void {
    this.loadCategories();
    this.loadProducts(1);
  }

  loadCategories(): void {
    this.catalogService.getCategories().subscribe({
      next: cats => {
        this.categories.set(cats.filter(c => c.is_active));
      },
      error: () => {
        // Lỗi tải danh mục không chặn hiển thị lỗi chung từ sản phẩm
      }
    });
  }

  loadProducts(page = 1): void {
    this.isLoading.set(true);
    this.loadError.set('');

    this.catalogService
      .getProducts({
        page,
        size: this.pageSize(),
        q: this.searchQuery.trim() || undefined,
        category_id: this.selectedCategoryId() || undefined,
        status: 'ACTIVE'
      })
      .subscribe({
        next: res => {
          this.products.set(res.items);
          this.totalProducts.set(res.total);
          this.currentPage.set(res.page);
          this.totalPages.set(Math.max(1, res.pages));
          this.isLoading.set(false);
        },
        error: () => {
          this.isLoading.set(false);
          this.loadError.set(
            'Không thể tải danh sách sản phẩm lúc này. Vui lòng thử tải lại sau.'
          );
        }
      });
  }

  selectCategory(categoryId: string): void {
    this.selectedCategoryId.set(categoryId);
    this.loadProducts(1);
  }

  applySearch(): void {
    this.loadProducts(1);
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.selectedCategoryId.set('');
    this.loadProducts(1);
  }

  openProductDetail(product: Product): void {
    this.selectedProduct.set(product);
  }

  closeProductDetail(): void {
    this.selectedProduct.set(null);
  }

  formatVnd(priceStr: string | number): string {
    const num = Number(priceStr);
    if (Number.isNaN(num)) return '0 ₫';
    return `${num.toLocaleString('vi-VN')} ₫`;
  }

  formatUnitLabel(unit: string): string {
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

  formatStorageLabel(condition: StorageCondition): string {
    switch (condition) {
      case 'COOL_2_8C':
        return 'Bảo quản mát 2–8°C';
      case 'COOL_8_12C':
        return 'Bảo quản mát 8–12°C';
      case 'AMBIENT':
      default:
        return 'Nhiệt độ thường';
    }
  }
}

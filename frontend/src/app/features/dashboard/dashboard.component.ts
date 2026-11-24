/**
 * Module: features/dashboard/dashboard.component.ts
 * Nhiệm vụ: Màn hình Tổng quan Quản trị Cửa hàng (Admin/Manager Dashboard).
 *           Tuân thủ nguyên tắc Honest UI trong `UI_UX_DESIGN_RULES_FruitStore.md`:
 *           - Chỉ hiển thị số liệu thật lấy từ Backend (hiện tại là `CatalogService` và `AuthService`).
 *           - Các khối dữ liệu thuộc `Inventory`, `Order`, `Reporting` (chưa triển khai)
 *             hiển thị trạng thái trung thực "Chưa có dữ liệu", tuyệt đối không bịa số giả.
 */

import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService, User } from '../../core/services/auth.service';
import {
  CatalogService,
  Category,
  Product
} from '../../core/services/catalog.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  activeTab = signal<'today' | 'week' | 'month'>('today');
  chartMetric = signal<'revenue' | 'volume'>('revenue');

  currentUser = signal<User | null>(null);
  todayLabel = new Date().toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  });

  // Dữ liệu thật từ Catalog Service (:8002 qua Gateway :8000)
  categories = signal<Category[]>([]);
  products = signal<Product[]>([]);
  totalProducts = signal<number>(0);
  isLoadingCatalog = signal<boolean>(false);
  catalogError = signal<string>('');

  // Các chỉ số tổng hợp tính từ dữ liệu thật của Catalog Service
  activeProductsCount = computed(
    () => this.products().filter(p => p.status === 'ACTIVE').length
  );
  inactiveProductsCount = computed(
    () => this.products().filter(p => p.status !== 'ACTIVE').length
  );
  topCatalogPreview = computed(() => this.products().slice(0, 5));

  constructor(
    public authService: AuthService,
    private catalogService: CatalogService
  ) {}

  ngOnInit(): void {
    const user = this.authService.currentUser();
    if (user) {
      this.currentUser.set(user);
    }
    this.loadRealCatalogSummary();
  }

  /** Tải dữ liệu thật từ Catalog Service để hiển thị lên Tổng quan */
  loadRealCatalogSummary(): void {
    this.isLoadingCatalog.set(true);
    this.catalogError.set('');

    this.catalogService.getCategories().subscribe({
      next: cats => this.categories.set(cats),
      error: () => {
        // Lỗi chung sẽ hiển thị tại khối tải sản phẩm
      }
    });

    this.catalogService.getProducts({ page: 1, size: 50 }).subscribe({
      next: res => {
        this.products.set(res.items);
        this.totalProducts.set(res.total);
        this.isLoadingCatalog.set(false);
      },
      error: () => {
        this.isLoadingCatalog.set(false);
        this.catalogError.set(
          'Chưa kết nối được Catalog Service (:8002) qua API Gateway (:8000).'
        );
      }
    });
  }

  setTab(tab: 'today' | 'week' | 'month'): void {
    this.activeTab.set(tab);
  }

  setChartMetric(metric: 'revenue' | 'volume'): void {
    this.chartMetric.set(metric);
  }

  /** Định dạng số tiền sang chuẩn VNĐ, ví dụ `65.000 ₫` */
  formatVnd(priceStr: string | number): string {
    const num = Number(priceStr);
    if (Number.isNaN(num)) return '0 ₫';
    return `${num.toLocaleString('vi-VN')} ₫`;
  }

  /** Chuyển mã đơn vị tính sang nhãn hiển thị */
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

  logout(): void {
    this.authService.logout();
  }
}

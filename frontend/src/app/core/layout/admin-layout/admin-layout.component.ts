/**
 * Module: core/layout/admin-layout/admin-layout.component.ts
 * Nhiệm vụ: Bố cục khung quản trị dùng chung (Admin Shell) cho toàn bộ màn hình quản trị
 *           (`/dashboard`, `/catalog`, `/users`):
 *           - Sidebar trái đồng nhất: 3 mục đang hoạt động và 7 mục đang phát triển (làm mờ disabled).
 *           - Hỗ trợ thu gọn sidebar trên desktop và mở dạng Drawer trên mobile (< 992px).
 *           - Topbar gồm nút menu, Breadcrumb ngữ cảnh, tên/vai trò người dùng và nút Đăng xuất.
 */

import { Component, Input, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './admin-layout.component.html',
  styleUrls: ['./admin-layout.component.css']
})
export class AdminLayoutComponent {
  @Input() sectionTitle = 'Tổng quan';
  @Input() pageTitle = 'Tổng quan Dashboard';

  currentUser = computed(() => this.authService.currentUser());
  isAdmin = computed(() => this.authService.hasRole('ADMIN'));
  isAdminOrManager = computed(() => this.authService.hasRole('ADMIN', 'MANAGER'));
  canSeeSalesSection = computed(() =>
    this.authService.hasRole('ADMIN', 'MANAGER', 'STAFF')
  );
  canSeeInventorySection = computed(() =>
    this.authService.hasRole('ADMIN', 'MANAGER', 'STAFF', 'WAREHOUSE')
  );
  canSeeStockOps = computed(() =>
    this.authService.hasRole('ADMIN', 'MANAGER', 'WAREHOUSE')
  );
  canSeeReportsSection = computed(() =>
    this.authService.hasRole('ADMIN', 'MANAGER', 'WAREHOUSE')
  );
  canSeeRevenueReport = computed(() =>
    this.authService.hasRole('ADMIN', 'MANAGER')
  );
  accountNavLabel = computed(() =>
    this.isAdminOrManager() ? 'Cấu hình & Nhân sự' : 'Hồ sơ cá nhân'
  );

  isSidebarCollapsed = signal(false);
  isMobileDrawerOpen = signal(false);

  constructor(public authService: AuthService) {}

  toggleDesktopSidebar(): void {
    this.isSidebarCollapsed.update(v => !v);
  }

  toggleMobileDrawer(): void {
    this.isMobileDrawerOpen.update(v => !v);
  }

  closeMobileDrawer(): void {
    this.isMobileDrawerOpen.set(false);
  }

  logout(): void {
    this.authService.logout();
  }
}

/**
 * Module: core/layout/storefront-layout/storefront-layout.component.ts
 * Nhiệm vụ: Khung giao diện Cửa hàng trực tuyến (Customer Storefront Shell) dành cho
 *           Khách hàng và khách truy cập công khai (`/shop`, `/profile`):
 *           - Header cố định (sticky) với logo Fresh Orchard, điều hướng Cửa hàng, Tài khoản của tôi
 *             và lối vào Trang quản trị (chỉ hiển thị với nhân sự nội bộ).
 *           - Giữ lớp CSS `.logout-icon-btn` để tương thích với bộ kiểm thử Cypress E2E.
 */

import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-storefront-layout',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './storefront-layout.component.html',
  styleUrls: ['./storefront-layout.component.css']
})
export class StorefrontLayoutComponent {
  currentUser = computed(() => this.authService.currentUser());
  isLoggedIn = computed(() => this.authService.isLoggedIn());
  isInternalUser = computed(() => this.authService.isInternalUser());
  isMobileMenuOpen = signal(false);

  constructor(public authService: AuthService) {}

  toggleMobileMenu(): void {
    this.isMobileMenuOpen.update(open => !open);
  }

  closeMobileMenu(): void {
    this.isMobileMenuOpen.set(false);
  }

  logout(): void {
    this.closeMobileMenu();
    this.authService.logout();
  }
}

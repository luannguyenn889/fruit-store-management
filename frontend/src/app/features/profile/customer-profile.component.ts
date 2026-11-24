/**
 * Module: features/profile/customer-profile.component.ts
 * Nhiệm vụ: Màn hình Tài khoản Khách hàng (`/profile`) bọc trong `StorefrontLayoutComponent`:
 *           - Cập nhật hồ sơ cá nhân (`PATCH /api/v1/auth/me`) qua `#profile-name`, `#profile-phone`.
 *           - Đổi mật khẩu (`POST /api/v1/auth/change-password`) qua `#curr-pwd`, `#new-pwd`, `#confirm-pwd`.
 *           - Hiển thị khối trạng thái trung thực cho mục Đơn hàng của tôi (chờ Order Service).
 */

import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService, User } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { StorefrontLayoutComponent } from '../../core/layout/storefront-layout/storefront-layout.component';

@Component({
  selector: 'app-customer-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, StorefrontLayoutComponent],
  templateUrl: './customer-profile.component.html',
  styleUrls: ['./customer-profile.component.css']
})
export class CustomerProfileComponent implements OnInit {
  currentUser = computed(() => this.authService.currentUser());

  profileFullName = '';
  profilePhone = '';
  isSavingProfile = signal(false);

  currentPassword = '';
  newPasswordInput = '';
  confirmPasswordInput = '';
  showPasswords = false;
  isSavingPassword = signal(false);

  constructor(
    public authService: AuthService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    const cached = this.currentUser();
    if (cached) {
      this.syncProfileForm(cached);
    }

    // Đồng bộ lại thông tin mới nhất từ backend sau khi tải trang / F5
    if (this.authService.getToken()) {
      this.authService.getProfile().subscribe({
        next: user => this.syncProfileForm(user),
        error: () => {
          // Giữ thông tin từ phiên hiện tại nếu không tải lại được
        }
      });
    }
  }

  private syncProfileForm(user: User): void {
    this.profileFullName = user.full_name || '';
    this.profilePhone = user.phone || '';
  }

  submitProfileUpdate(): void {
    if (!this.profileFullName.trim() || this.profileFullName.trim().length < 2) {
      this.toastService.error('Họ và tên phải có tối thiểu 2 ký tự.');
      return;
    }

    this.isSavingProfile.set(true);
    this.authService
      .updateProfile({
        full_name: this.profileFullName.trim(),
        phone: this.profilePhone.trim() || undefined
      })
      .subscribe({
        next: user => {
          this.isSavingProfile.set(false);
          this.syncProfileForm(user);
          this.toastService.success('Đã cập nhật thông tin hồ sơ cá nhân thành công.');
        },
        error: err => {
          this.isSavingProfile.set(false);
          this.toastService.error(
            err.error?.message || err.error?.detail || 'Không thể cập nhật hồ sơ cá nhân.'
          );
        }
      });
  }

  submitChangePassword(): void {
    if (!this.currentPassword) {
      this.toastService.error('Vui lòng nhập mật khẩu hiện tại.');
      return;
    }

    if (!this.newPasswordInput || this.newPasswordInput.length < 6) {
      this.toastService.error('Mật khẩu mới phải có tối thiểu 6 ký tự.');
      return;
    }

    if (this.newPasswordInput !== this.confirmPasswordInput) {
      this.toastService.error('Mật khẩu xác nhận không khớp với mật khẩu mới.');
      return;
    }

    this.isSavingPassword.set(true);
    this.authService
      .changePassword({
        current_password: this.currentPassword,
        new_password: this.newPasswordInput
      })
      .subscribe({
        next: () => {
          this.isSavingPassword.set(false);
          this.currentPassword = '';
          this.newPasswordInput = '';
          this.confirmPasswordInput = '';
          this.toastService.success('Đã đổi mật khẩu thành công.');
        },
        error: err => {
          this.isSavingPassword.set(false);
          this.toastService.error(
            err.error?.message || err.error?.detail || 'Mật khẩu hiện tại không chính xác.'
          );
        }
      });
  }
}

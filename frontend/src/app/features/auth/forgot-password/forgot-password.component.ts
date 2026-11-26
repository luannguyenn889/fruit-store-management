/**
 * Module: features/auth/forgot-password/forgot-password.component.ts
 * Nhiệm vụ: Màn hình Quên mật khẩu (`/forgot-password` - FR-A10).
 *           Gửi yêu cầu tới `POST /api/v1/auth/forgot-password` để nhận email Gmail chứa liên kết đặt lại mật khẩu.
 */

import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './forgot-password.component.html',
  styleUrls: ['../login/login.component.css']
})
export class ForgotPasswordComponent {
  email = '';
  isLoading = signal(false);
  isSent = signal(false);

  constructor(
    private authService: AuthService,
    private toastService: ToastService
  ) {}

  onSubmit(): void {
    const cleanEmail = this.email.trim();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      this.toastService.error('Vui lòng nhập địa chỉ email hợp lệ.');
      return;
    }

    this.isLoading.set(true);
    this.authService.forgotPassword(cleanEmail).subscribe({
      next: res => {
        this.isLoading.set(false);
        this.isSent.set(true);
        this.toastService.success(res.message);
      },
      error: err => {
        this.isLoading.set(false);
        const message =
          err.error?.message ||
          err.error?.detail ||
          'Không thể gửi yêu cầu đặt lại mật khẩu lúc này. Vui lòng thử lại sau.';
        this.toastService.error(message);
      }
    });
  }
}

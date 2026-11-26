/**
 * Module: features/auth/forgot-password/forgot-password.component.ts
 * Nhiệm vụ: Màn hình Quên mật khẩu (`/forgot-password` - FR-A10).
 *           Gửi yêu cầu tới `POST /api/v1/auth/forgot-password` để nhận mã OTP 6 chữ số qua Gmail
 *           và chuyển sang màn hình nhập mã `/reset-password`.
 */

import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
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

  constructor(
    private authService: AuthService,
    private toastService: ToastService,
    private router: Router
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
        this.toastService.success(res.message);
        this.router.navigate(['/reset-password'], {
          queryParams: { email: cleanEmail }
        });
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

/**
 * Module: features/auth/reset-password/reset-password.component.ts
 * Nhiệm vụ: Màn hình Đặt lại mật khẩu mới (`/reset-password?token=...` - FR-A10).
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './reset-password.component.html',
  styleUrls: ['../login/login.component.css']
})
export class ResetPasswordComponent implements OnInit {
  token = '';
  newPassword = '';
  confirmPassword = '';
  showPassword = false;
  isLoading = signal(false);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    const queryToken = this.route.snapshot.queryParamMap.get('token');
    if (queryToken) {
      this.token = queryToken;
    }
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    if (!this.token.trim()) {
      this.toastService.error('Liên kết đặt lại mật khẩu thiếu token xác thực.');
      return;
    }

    if (!this.newPassword || this.newPassword.length < 6) {
      this.toastService.error('Mật khẩu mới phải có tối thiểu 6 ký tự.');
      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.toastService.error('Mật khẩu xác nhận không khớp. Vui lòng nhập lại.');
      return;
    }

    this.isLoading.set(true);
    this.authService.resetPassword(this.token, this.newPassword).subscribe({
      next: res => {
        this.isLoading.set(false);
        this.toastService.success(res.message);
        this.router.navigate(['/login']);
      },
      error: err => {
        this.isLoading.set(false);
        const message =
          err.error?.message ||
          err.error?.detail ||
          'Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.';
        this.toastService.error(message);
      }
    });
  }
}

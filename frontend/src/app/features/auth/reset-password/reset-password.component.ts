/**
 * Module: features/auth/reset-password/reset-password.component.ts
 * Nhiệm vụ: Màn hình Nhập mã OTP 6 chữ số và Đặt lại mật khẩu mới (`/reset-password` - FR-A10).
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
  email = '';
  otpCode = '';
  newPassword = '';
  confirmPassword = '';
  showPassword = false;
  isLoading = signal(false);
  isResending = signal(false);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    const queryEmail = this.route.snapshot.queryParamMap.get('email');
    if (queryEmail) {
      this.email = queryEmail;
    }
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  resendOtp(): void {
    const cleanEmail = this.email.trim();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      this.toastService.error('Vui lòng nhập email hợp lệ để gửi lại mã.');
      return;
    }
    this.isResending.set(true);
    this.authService.forgotPassword(cleanEmail).subscribe({
      next: res => {
        this.isResending.set(false);
        this.toastService.success(res.message);
      },
      error: err => {
        this.isResending.set(false);
        this.toastService.error(
          err.error?.message || 'Không thể gửi lại mã xác nhận lúc này.'
        );
      }
    });
  }

  onSubmit(): void {
    const cleanEmail = this.email.trim();
    const cleanOtp = this.otpCode.trim();

    if (!cleanEmail || !cleanEmail.includes('@')) {
      this.toastService.error('Vui lòng nhập email tài khoản hợp lệ.');
      return;
    }

    if (!/^\d{6}$/.test(cleanOtp)) {
      this.toastService.error('Mã xác nhận phải gồm đúng 6 chữ số.');
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
    this.authService.resetPassword(cleanEmail, cleanOtp, this.newPassword).subscribe({
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
          'Mã xác nhận 6 chữ số không đúng hoặc đã hết hạn.';
        this.toastService.error(message);
      }
    });
  }
}

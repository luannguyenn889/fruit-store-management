/**
 * Module: features/auth/login/login.component.ts
 * Nhiệm vụ: Xử lý giao diện và sự kiện đăng nhập hệ thống FruitStore.
 *           - Hỗ trợ đăng nhập bằng Email/SĐT + mật khẩu qua API Gateway.
 *           - Hỗ trợ đăng nhập bằng Google OAuth2 (Google Identity Services).
 *           - Hiển thị phản hồi thành công/lỗi qua Global `ToastService` (thay thế alert cố định).
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

declare const google: any;

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit {
  // Tài khoản mẫu Quản lý cửa hàng (khớp với script seed.py của auth-service)
  contact = 'manager@fruitstore.com';
  password = 'Manager@123';
  rememberMe = true;

  showPassword = false;
  isLoading = signal(false);

  constructor(
    private authService: AuthService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.initGoogleAuth();
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    if (!this.contact.trim() || !this.password) {
      this.toastService.error('Vui lòng nhập đầy đủ email/số điện thoại và mật khẩu.');
      return;
    }

    this.isLoading.set(true);
    this.authService.login(this.contact.trim(), this.password).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.toastService.success('Đăng nhập thành công.');
        this.router.navigate([this.authService.getDefaultRoute()]);
      },
      error: err => {
        this.isLoading.set(false);
        const message =
          err.error?.message ||
          err.error?.detail ||
          'Email/số điện thoại hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại.';
        this.toastService.error(message);
      }
    });
  }

  private initGoogleAuth(): void {
    if (typeof google !== 'undefined' && google.accounts?.id) {
      google.accounts.id.initialize({
        client_id: this.authService.googleClientId,
        callback: (response: any) => this.handleGoogleCredential(response.credential)
      });
    }
  }

  triggerGoogleSignIn(): void {
    if (typeof google !== 'undefined' && google.accounts?.id) {
      google.accounts.id.initialize({
        client_id: this.authService.googleClientId,
        callback: (response: any) => this.handleGoogleCredential(response.credential)
      });
      google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          this.toastService.error(
            'Không thể mở hộp thoại Google (trình duyệt đã chặn popup hoặc domain chưa được cấp phép trên Google Cloud Console). Vui lòng đăng nhập bằng Email và mật khẩu.'
          );
        }
      });
    } else {
      this.toastService.error(
        'Thư viện Google Identity Services chưa tải xong. Vui lòng kiểm tra kết nối mạng hoặc đăng nhập bằng mật khẩu.'
      );
    }
  }

  private handleGoogleCredential(credential: string): void {
    this.isLoading.set(true);
    this.authService.loginWithGoogle(credential).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.toastService.success('Đăng nhập thành công.');
        this.router.navigate([this.authService.getDefaultRoute()]);
      },
      error: err => {
        this.isLoading.set(false);
        const message =
          err.error?.message ||
          err.error?.detail ||
          'Xác thực tài khoản Google không thành công. Vui lòng thử lại.';
        this.toastService.error(message);
      }
    });
  }
}

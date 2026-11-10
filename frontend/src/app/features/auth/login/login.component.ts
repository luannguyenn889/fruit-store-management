/**
 * Module: features/auth/login/login.component.ts
 * Nhiệm vụ: Xử lý giao diện và sự kiện đăng nhập hệ thống FruitStore.
 *           - Hỗ trợ đăng nhập bằng Email/SĐT + mật khẩu qua API Gateway.
 *           - Hỗ trợ đăng nhập bằng Google OAuth2 (Google Identity Services).
 *           - Đã loại bỏ hoàn toàn `mockGoogleLoginFallback` để đảm bảo tính trung thực
 *             và bảo mật (Honest UI & SRS Security Fix).
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

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
  errorMessage = signal('');

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.initGoogleAuth();
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    this.errorMessage.set('');

    if (!this.contact.trim() || !this.password) {
      this.errorMessage.set('Vui lòng nhập đầy đủ email/số điện thoại và mật khẩu.');
      return;
    }

    this.isLoading.set(true);
    this.authService.login(this.contact.trim(), this.password).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: err => {
        this.isLoading.set(false);
        const message =
          err.error?.message ||
          err.error?.detail ||
          'Email/số điện thoại hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại.';
        this.errorMessage.set(message);
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
    this.errorMessage.set('');
    if (typeof google !== 'undefined' && google.accounts?.id) {
      google.accounts.id.initialize({
        client_id: this.authService.googleClientId,
        callback: (response: any) => this.handleGoogleCredential(response.credential)
      });
      google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          this.errorMessage.set(
            'Không thể mở hộp thoại Google (trình duyệt đã chặn popup hoặc domain chưa được cấp phép trên Google Cloud Console). Vui lòng đăng nhập bằng Email và mật khẩu.'
          );
        }
      });
    } else {
      this.errorMessage.set(
        'Thư viện Google Identity Services chưa tải xong. Vui lòng kiểm tra kết nối mạng hoặc đăng nhập bằng mật khẩu.'
      );
    }
  }

  private handleGoogleCredential(credential: string): void {
    this.errorMessage.set('');
    this.isLoading.set(true);
    this.authService.loginWithGoogle(credential).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: err => {
        this.isLoading.set(false);
        const message =
          err.error?.message ||
          err.error?.detail ||
          'Xác thực tài khoản Google không thành công. Vui lòng thử lại.';
        this.errorMessage.set(message);
      }
    });
  }
}

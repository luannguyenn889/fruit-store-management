/**
 * Module: features/auth/register/register.component.ts
 * Nhiệm vụ: Màn hình đăng ký tài khoản khách hàng mới của hệ thống FruitStore.
 *           - Bảo mật (FR-A01): Không gửi `role_code` lên server; hệ thống luôn gán vai trò `CUSTOMER`.
 *           - Bảo mật Google OAuth2: Đã loại bỏ `mockGoogleLoginFallback`, chỉ chấp nhận
 *             Google ID Token hợp lệ được xác thực chữ ký tại Backend.
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

declare const google: any;

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent implements OnInit {
  fullName = '';
  contact = '';
  password = '';
  confirmPassword = '';
  agreeTerms = true;

  showPassword = false;
  showConfirmPassword = false;
  isLoading = signal(false);
  errorMessage = signal('');

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.initGoogleAuth();
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPassword(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  onSubmit(): void {
    this.errorMessage.set('');

    if (!this.fullName.trim()) {
      this.errorMessage.set('Vui lòng nhập họ và tên đầy đủ.');
      return;
    }

    if (!this.contact.trim()) {
      this.errorMessage.set('Vui lòng nhập địa chỉ email hoặc số điện thoại.');
      return;
    }

    if (!this.password || this.password.length < 6) {
      this.errorMessage.set('Mật khẩu phải có tối thiểu 6 ký tự.');
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.errorMessage.set('Mật khẩu xác nhận không khớp. Vui lòng nhập lại.');
      return;
    }

    if (!this.agreeTerms) {
      this.errorMessage.set(
        'Bạn cần đồng ý với Điều khoản dịch vụ và Chính sách bảo mật để tiếp tục.'
      );
      return;
    }

    const email = this.contact.includes('@')
      ? this.contact.trim()
      : `${this.contact.trim()}@fruitstore.local`;

    const phone = !this.contact.includes('@') ? this.contact.trim() : undefined;

    this.isLoading.set(true);
    this.authService
      .register({
        email,
        phone,
        password: this.password,
        full_name: this.fullName.trim()
      })
      .subscribe({
        next: () => {
          // Tự động đăng nhập sau khi tạo tài khoản thành công
          this.authService.login(email, this.password).subscribe({
            next: () => {
              this.isLoading.set(false);
              this.router.navigate(['/dashboard']);
            },
            error: () => {
              this.isLoading.set(false);
              this.router.navigate(['/login']);
            }
          });
        },
        error: err => {
          this.isLoading.set(false);
          const message =
            err.error?.message ||
            err.error?.detail ||
            'Không thể đăng ký tài khoản. Vui lòng kiểm tra lại thông tin đã nhập.';
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
            'Không thể hiển thị cửa sổ đăng ký Google (popup bị chặn hoặc origin chưa được ủy quyền). Vui lòng điền biểu mẫu đăng ký bên trên.'
          );
        }
      });
    } else {
      this.errorMessage.set(
        'Không tải được dịch vụ Google Identity. Vui lòng sử dụng biểu mẫu đăng ký bằng Email.'
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
          'Đăng ký nhanh bằng Google không thành công.';
        this.errorMessage.set(message);
      }
    });
  }
}

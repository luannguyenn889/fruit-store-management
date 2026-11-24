/**
 * Module: features/auth/register/register.component.ts
 * Nhiệm vụ: Màn hình đăng ký tài khoản khách hàng mới của hệ thống FruitStore.
 *           - Bảo mật (FR-A01): Không gửi `role_code` lên server; hệ thống luôn gán vai trò `CUSTOMER`.
 *           - Hiển thị thông báo validation và kết quả qua Global `ToastService` (thay thế alert cố định).
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

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

  toggleConfirmPassword(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  onSubmit(): void {
    if (!this.fullName.trim()) {
      this.toastService.error('Vui lòng nhập họ và tên đầy đủ.');
      return;
    }

    if (!this.contact.trim()) {
      this.toastService.error('Vui lòng nhập địa chỉ email hoặc số điện thoại.');
      return;
    }

    if (!this.password || this.password.length < 6) {
      this.toastService.error('Mật khẩu phải có tối thiểu 6 ký tự.');
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.toastService.error('Mật khẩu xác nhận không khớp. Vui lòng nhập lại.');
      return;
    }

    if (!this.agreeTerms) {
      this.toastService.error(
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
              this.toastService.success('Đăng ký tài khoản thành công.');
              this.router.navigate([this.authService.getDefaultRoute()]);
            },
            error: () => {
              this.isLoading.set(false);
              this.toastService.success('Đăng ký tài khoản thành công. Vui lòng đăng nhập.');
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
            'Không thể hiển thị cửa sổ đăng ký Google (popup bị chặn hoặc origin chưa được ủy quyền). Vui lòng điền biểu mẫu đăng ký bên trên.'
          );
        }
      });
    } else {
      this.toastService.error(
        'Không tải được dịch vụ Google Identity. Vui lòng sử dụng biểu mẫu đăng ký bằng Email.'
      );
    }
  }

  private handleGoogleCredential(credential: string): void {
    this.isLoading.set(true);
    this.authService.loginWithGoogle(credential).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.toastService.success('Đăng ký tài khoản thành công.');
        this.router.navigate([this.authService.getDefaultRoute()]);
      },
      error: err => {
        this.isLoading.set(false);
        const message =
          err.error?.message ||
          err.error?.detail ||
          'Đăng ký nhanh bằng Google không thành công.';
        this.toastService.error(message);
      }
    });
  }
}

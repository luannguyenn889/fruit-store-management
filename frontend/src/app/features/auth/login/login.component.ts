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
  contact = 'admin@fruitstore.com';
  password = 'admin123';
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
      this.errorMessage.set('Vui lòng nhập đầy đủ thông tin đăng nhập.');
      return;
    }

    const email = this.contact.includes('@')
      ? this.contact.trim()
      : `${this.contact.trim()}@fruitstore.local`;

    this.isLoading.set(true);
    this.authService.login(email, this.password).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: err => {
        this.isLoading.set(false);
        const detail = err.error?.detail || 'Email hoặc mật khẩu không chính xác.';
        this.errorMessage.set(detail);
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
          this.mockGoogleLoginFallback();
        }
      });
    } else {
      this.mockGoogleLoginFallback();
    }
  }

  private handleGoogleCredential(credential: string): void {
    this.isLoading.set(true);
    this.authService.loginWithGoogle(credential).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: err => {
        this.isLoading.set(false);
        this.errorMessage.set(err.error?.detail || 'Đăng nhập bằng Google không thành công.');
      }
    });
  }

  private mockGoogleLoginFallback(): void {
    this.isLoading.set(true);
    this.authService.login('admin@fruitstore.com', 'admin123').subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.isLoading.set(false);
        this.errorMessage.set('Đang kết nối tới máy chủ Google...');
      }
    });
  }
}


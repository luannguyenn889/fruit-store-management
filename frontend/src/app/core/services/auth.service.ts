/**
 * Module: core/services/auth.service.ts
 * Nhiệm vụ: Quản lý trạng thái xác thực người dùng (Authentication & RBAC State) tại Frontend.
 *           Giao tiếp với Auth Service thông qua API Gateway (`http://localhost:8000/api/v1/auth`).
 *           Lưu trữ JWT Access Token, thông tin hồ sơ người dùng và cung cấp các hàm kiểm tra vai trò.
 */

import { Injectable, signal, computed } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Router } from '@angular/router';

export interface RoleInfo {
  id: number;
  code: string;
  name: string;
  description?: string | null;
}

export interface User {
  id: string;
  email: string;
  phone?: string | null;
  full_name: string;
  status: string;
  roles: (RoleInfo | string)[];
  created_at?: string;
  updated_at?: string;
  last_login_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

/**
 * Payload đăng ký tài khoản công khai.
 * Bảo mật (FR-A01): Không gửi `role_code` từ client; Backend tự động gán vai trò `CUSTOMER`.
 */
export interface UserRegisterPayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/auth';
  readonly googleClientId =
    '569426721711-6ub3hgomi74b201otif6cpe3oq53s5fj.apps.googleusercontent.com';

  private readonly tokenKey = 'fruitstore_access_token';
  private readonly userKey = 'fruitstore_user';

  // Quản lý trạng thái người dùng phản ứng bằng Angular Signals
  private readonly currentUserSignal = signal<User | null>(this.getStoredUser());
  readonly currentUser = computed(() => this.currentUserSignal());
  readonly isLoggedIn = computed(() => !!this.currentUserSignal());

  constructor(private http: HttpClient, private router: Router) {}

  /** Đăng nhập bằng Email/SĐT và mật khẩu qua API Gateway */
  login(email: string, password: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.apiUrl}/login`, { email, password })
      .pipe(tap(response => this.handleAuthSuccess(response)));
  }

  /** Đăng ký tài khoản khách hàng mới (Mặc định nhận vai trò CUSTOMER từ Backend) */
  register(payload: UserRegisterPayload): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/register`, payload);
  }

  /** Đăng nhập bằng Google ID Token đã được Google ký số */
  loginWithGoogle(credential: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.apiUrl}/google`, { credential })
      .pipe(tap(response => this.handleAuthSuccess(response)));
  }

  /** Lấy thông tin hồ sơ người dùng hiện tại từ `/api/v1/auth/me` */
  getProfile(): Observable<User> {
    return this.http
      .get<User>(`${this.apiUrl}/me`, { headers: this.getAuthHeaders() })
      .pipe(
        tap(user => {
          this.currentUserSignal.set(user);
          localStorage.setItem(this.userKey, JSON.stringify(user));
        })
      );
  }

  /** Đăng xuất khỏi hệ thống và xóa thông tin phiên lưu cục bộ */
  logout(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.currentUserSignal.set(null);
    this.router.navigate(['/login']);
  }

  /** Trả về JWT Access Token hiện tại */
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  /** Tạo HttpHeaders đính kèm Bearer JWT cho các request cần xác thực */
  getAuthHeaders(): HttpHeaders {
    const token = this.getToken();
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
  }

  /** Kiểm tra người dùng hiện tại có sở hữu một trong các mã vai trò được chỉ định không */
  hasRole(...allowedCodes: string[]): boolean {
    const user = this.currentUserSignal();
    if (!user || !user.roles) return false;
    const upperAllowed = new Set(allowedCodes.map(c => c.toUpperCase()));
    return user.roles.some(r => {
      const code = typeof r === 'string' ? r : r.code;
      return upperAllowed.has(code.toUpperCase());
    });
  }

  /** Trả về tên hiển thị vai trò chính bằng tiếng Việt của người dùng hiện tại */
  getPrimaryRoleLabel(): string {
    const user = this.currentUserSignal();
    if (!user || !user.roles || user.roles.length === 0) {
      return 'Khách hàng';
    }
    const first = user.roles[0];
    if (typeof first === 'string') {
      return first;
    }
    return first.name || first.code;
  }

  private handleAuthSuccess(response: TokenResponse): void {
    localStorage.setItem(this.tokenKey, response.access_token);
    localStorage.setItem(this.userKey, JSON.stringify(response.user));
    this.currentUserSignal.set(response.user);
  }

  private getStoredUser(): User | null {
    const stored = localStorage.getItem(this.userKey);
    if (!stored) return null;
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  }
}

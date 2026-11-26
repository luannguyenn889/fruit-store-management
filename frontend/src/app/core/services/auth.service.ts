/**
 * Module: core/services/auth.service.ts
 * Nhiệm vụ: Quản lý trạng thái xác thực, gia hạn Refresh Token (FR-A02), đăng xuất thu hồi phiên (FR-A03),
 *           cập nhật hồ sơ/đổi mật khẩu và các API quản trị nhân sự (ADMIN) thông qua API Gateway
 *           (`http://localhost:8000/api/v1/auth`).
 */

import { Injectable, signal, computed } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, catchError, of, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

export const INTERNAL_ROLES = ['ADMIN', 'MANAGER', 'STAFF', 'WAREHOUSE'] as const;

export type UserStatus = 'ACTIVE' | 'LOCKED' | 'INACTIVE';

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
  status: UserStatus | string;
  roles: (RoleInfo | string)[];
  created_at?: string;
  updated_at?: string;
  last_login_at?: string | null;
}

export interface PaginatedUsers {
  items: User[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AuditLogItem {
  id: string;
  actor_user_id?: string | null;
  target_user_id?: string | null;
  action: string;
  old_value?: string | null;
  new_value?: string | null;
  request_id?: string | null;
  ip_address?: string | null;
  created_at: string;
}

export interface PaginatedAuditLogs {
  items: AuditLogItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AuditLogFilterParams {
  page?: number;
  size?: number;
  action?: string;
  target_user_id?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string | null;
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

export interface UpdateProfilePayload {
  full_name?: string;
  phone?: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface AdminUserCreatePayload {
  email: string;
  phone?: string;
  full_name: string;
  password: string;
  role_codes: string[];
}

export interface UserFilterParams {
  page?: number;
  size?: number;
  q?: string;
  role_code?: string;
  status?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly apiUrl = `${environment.apiBaseUrl}/auth`;
  readonly googleClientId = environment.googleClientId;

  private readonly tokenKey = 'fruitstore_access_token';
  private readonly refreshTokenKey = 'fruitstore_refresh_token';
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

  /** Gia hạn Access Token bằng Refresh Token đang lưu trữ (FR-A02) */
  refreshSession(): Observable<TokenResponse> {
    const refreshToken = this.getRefreshToken();
    return this.http
      .post<TokenResponse>(`${this.apiUrl}/refresh`, {
        refresh_token: refreshToken
      })
      .pipe(tap(response => this.handleAuthSuccess(response)));
  }

  /** Lấy thông tin hồ sơ người dùng hiện tại từ `/api/v1/auth/me` */
  getProfile(): Observable<User> {
    return this.http
      .get<User>(`${this.apiUrl}/me`, { headers: this.getAuthHeaders() })
      .pipe(tap(user => this.persistUser(user)));
  }

  /** Cập nhật hồ sơ cá nhân (`PATCH /api/v1/auth/me`) */
  updateProfile(payload: UpdateProfilePayload): Observable<User> {
    return this.http
      .patch<User>(`${this.apiUrl}/me`, payload, {
        headers: this.getAuthHeaders()
      })
      .pipe(tap(user => this.persistUser(user)));
  }

  /** Đổi mật khẩu cá nhân (`POST /api/v1/auth/change-password`) */
  changePassword(
    payload: ChangePasswordPayload
  ): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.apiUrl}/change-password`,
      payload,
      { headers: this.getAuthHeaders() }
    );
  }

  /** Yêu cầu gửi email đặt lại mật khẩu (FR-A10) */
  forgotPassword(email: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/forgot-password`, {
      email: email.trim()
    });
  }

  /** Đặt lại mật khẩu mới bằng mã OTP 6 chữ số nhận từ Email (FR-A10) */
  resetPassword(
    email: string,
    otpCode: string,
    newPassword: string
  ): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/reset-password`, {
      email: email.trim(),
      otp_code: otpCode.trim(),
      new_password: newPassword
    });
  }

  // ===========================================================================
  // QUẢN TRỊ NHÂN SỰ & PHÂN QUYỀN (CHỈ ADMIN)
  // ===========================================================================
  /** Lấy danh mục vai trò RBAC */
  getRoles(): Observable<RoleInfo[]> {
    return this.http.get<RoleInfo[]>(`${this.apiUrl}/roles`, {
      headers: this.getAuthHeaders()
    });
  }

  /** Tra cứu, tìm kiếm và lọc danh sách tài khoản người dùng (Chỉ ADMIN) */
  getUsers(filters: UserFilterParams = {}): Observable<PaginatedUsers> {
    let params = new HttpParams()
      .set('page', String(filters.page ?? 1))
      .set('size', String(filters.size ?? 20));
    if (filters.q && filters.q.trim()) {
      params = params.set('q', filters.q.trim());
    }
    if (filters.role_code) {
      params = params.set('role_code', filters.role_code);
    }
    if (filters.status) {
      params = params.set('status', filters.status);
    }
    return this.http.get<PaginatedUsers>(`${this.apiUrl}/users`, {
      headers: this.getAuthHeaders(),
      params
    });
  }

  /** Tạo tài khoản nhân sự nội bộ mới (Chỉ ADMIN) */
  createUser(payload: AdminUserCreatePayload): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/users`, payload, {
      headers: this.getAuthHeaders()
    });
  }

  /** Cập nhật danh sách vai trò cho tài khoản (Chỉ ADMIN) */
  updateUserRoles(userId: string, roleCodes: string[]): Observable<User> {
    return this.http.patch<User>(
      `${this.apiUrl}/users/${userId}/roles`,
      { role_codes: roleCodes },
      { headers: this.getAuthHeaders() }
    );
  }

  /** Khóa / mở khóa / ngừng hoạt động tài khoản (Chỉ ADMIN) */
  updateUserStatus(userId: string, status: UserStatus): Observable<User> {
    return this.http.patch<User>(
      `${this.apiUrl}/users/${userId}/status`,
      { status },
      { headers: this.getAuthHeaders() }
    );
  }

  /** Tra cứu nhật ký kiểm toán bảo mật/quản trị bất biến (Chỉ ADMIN - FR-H01) */
  getAuditLogs(filters: AuditLogFilterParams = {}): Observable<PaginatedAuditLogs> {
    let params = new HttpParams()
      .set('page', String(filters.page ?? 1))
      .set('size', String(filters.size ?? 20));
    if (filters.action) {
      params = params.set('action', filters.action);
    }
    if (filters.target_user_id && filters.target_user_id.trim()) {
      params = params.set('target_user_id', filters.target_user_id.trim());
    }
    return this.http.get<PaginatedAuditLogs>(`${this.apiUrl}/audit-logs`, {
      headers: this.getAuthHeaders(),
      params
    });
  }

  /**
   * Đăng xuất khỏi hệ thống: gọi `POST /api/v1/auth/logout` thu hồi Refresh Token ở backend (FR-A03),
   * sau đó xóa toàn bộ thông tin phiên cục bộ và điều hướng về `/login`.
   */
  logout(): void {
    const token = this.getToken();
    const refreshToken = this.getRefreshToken();

    if (token) {
      this.http
        .post(
          `${this.apiUrl}/logout`,
          { refresh_token: refreshToken },
          { headers: this.getAuthHeaders() }
        )
        .pipe(catchError(() => of(null)))
        .subscribe(() => this.clearLocalSession());
    } else {
      this.clearLocalSession();
    }
  }

  /** Xóa phiên lưu cục bộ mà không gọi lại API (dùng khi refresh token đã hết hạn) */
  clearLocalSession(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshTokenKey);
    localStorage.removeItem(this.userKey);
    this.currentUserSignal.set(null);
    this.router.navigate(['/login']);
  }

  /** Trả về JWT Access Token hiện tại */
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  /** Trả về Refresh Token hiện tại */
  getRefreshToken(): string | null {
    return localStorage.getItem(this.refreshTokenKey);
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

  /** Kiểm tra tài khoản hiện tại có thuộc nhóm nhân sự nội bộ (ADMIN/MANAGER/STAFF/WAREHOUSE) không */
  isInternalUser(): boolean {
    return this.hasRole(...INTERNAL_ROLES);
  }

  /** Kiểm tra tài khoản đã đăng nhập nhưng chỉ có vai trò khách hàng (CUSTOMER) */
  isCustomerOnly(): boolean {
    return this.isLoggedIn() && !this.isInternalUser();
  }

  /** Xác định route mặc định sau đăng nhập dựa theo vai trò tài khoản */
  getDefaultRoute(): string {
    return this.isInternalUser() ? '/dashboard' : '/shop';
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
    if (response.refresh_token) {
      localStorage.setItem(this.refreshTokenKey, response.refresh_token);
    }
    this.persistUser(response.user);
  }

  private persistUser(user: User): void {
    localStorage.setItem(this.userKey, JSON.stringify(user));
    this.currentUserSignal.set(user);
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

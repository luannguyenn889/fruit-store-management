import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Router } from '@angular/router';

export interface User {
  id: string;
  email: string;
  phone?: string | null;
  full_name: string;
  status: string;
  roles: string[];
  created_at?: string;
  last_login_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface UserRegisterPayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  role_code?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/auth';
  readonly googleClientId = '569426721711-6ub3hgomi74b201otif6cpe3oq53s5fj.apps.googleusercontent.com';

  private readonly tokenKey = 'fruitstore_access_token';
  private readonly userKey = 'fruitstore_user';

  // Reactive state using Angular Signals
  private readonly currentUserSignal = signal<User | null>(this.getStoredUser());
  readonly currentUser = computed(() => this.currentUserSignal());
  readonly isLoggedIn = computed(() => !!this.currentUserSignal());

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.apiUrl}/login`, { email, password }).pipe(
      tap(response => this.handleAuthSuccess(response))
    );
  }

  register(payload: UserRegisterPayload): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/register`, payload);
  }

  loginWithGoogle(credential: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.apiUrl}/google`, { credential }).pipe(
      tap(response => this.handleAuthSuccess(response))
    );
  }

  getProfile(): Observable<User> {
    const headers = { Authorization: `Bearer ${this.getToken()}` };
    return this.http.get<User>(`${this.apiUrl}/me`, { headers }).pipe(
      tap(user => {
        this.currentUserSignal.set(user);
        localStorage.setItem(this.userKey, JSON.stringify(user));
      })
    );
  }

  logout(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.currentUserSignal.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
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


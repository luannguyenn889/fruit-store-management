/**
 * Module: core/interceptors/auth.interceptor.ts
 * Nhiệm vụ: Angular Functional HTTP Interceptor tự động xử lý xác thực và gia hạn phiên (FR-A02):
 *           1. Tự động đính kèm header `Authorization: Bearer <access_token>` cho các request gửi tới API Gateway.
 *           2. Khi gặp lỗi `401 Unauthorized` (Access Token hết hạn sau 30 phút), tự động gọi `POST /api/v1/auth/refresh`
 *              để xoay vòng lấy Access Token mới và gửi lại request ban đầu (gom hàng đợi chống gọi trùng).
 *           3. Nếu Refresh Token cũng hết hạn hoặc bị thu hồi, xóa phiên cục bộ và điều hướng về `/login`.
 */

import { inject } from '@angular/core';
import {
  HttpErrorResponse,
  HttpInterceptorFn,
  HttpRequest
} from '@angular/common/http';
import {
  BehaviorSubject,
  catchError,
  filter,
  switchMap,
  take,
  throwError
} from 'rxjs';
import { AuthService } from '../services/auth.service';

const GATEWAY_PREFIX = 'http://localhost:8000/api/v1/';
const SKIP_REFRESH_PATHS = [
  '/auth/login',
  '/auth/register',
  '/auth/google',
  '/auth/refresh',
  '/auth/logout'
];

// Biến trạng thái dùng chung để đảm bảo chỉ có 1 lời gọi /auth/refresh tại cùng một thời điểm
let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<string | null>(null);

function attachToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`
    }
  });
}

function shouldSkipRefresh(url: string): boolean {
  return SKIP_REFRESH_PATHS.some(segment => url.includes(segment));
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  if (!req.url.startsWith(GATEWAY_PREFIX)) {
    return next(req);
  }

  let outgoingReq = req;
  const accessToken = authService.getToken();
  if (accessToken && !req.headers.has('Authorization') && !shouldSkipRefresh(req.url)) {
    outgoingReq = attachToken(req, accessToken);
  }

  return next(outgoingReq).pipe(
    catchError((error: unknown) => {
      if (
        !(error instanceof HttpErrorResponse) ||
        error.status !== 401 ||
        shouldSkipRefresh(req.url)
      ) {
        return throwError(() => error);
      }

      const currentRefreshToken = authService.getRefreshToken();
      if (!currentRefreshToken) {
        authService.clearLocalSession();
        return throwError(() => error);
      }

      if (!isRefreshing) {
        isRefreshing = true;
        refreshTokenSubject.next(null);

        return authService.refreshSession().pipe(
          switchMap(res => {
            isRefreshing = false;
            refreshTokenSubject.next(res.access_token);
            return next(attachToken(req, res.access_token));
          }),
          catchError(refreshErr => {
            isRefreshing = false;
            authService.clearLocalSession();
            return throwError(() => refreshErr);
          })
        );
      }

      // Đợi lời gọi refresh đang diễn ra hoàn tất rồi thử lại request với token mới
      return refreshTokenSubject.pipe(
        filter((token): token is string => token !== null),
        take(1),
        switchMap(newToken => next(attachToken(req, newToken)))
      );
    })
  );
};

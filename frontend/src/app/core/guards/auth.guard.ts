/**
 * Module: core/guards/auth.guard.ts
 * Nhiệm vụ: Kiểm tra trạng thái xác thực JWT trước khi cho phép truy cập route cần đăng nhập
 *           (`authGuard`) và điều hướng trang gốc `/` theo vai trò (`homeRedirectGuard`).
 */

import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.getToken()) {
    return true;
  }

  return router.createUrlTree(['/login']);
};

export const homeRedirectGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.getToken() && authService.isInternalUser()) {
    return router.createUrlTree(['/dashboard']);
  }

  return router.createUrlTree(['/shop']);
};

/**
 * Module: core/guards/role.guard.ts
 * Nhiệm vụ: Bảo vệ các route khu vực quản trị nội bộ theo vai trò RBAC (`ADMIN`, `MANAGER`,
 *           `STAFF`, `WAREHOUSE`). Tài khoản `CUSTOMER` sẽ bị chuyển hướng về `/shop`.
 */

import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ToastService } from '../services/toast.service';

/** Tạo Route Guard kiểm tra người dùng hiện tại có thuộc tập vai trò được phép không */
export function roleGuard(allowedRoles: readonly string[]): CanActivateFn {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);
    const toastService = inject(ToastService);

    if (!authService.getToken()) {
      return router.createUrlTree(['/login']);
    }

    if (authService.hasRole(...allowedRoles)) {
      return true;
    }

    toastService.warning('Bạn không có quyền truy cập khu vực này.');
    return router.createUrlTree([authService.getDefaultRoute()]);
  };
}

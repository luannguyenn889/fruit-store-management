/**
 * Module: app.routes.ts
 * Nhiệm vụ: Định nghĩa bảng định tuyến (Routing) và phân tách khu vực theo vai trò RBAC:
 *           - `/shop`: Cửa hàng trực tuyến (Storefront) công khai cho Khách hàng.
 *           - `/profile`: Hồ sơ cá nhân & đổi mật khẩu cho Khách hàng (yêu cầu đăng nhập).
 *           - `/login`, `/register`: Màn hình xác thực.
 *           - `/dashboard`, `/catalog`, `/inventory`, `/procurement`, `/users`: Khu vực quản trị nội bộ (chặn theo `roleGuard`).
 */

import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login.component';
import { RegisterComponent } from './features/auth/register/register.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { CatalogComponent } from './features/catalog/catalog.component';
import { InventoryComponent } from './features/inventory/inventory.component';
import { ProcurementComponent } from './features/procurement/procurement.component';
import { UsersComponent } from './features/users/users.component';
import { ShopComponent } from './features/shop/shop.component';
import { CustomerProfileComponent } from './features/profile/customer-profile.component';
import { authGuard, homeRedirectGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { INTERNAL_ROLES } from './core/services/auth.service';

export const routes: Routes = [
  { path: '', pathMatch: 'full', component: ShopComponent, canActivate: [homeRedirectGuard] },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'shop', component: ShopComponent },
  { path: 'profile', component: CustomerProfileComponent, canActivate: [authGuard] },
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [authGuard, roleGuard(INTERNAL_ROLES)]
  },
  {
    path: 'catalog',
    component: CatalogComponent,
    canActivate: [authGuard, roleGuard(INTERNAL_ROLES)]
  },
  {
    path: 'inventory',
    component: InventoryComponent,
    canActivate: [authGuard, roleGuard(INTERNAL_ROLES)]
  },
  {
    path: 'procurement',
    component: ProcurementComponent,
    canActivate: [authGuard, roleGuard(['ADMIN', 'MANAGER', 'WAREHOUSE'])]
  },
  {
    path: 'users',
    component: UsersComponent,
    canActivate: [authGuard, roleGuard(INTERNAL_ROLES)]
  },
  { path: '**', redirectTo: '' }
];

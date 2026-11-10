/**
 * Module: app.routes.ts
 * Nhiệm vụ: Định nghĩa bảng định tuyến (Routing) cho ứng dụng Angular FruitStore:
 *           - `/login`, `/register`: Màn hình xác thực.
 *           - `/dashboard`: Màn hình tổng quan quản trị cửa hàng.
 *           - `/catalog`: Màn hình quản lý Danh mục, Sản phẩm & Lịch sử Đơn giá (Catalog Service).
 */

import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login.component';
import { RegisterComponent } from './features/auth/register/register.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { CatalogComponent } from './features/catalog/catalog.component';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'catalog', component: CatalogComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: 'dashboard' },
];

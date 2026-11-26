/**
 * Module: features/audit-logs/audit-logs.component.ts
 * Nhiệm vụ: Màn hình tra cứu Nhật ký kiểm toán (Audit Log) bất biến cho Quản trị viên (`/audit-logs`, FR-H01).
 *           Hiển thị các thao tác nhạy cảm: tạo nhân sự, phân quyền RBAC, khóa/mở khóa tài khoản,
 *           khóa tạm thời brute-force và đặt lại mật khẩu qua OTP.
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  AuditLogItem,
  AuthService
} from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { AdminLayoutComponent } from '../../core/layout/admin-layout/admin-layout.component';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';

interface ActionMeta {
  label: string;
  tone: 'info' | 'warning' | 'danger' | 'success';
}

const ACTION_META_MAP: Record<string, ActionMeta> = {
  ADMIN_CREATE_USER: { label: 'Tạo nhân sự mới', tone: 'success' },
  UPDATE_USER_ROLES: { label: 'Cập nhật vai trò RBAC', tone: 'info' },
  UPDATE_USER_STATUS: { label: 'Đổi trạng thái tài khoản', tone: 'warning' },
  ACCOUNT_LOCKED_BRUTE_FORCE: { label: 'Khóa tạm Brute-force', tone: 'danger' },
  PASSWORD_RESET_COMPLETED: { label: 'Đặt lại mật khẩu OTP', tone: 'info' }
};

@Component({
  selector: 'app-audit-logs',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AdminLayoutComponent,
    SkeletonLoaderComponent,
    PaginationComponent
  ],
  templateUrl: './audit-logs.component.html',
  styleUrls: ['./audit-logs.component.css']
})
export class AuditLogsComponent implements OnInit {
  logs = signal<AuditLogItem[]>([]);
  totalLogs = signal(0);
  currentPage = signal(1);
  pageSize = signal(20);
  totalPages = signal(1);
  isLoading = signal(false);
  loadError = signal('');

  filterAction = '';
  filterTargetUserId = '';

  readonly actionOptions = [
    { value: '', label: 'Tất cả hành động' },
    { value: 'ADMIN_CREATE_USER', label: 'Tạo nhân sự mới' },
    { value: 'UPDATE_USER_ROLES', label: 'Cập nhật vai trò RBAC' },
    { value: 'UPDATE_USER_STATUS', label: 'Đổi trạng thái tài khoản' },
    { value: 'ACCOUNT_LOCKED_BRUTE_FORCE', label: 'Khóa tạm Brute-force' },
    { value: 'PASSWORD_RESET_COMPLETED', label: 'Đặt lại mật khẩu OTP' }
  ];

  constructor(
    private authService: AuthService,
    private toast: ToastService
  ) {}

  ngOnInit(): void {
    this.loadLogs(1);
  }

  loadLogs(page = 1): void {
    this.isLoading.set(true);
    this.loadError.set('');

    const targetId = this.filterTargetUserId.trim();
    if (
      targetId &&
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(targetId)
    ) {
      this.isLoading.set(false);
      this.loadError.set('ID người dùng đích phải đúng định dạng UUID.');
      return;
    }

    this.authService
      .getAuditLogs({
        page,
        size: this.pageSize(),
        action: this.filterAction || undefined,
        target_user_id: targetId || undefined
      })
      .subscribe({
        next: res => {
          this.logs.set(res.items);
          this.totalLogs.set(res.total);
          this.currentPage.set(res.page);
          this.totalPages.set(res.pages || 1);
          this.isLoading.set(false);
        },
        error: err => {
          const msg =
            err?.error?.message ||
            err?.error?.detail ||
            'Không thể tải nhật ký kiểm toán từ Auth Service.';
          this.loadError.set(msg);
          this.toast.error(msg);
          this.isLoading.set(false);
        }
      });
  }

  applyFilters(): void {
    this.loadLogs(1);
  }

  resetFilters(): void {
    this.filterAction = '';
    this.filterTargetUserId = '';
    this.loadLogs(1);
  }

  filterByTargetUser(userId: string | null | undefined): void {
    if (!userId) {
      return;
    }
    this.filterTargetUserId = userId;
    this.loadLogs(1);
  }

  onPageChange(page: number): void {
    this.loadLogs(page);
  }

  getActionLabel(action: string): string {
    return ACTION_META_MAP[action]?.label ?? action;
  }

  getActionTone(action: string): string {
    return ACTION_META_MAP[action]?.tone ?? 'info';
  }

  shortId(value: string | null | undefined): string {
    if (!value) {
      return 'Hệ thống';
    }
    return value.length > 10 ? `${value.slice(0, 8)}…` : value;
  }

  formatPayload(raw: string | null | undefined): string {
    if (!raw) {
      return '—';
    }
    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      return Object.entries(parsed)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v ?? 'null')}`)
        .join(' · ');
    } catch {
      return raw;
    }
  }
}

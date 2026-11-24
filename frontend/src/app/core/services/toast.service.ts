/**
 * Module: core/services/toast.service.ts
 * Nhiệm vụ: Dịch vụ thông báo Toast toàn cục (Global Toast Service) thay thế các hộp alert cố định.
 *           Quản lý hàng đợi thông báo theo Angular Signals (`success`, `error`, `warning`, `info`),
 *           tự động đóng sau thời gian đủ đọc (4.5s–5.5s) và cho phép người dùng đóng thủ công.
 */

import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: number;
  type: ToastType;
  title: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private nextId = 1;
  private readonly toastsSignal = signal<ToastItem[]>([]);
  readonly toasts = this.toastsSignal.asReadonly();

  /** Hiển thị thông báo thành công (chỉ gọi sau khi Server xác nhận) */
  success(message: string, title = 'Thành công', durationMs = 4500): void {
    this.show('success', title, message, durationMs);
  }

  /** Hiển thị thông báo lỗi (validation, phân quyền hoặc lỗi hệ thống) */
  error(message: string, title = 'Không thể thực hiện', durationMs = 5500): void {
    this.show('error', title, message, durationMs);
  }

  /** Hiển thị cảnh báo nghiệp vụ */
  warning(message: string, title = 'Lưu ý', durationMs = 5000): void {
    this.show('warning', title, message, durationMs);
  }

  /** Hiển thị thông tin trung tính */
  info(message: string, title = 'Thông báo', durationMs = 4500): void {
    this.show('info', title, message, durationMs);
  }

  /** Đóng một thông báo Toast theo ID */
  dismiss(id: number): void {
    this.toastsSignal.update(list => list.filter(t => t.id !== id));
  }

  /** Xóa toàn bộ thông báo Toast đang hiển thị */
  clear(): void {
    this.toastsSignal.set([]);
  }

  private show(
    type: ToastType,
    title: string,
    message: string,
    durationMs: number
  ): void {
    const cleanMsg = (message || '').trim();
    if (!cleanMsg) return;

    const id = this.nextId++;
    const item: ToastItem = { id, type, title, message: cleanMsg };

    // Giới hạn tối đa 4 toast hiển thị cùng lúc để giao diện luôn gọn gàng
    this.toastsSignal.update(list => [...list.slice(-3), item]);

    if (durationMs > 0) {
      setTimeout(() => this.dismiss(id), durationMs);
    }
  }
}

/**
 * Module: shared/components/toast-container/toast-container.component.ts
 * Nhiệm vụ: Thành phần hiển thị danh sách thông báo Toast nổi ở góc trên bên phải toàn ứng dụng.
 *           Sử dụng icon ngữ nghĩa kèm tiêu đề và nội dung rõ ràng (không chỉ dựa vào màu sắc).
 */

import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './toast-container.component.html',
  styleUrls: ['./toast-container.component.css']
})
export class ToastContainerComponent {
  constructor(public toastService: ToastService) {}
}

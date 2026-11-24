/**
 * Module: shared/components/pagination/pagination.component.ts
 * Nhiệm vụ: Thành phần phân trang (Pagination UI) tái sử dụng cho các bảng dữ liệu lớn
 *           trên `/catalog` và `/users` (Mục 5.2 `UI_UX_DESIGN_RULES_FruitStore.md`).
 */

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pagination.component.html',
  styleUrls: ['./pagination.component.css']
})
export class PaginationComponent {
  @Input() currentPage = 1;
  @Input() totalPages = 1;
  @Input() totalItems = 0;
  @Input() pageSize = 20;

  @Output() pageChange = new EventEmitter<number>();

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.currentPage) {
      return;
    }
    this.pageChange.emit(page);
  }
}

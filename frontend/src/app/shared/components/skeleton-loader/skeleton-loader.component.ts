/**
 * Module: shared/components/skeleton-loader/skeleton-loader.component.ts
 * Nhiệm vụ: Thành phần Skeleton Loading tái sử dụng (thay thế spinner tròn đơn điệu)
 *           hỗ trợ các biến thể bố cục: `table`, `kpi`, `list`, `history`.
 *           Giúp giảm cảm giác giật bố cục (CLS) và tạo trải nghiệm chuyên nghiệp.
 */

import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type SkeletonVariant = 'table' | 'kpi' | 'list' | 'history';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './skeleton-loader.component.html',
  styleUrls: ['./skeleton-loader.component.css']
})
export class SkeletonLoaderComponent {
  @Input() variant: SkeletonVariant = 'table';
  @Input() rows = 5;
  @Input() columns = 6;

  get rowIndices(): number[] {
    return Array.from({ length: this.rows }, (_, i) => i);
  }

  get colIndices(): number[] {
    return Array.from({ length: this.columns }, (_, i) => i);
  }
}

/**
 * Module: core/services/catalog.service.ts
 * Nhiệm vụ: Lớp Data-Access giao tiếp với Catalog Service thông qua API Gateway
 *           (`http://localhost:8000/api/v1/catalog`).
 *           Cung cấp các phương thức type-safe cho Danh mục (`Category`), Sản phẩm (`Product`),
 *           Cập nhật đơn giá nguyên tử (`POST /products/{id}/price`) và Lịch sử giá (`PriceHistory`).
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export type ProductUnit = 'kg' | 'hop' | 'qua';
export type StorageCondition = 'AMBIENT' | 'COOL_2_8C' | 'COOL_8_12C';
export type ProductStatus = 'ACTIVE' | 'INACTIVE' | 'OUT_OF_SEASON';

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryCreatePayload {
  name: string;
  slug?: string;
  description?: string;
  is_active?: boolean;
}

export interface Product {
  id: string;
  category_id: string;
  category_name?: string | null;
  sku: string;
  name: string;
  slug: string;
  unit: ProductUnit;
  price: string; // Decimal chuỗi chính xác từ Backend, ví dụ "65000.00"
  origin?: string | null;
  default_shelf_life_days: number;
  storage_condition: StorageCondition;
  description?: string | null;
  status: ProductStatus;
  created_at: string;
  updated_at: string;
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ProductCreatePayload {
  category_id: string;
  sku: string;
  name: string;
  unit: ProductUnit;
  price: string;
  origin?: string;
  default_shelf_life_days: number;
  storage_condition: StorageCondition;
  description?: string;
  status?: ProductStatus;
}

export interface ProductUpdatePayload {
  category_id?: string;
  name?: string;
  unit?: ProductUnit;
  origin?: string;
  default_shelf_life_days?: number;
  storage_condition?: StorageCondition;
  description?: string;
  status?: ProductStatus;
}

export interface PriceUpdatePayload {
  new_price: string;
  reason: string;
}

export interface PriceHistoryRecord {
  id: string;
  product_id: string;
  old_price: string;
  new_price: string;
  changed_by_user_id?: string | null;
  reason?: string | null;
  effective_at: string;
}

export interface ProductFilterParams {
  page?: number;
  size?: number;
  q?: string;
  category_id?: string;
  status?: string;
}

@Injectable({
  providedIn: 'root'
})
export class CatalogService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/catalog';

  constructor(private http: HttpClient, private authService: AuthService) {}

  /** Lấy danh sách toàn bộ danh mục trái cây (Công khai) */
  getCategories(): Observable<Category[]> {
    return this.http.get<Category[]>(`${this.apiUrl}/categories`);
  }

  /** Tạo danh mục mới (Yêu cầu quyền MANAGER hoặc ADMIN) */
  createCategory(payload: CategoryCreatePayload): Observable<Category> {
    return this.http.post<Category>(`${this.apiUrl}/categories`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }

  /** Xóa danh mục chưa có sản phẩm (Yêu cầu quyền MANAGER hoặc ADMIN) */
  deleteCategory(categoryId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/categories/${categoryId}`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  /** Tìm kiếm, lọc và phân trang danh sách sản phẩm trái cây (Công khai) */
  getProducts(filters: ProductFilterParams = {}): Observable<PaginatedProducts> {
    let params = new HttpParams()
      .set('page', String(filters.page ?? 1))
      .set('size', String(filters.size ?? 20));

    if (filters.q && filters.q.trim()) {
      params = params.set('q', filters.q.trim());
    }
    if (filters.category_id) {
      params = params.set('category_id', filters.category_id);
    }
    if (filters.status) {
      params = params.set('status', filters.status);
    }

    return this.http.get<PaginatedProducts>(`${this.apiUrl}/products`, { params });
  }

  /** Lấy chi tiết một sản phẩm theo UUID */
  getProductById(productId: string): Observable<Product> {
    return this.http.get<Product>(`${this.apiUrl}/products/${productId}`);
  }

  /** Tạo sản phẩm trái cây mới kèm giá khởi tạo (Chỉ MANAGER / ADMIN) */
  createProduct(payload: ProductCreatePayload): Observable<Product> {
    return this.http.post<Product>(`${this.apiUrl}/products`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }

  /** Cập nhật thông tin mô tả, xuất xứ, đơn vị tính, bảo quản - Không đổi giá (Chỉ MANAGER / ADMIN) */
  updateProduct(productId: string, payload: ProductUpdatePayload): Observable<Product> {
    return this.http.patch<Product>(`${this.apiUrl}/products/${productId}`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }

  /** Ngừng kinh doanh sản phẩm -> INACTIVE (Chỉ MANAGER / ADMIN) */
  deactivateProduct(productId: string): Observable<Product> {
    return this.http.post<Product>(
      `${this.apiUrl}/products/${productId}/deactivate`,
      {},
      { headers: this.authService.getAuthHeaders() }
    );
  }

  /** Cập nhật đơn giá bán và ghi nhận PriceHistory nguyên tử (Chỉ MANAGER / ADMIN) */
  updateProductPrice(
    productId: string,
    payload: PriceUpdatePayload
  ): Observable<Product> {
    return this.http.post<Product>(
      `${this.apiUrl}/products/${productId}/price`,
      payload,
      { headers: this.authService.getAuthHeaders() }
    );
  }

  /** Lấy danh sách lịch sử biến động đơn giá của sản phẩm */
  getPriceHistory(productId: string): Observable<PriceHistoryRecord[]> {
    return this.http.get<PriceHistoryRecord[]>(
      `${this.apiUrl}/products/${productId}/price-history`
    );
  }
}


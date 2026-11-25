/**
 * Module: core/services/inventory.service.ts
 * Nhiệm vụ: Lớp Data-Access giao tiếp với Inventory Service (:8003) thông qua API Gateway
 *           (`${environment.apiBaseUrl}/inventory`).
 *           Cung cấp các phương thức type-safe cho Nhà cung cấp, Phiếu nhập kho,
 *           Lô hàng FEFO, Tổng hợp tồn kho, Sổ cái biến động, Hao hụt và Điều chỉnh kiểm kê.
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

// =============================================================================
// 1. KIỂU DỮ LIỆU NHÀ CUNG CẤP (SUPPLIERS - FR-C01)
// =============================================================================
export interface Supplier {
  id: string;
  code: string;
  name: string;
  phone?: string | null;
  address?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupplierListResponse {
  items: Supplier[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface SupplierCreatePayload {
  code?: string;
  name: string;
  phone?: string;
  address?: string;
  is_active?: boolean;
}

export interface SupplierUpdatePayload {
  code?: string;
  name?: string;
  phone?: string;
  address?: string;
  is_active?: boolean;
}

export interface SupplierFilterParams {
  q?: string;
  is_active?: boolean | null;
  page?: number;
  limit?: number;
}

// =============================================================================
// 2. KIỂU DỮ LIỆU PHIẾU NHẬP KHO (PURCHASE ORDERS - FR-C02, FR-C03)
// =============================================================================
export type PurchaseOrderStatus = 'DRAFT' | 'RECEIVED' | 'CANCELLED';

export interface PurchaseItem {
  id: string;
  purchase_order_id: string;
  product_id: string;
  quantity_ordered: string;
  quantity_received: string;
  unit_cost: string;
  line_total: string;
  expected_expiry_date?: string | null;
}

export interface PurchaseOrder {
  id: string;
  po_number: string;
  supplier_id: string;
  supplier_code?: string | null;
  supplier_name?: string | null;
  status: PurchaseOrderStatus | string;
  total_amount: string;
  created_by_user_id: string;
  received_at?: string | null;
  created_at: string;
  items: PurchaseItem[];
}

export interface PurchaseOrderListResponse {
  items: PurchaseOrder[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface PurchaseItemCreatePayload {
  product_id: string;
  quantity_ordered: string;
  unit_cost: string;
  expected_expiry_date?: string;
}

export interface PurchaseOrderCreatePayload {
  supplier_id: string;
  items: PurchaseItemCreatePayload[];
}

export interface PurchaseOrderFilterParams {
  status?: string;
  supplier_id?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  limit?: number;
}

export interface PurchaseItemReceiveInput {
  purchase_item_id?: string;
  product_id?: string;
  quantity_received?: string;
  expiry_date?: string;
  lot_code?: string;
}

export interface PurchaseOrderReceivePayload {
  received_date?: string;
  items?: PurchaseItemReceiveInput[];
}

export interface CreatedStockLotSummary {
  id: string;
  lot_code: string;
  product_id: string;
  supplier_id: string;
  purchase_order_id: string;
  quantity_received: string;
  quantity_remaining: string;
  quantity_reserved: string;
  unit_cost: string;
  received_date: string;
  expiry_date: string;
  status: string;
}

export interface CreatedStockMovementSummary {
  id: string;
  lot_id: string;
  movement_type: string;
  quantity_change: string;
  unit_cost_snapshot: string;
  reference_type?: string | null;
  reference_id?: string | null;
  idempotency_key?: string | null;
  reason?: string | null;
  performed_by_user_id?: string | null;
  created_at: string;
}

export interface PurchaseOrderReceiveResponse {
  purchase_order: PurchaseOrder;
  created_lots: CreatedStockLotSummary[];
  created_movements: CreatedStockMovementSummary[];
}

// =============================================================================
// 3. KIỂU DỮ LIỆU LÔ HÀNG FEFO, TỒN KHO & SỔ CÁI (FR-C04..C09)
// =============================================================================
export type LotStatus = 'AVAILABLE' | 'NEAR_EXPIRY' | 'EXPIRED' | 'DEPLETED';

export interface StockLot {
  id: string;
  lot_code: string;
  product_id: string;
  supplier_id?: string | null;
  purchase_order_id?: string | null;
  quantity_received: string;
  quantity_remaining: string;
  quantity_reserved: string;
  available_quantity: string;
  unit_cost: string;
  received_date: string;
  expiry_date: string;
  status: LotStatus | string;
  days_until_expiry: number;
  is_expired: boolean;
  created_at: string;
  updated_at: string;
}

export interface LotListResponse {
  items: StockLot[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface LotFilterParams {
  product_id?: string;
  status?: string;
  page?: number;
  limit?: number;
}

export interface ProductStockSummary {
  product_id: string;
  total_received: string;
  total_remaining: string;
  total_reserved: string;
  available_quantity: string;
  active_lots_count: number;
  near_expiry_lots_count: number;
  expired_lots_count: number;
}

export interface StockSummaryResponse {
  total_products: number;
  total_available_quantity: string;
  total_reserved_quantity: string;
  total_remaining_quantity: string;
  products: ProductStockSummary[];
}

export interface ExpiringLotsResponse {
  days_threshold: number;
  total_near_expiry: number;
  total_expired: number;
  near_expiry_lots: StockLot[];
  expired_lots: StockLot[];
}

export type MovementType =
  | 'IN'
  | 'SALE_OUT'
  | 'RESERVE'
  | 'RELEASE'
  | 'WASTE_EXPIRED'
  | 'WASTE_DAMAGED'
  | 'ADJUSTMENT';

export interface StockMovement {
  id: string;
  lot_id: string;
  movement_type: MovementType | string;
  quantity_change: string;
  unit_cost_snapshot: string;
  reference_type?: string | null;
  reference_id?: string | null;
  idempotency_key?: string | null;
  reason?: string | null;
  performed_by_user_id?: string | null;
  created_at: string;
}

export interface StockMovementListResponse {
  items: StockMovement[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface MovementFilterParams {
  product_id?: string;
  lot_id?: string;
  movement_type?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  limit?: number;
}

export type WastageReasonType = 'WASTE_EXPIRED' | 'WASTE_DAMAGED';

export interface WastageCreatePayload {
  quantity: string;
  reason_type: WastageReasonType;
  note: string;
}

export interface AdjustmentCreatePayload {
  actual_quantity: string;
  reason: string;
}

@Injectable({
  providedIn: 'root'
})
export class InventoryService {
  private readonly apiUrl = `${environment.apiBaseUrl}/inventory`;

  constructor(private http: HttpClient, private authService: AuthService) {}

  // ===========================================================================
  // NHÀ CUNG CẤP (SUPPLIERS)
  // ===========================================================================
  getSuppliers(filters: SupplierFilterParams = {}): Observable<SupplierListResponse> {
    let params = new HttpParams()
      .set('page', String(filters.page ?? 1))
      .set('limit', String(filters.limit ?? 20));

    if (filters.q && filters.q.trim()) {
      params = params.set('q', filters.q.trim());
    }
    if (filters.is_active !== undefined && filters.is_active !== null) {
      params = params.set('is_active', String(filters.is_active));
    }

    return this.http.get<SupplierListResponse>(`${this.apiUrl}/suppliers`, {
      headers: this.authService.getAuthHeaders(),
      params
    });
  }

  getSupplierById(supplierId: string): Observable<Supplier> {
    return this.http.get<Supplier>(`${this.apiUrl}/suppliers/${supplierId}`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  createSupplier(payload: SupplierCreatePayload): Observable<Supplier> {
    return this.http.post<Supplier>(`${this.apiUrl}/suppliers`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }

  updateSupplier(supplierId: string, payload: SupplierUpdatePayload): Observable<Supplier> {
    return this.http.patch<Supplier>(`${this.apiUrl}/suppliers/${supplierId}`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }

  // ===========================================================================
  // PHIẾU NHẬP KHO (PURCHASE ORDERS)
  // ===========================================================================
  getPurchaseOrders(
    filters: PurchaseOrderFilterParams = {}
  ): Observable<PurchaseOrderListResponse> {
    let params = new HttpParams()
      .set('page', String(filters.page ?? 1))
      .set('limit', String(filters.limit ?? 20));

    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.supplier_id) {
      params = params.set('supplier_id', filters.supplier_id);
    }
    if (filters.from_date) {
      params = params.set('from_date', filters.from_date);
    }
    if (filters.to_date) {
      params = params.set('to_date', filters.to_date);
    }

    return this.http.get<PurchaseOrderListResponse>(`${this.apiUrl}/purchase-orders`, {
      headers: this.authService.getAuthHeaders(),
      params
    });
  }

  getPurchaseOrderById(poId: string): Observable<PurchaseOrder> {
    return this.http.get<PurchaseOrder>(`${this.apiUrl}/purchase-orders/${poId}`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  createPurchaseOrder(payload: PurchaseOrderCreatePayload): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.apiUrl}/purchase-orders`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }

  receivePurchaseOrder(
    poId: string,
    payload?: PurchaseOrderReceivePayload
  ): Observable<PurchaseOrderReceiveResponse> {
    return this.http.post<PurchaseOrderReceiveResponse>(
      `${this.apiUrl}/purchase-orders/${poId}/receive`,
      payload ?? {},
      { headers: this.authService.getAuthHeaders() }
    );
  }

  cancelPurchaseOrder(poId: string): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(
      `${this.apiUrl}/purchase-orders/${poId}/cancel`,
      {},
      { headers: this.authService.getAuthHeaders() }
    );
  }

  // ===========================================================================
  // LÔ HÀNG FEFO, TỒN KHO & SỔ CÁI BIẾN ĐỘNG
  // ===========================================================================
  getStockSummary(productId?: string): Observable<StockSummaryResponse> {
    let params = new HttpParams();
    if (productId) {
      params = params.set('product_id', productId);
    }
    return this.http.get<StockSummaryResponse>(`${this.apiUrl}/stock/summary`, {
      headers: this.authService.getAuthHeaders(),
      params
    });
  }

  getExpiringLots(days = 3): Observable<ExpiringLotsResponse> {
    const params = new HttpParams().set('days', String(days));
    return this.http.get<ExpiringLotsResponse>(`${this.apiUrl}/lots/expiring`, {
      headers: this.authService.getAuthHeaders(),
      params
    });
  }

  getLots(filters: LotFilterParams = {}): Observable<LotListResponse> {
    let params = new HttpParams()
      .set('page', String(filters.page ?? 1))
      .set('limit', String(filters.limit ?? 20));

    if (filters.product_id) {
      params = params.set('product_id', filters.product_id);
    }
    if (filters.status) {
      params = params.set('status', filters.status);
    }

    return this.http.get<LotListResponse>(`${this.apiUrl}/lots`, {
      headers: this.authService.getAuthHeaders(),
      params
    });
  }

  getLotById(lotId: string): Observable<StockLot> {
    return this.http.get<StockLot>(`${this.apiUrl}/lots/${lotId}`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  getMovements(filters: MovementFilterParams = {}): Observable<StockMovementListResponse> {
    let params = new HttpParams()
      .set('page', String(filters.page ?? 1))
      .set('limit', String(filters.limit ?? 20));

    if (filters.product_id) {
      params = params.set('product_id', filters.product_id);
    }
    if (filters.lot_id) {
      params = params.set('lot_id', filters.lot_id);
    }
    if (filters.movement_type) {
      params = params.set('movement_type', filters.movement_type);
    }
    if (filters.from_date) {
      params = params.set('from_date', filters.from_date);
    }
    if (filters.to_date) {
      params = params.set('to_date', filters.to_date);
    }

    return this.http.get<StockMovementListResponse>(`${this.apiUrl}/movements`, {
      headers: this.authService.getAuthHeaders(),
      params
    });
  }

  recordWastage(lotId: string, payload: WastageCreatePayload): Observable<StockLot> {
    return this.http.post<StockLot>(`${this.apiUrl}/lots/${lotId}/wastage`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }

  adjustStock(lotId: string, payload: AdjustmentCreatePayload): Observable<StockLot> {
    return this.http.post<StockLot>(`${this.apiUrl}/lots/${lotId}/adjust`, payload, {
      headers: this.authService.getAuthHeaders()
    });
  }
}

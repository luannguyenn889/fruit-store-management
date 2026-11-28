"""
Module: app.services.tool_executor (Chatbot Service)
Nhiệm vụ: Thực thi các Tool (Function Calling) gọi sang `Catalog Service` (:8002)
          và `Inventory Service` (:8003) qua REST API nội bộ theo đúng RBAC,
          đồng thời thu thập danh sách `RecommendedProduct` để render thẻ sản phẩm có ảnh trên UI.
"""

from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.schemas.chat import RecommendedProduct

INTERNAL_INVENTORY_ROLES = {"WAREHOUSE", "MANAGER", "ADMIN"}


class ToolExecutor:
    """Bộ thực thi tool đọc dữ liệu thật từ các Enterprise Service."""

    def __init__(self, user_role: str, user_id: Optional[str], request_id: str) -> None:
        self.user_role = user_role.upper()
        self.user_id = user_id or "00000000-0000-0000-0000-000000000000"
        self.request_id = request_id
        self._collected: Dict[str, RecommendedProduct] = {}

    @property
    def recommended_products(self) -> List[RecommendedProduct]:
        """Trả về tối đa 4 thẻ sản phẩm vừa được tra cứu trong lượt hội thoại."""
        return list(self._collected.values())[:4]

    def _internal_headers(self, role_override: Optional[str] = None) -> Dict[str, str]:
        return {
            "X-Internal-Key": settings.INTERNAL_API_KEY,
            "X-User-Id": self.user_id,
            "X-User-Role": role_override or self.user_role,
            "X-Request-ID": self.request_id,
        }

    def _upsert_product_card(self, raw: Dict[str, Any]) -> None:
        pid = str(raw.get("id") or raw.get("product_id") or "").strip()
        name = str(raw.get("name") or raw.get("product_name") or "").strip()
        if not pid or not name:
            return
        images = raw.get("images") or []
        first_image = images[0].get("image_url") if images and isinstance(images[0], dict) else raw.get("image_url")
        existing = self._collected.get(pid)
        self._collected[pid] = RecommendedProduct(
            id=pid,
            sku=raw.get("sku") or (existing.sku if existing else None),
            name=name,
            unit=raw.get("unit") or (existing.unit if existing else None),
            price=str(raw["price"]) if raw.get("price") is not None else (existing.price if existing else None),
            image_url=first_image or (existing.image_url if existing else None),
            available_quantity=(
                str(raw["available_quantity"])
                if raw.get("available_quantity") is not None
                else (existing.available_quantity if existing else None)
            ),
        )

    async def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Điều phối lời gọi tool từ Gemini sang đúng endpoint REST tương ứng."""
        if name == "search_products":
            return await self._search_products(
                query=str(args.get("query", "")),
                limit=int(args.get("limit", 10)),
            )
        if name == "get_product_detail":
            return await self._get_product_detail(product_id=str(args.get("product_id", "")))
        if name == "check_stock":
            return await self._check_stock(
                product_id=args.get("product_id"),
                keyword=args.get("keyword"),
            )
        if name == "get_expiring_lots":
            if self.user_role not in INTERNAL_INVENTORY_ROLES:
                return {
                    "error": "FORBIDDEN",
                    "message": "Chức năng xem lô cận hạn chỉ dành cho Quản lý / Nhân viên kho.",
                }
            return await self._get_expiring_lots(days=int(args.get("days", 3)))

        return {"error": "UNKNOWN_TOOL", "message": f"Tool '{name}' không được hỗ trợ."}

    async def _search_products(self, query: str, limit: int = 10) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": 1, "size": max(1, min(limit, 20)), "status": "ACTIVE"}
        if query.strip():
            params["q"] = query.strip()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{settings.CATALOG_SERVICE_URL}/api/v1/catalog/products",
                    headers=self._internal_headers("CUSTOMER"),
                    params=params,
                )
            if resp.status_code != 200:
                return {"error": f"CATALOG_HTTP_{resp.status_code}"}
            data = resp.json()
            items = []
            for p in data.get("items", []):
                self._upsert_product_card(p)
                items.append(
                    {
                        "id": p.get("id"),
                        "sku": p.get("sku"),
                        "name": p.get("name"),
                        "unit": p.get("unit"),
                        "price": p.get("price"),
                        "origin": p.get("origin"),
                        "shelf_life_days": p.get("shelf_life_days"),
                        "storage_condition": p.get("storage_condition"),
                    }
                )
            return {"total": data.get("total", len(items)), "products": items}
        except httpx.RequestError as exc:
            return {"error": "CATALOG_UNAVAILABLE", "detail": str(exc)}

    async def _get_product_detail(self, product_id: str) -> Dict[str, Any]:
        if not product_id.strip():
            return {"error": "INVALID_PRODUCT_ID"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{settings.CATALOG_SERVICE_URL}/api/v1/catalog/products/{product_id.strip()}",
                    headers=self._internal_headers("CUSTOMER"),
                )
            if resp.status_code != 200:
                return {"error": f"CATALOG_HTTP_{resp.status_code}"}
            detail = resp.json()
            self._upsert_product_card(detail)
            return detail
        except httpx.RequestError as exc:
            return {"error": "CATALOG_UNAVAILABLE", "detail": str(exc)}

    async def _check_stock(
        self, product_id: Optional[str] = None, keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{settings.INVENTORY_SERVICE_URL}/api/v1/inventory/stock/summary",
                    headers=self._internal_headers("STAFF"),
                )
            if resp.status_code != 200:
                return {"error": f"INVENTORY_HTTP_{resp.status_code}"}
            summary = resp.json()
            products: List[Dict[str, Any]] = summary.get("products", [])
            if product_id:
                products = [p for p in products if str(p.get("product_id")) == str(product_id)]
            elif keyword:
                kw = keyword.strip().lower()
                products = [
                    p
                    for p in products
                    if kw in str(p.get("product_name", "")).lower()
                    or kw in str(p.get("sku", "")).lower()
                ]
            result_items = []
            for p in products[:15]:
                self._upsert_product_card(p)
                result_items.append(
                    {
                        "product_id": p.get("product_id"),
                        "sku": p.get("sku"),
                        "product_name": p.get("product_name"),
                        "available_quantity": p.get("available_quantity"),
                        "status": "CON_HANG"
                        if float(p.get("available_quantity") or 0) > 0
                        else "HET_HANG",
                    }
                )
            return {"items": result_items}
        except httpx.RequestError as exc:
            return {"error": "INVENTORY_UNAVAILABLE", "detail": str(exc)}

    async def _get_expiring_lots(self, days: int = 3) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{settings.INVENTORY_SERVICE_URL}/api/v1/inventory/lots/expiring",
                    headers=self._internal_headers(),
                    params={"days": max(1, min(days, 30))},
                )
            if resp.status_code != 200:
                return {"error": f"INVENTORY_HTTP_{resp.status_code}"}
            return resp.json()
        except httpx.RequestError as exc:
            return {"error": "INVENTORY_UNAVAILABLE", "detail": str(exc)}

"""
Module: app.scripts.seed (Catalog Service)
Nhiệm vụ: Kịch bản khởi tạo dữ liệu mẫu tường minh (Idempotent Seed Script) cho `fruitstore_catalog_db`.
          Tạo các danh mục trái cây thực tế tại Việt Nam ("Trái cây nội địa", "Trái cây nhập khẩu", "Hộp quà trái cây")
          và các sản phẩm mẫu đúng chuẩn `UI_UX_DESIGN_RULES_FruitStore.md` (Xoài cát Hòa Lộc, Táo Fuji, Cam sành, Chuối...).
          Cách chạy: `python -m app.scripts.seed` từ thư mục `backend/services/catalog-service`.
"""

import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.catalog import Category, PriceHistory, Product
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.services.catalog_service import slugify_vietnamese

SAMPLE_CATEGORIES = [
    (
        "Trái cây nội địa",
        "trai-cay-noi-dia",
        "Trái cây tươi đặc sản các vùng miền Việt Nam (Tiền Giang, Bến Tre, Đà Lạt, Sơn La).",
    ),
    (
        "Trái cây nhập khẩu",
        "trai-cay-nhap-khau",
        "Trái cây nhập khẩu chính ngạch bảo quản lạnh tiêu chuẩn quốc tế (Úc, Mỹ, Nhật Bản, New Zealand).",
    ),
    (
        "Hộp quà trái cây",
        "hop-qua-trai-cay",
        "Hộp trái cây tuyển chọn đóng gói sẵn theo hộp tiêu chuẩn.",
    ),
]

SAMPLE_PRODUCTS = [
    {
        "category_slug": "trai-cay-noi-dia",
        "sku": "XOAI-HL-01",
        "name": "Xoài cát Hòa Lộc",
        "unit": "kg",
        "price": Decimal("65000.00"),
        "origin": "Cái Bè, Tiền Giang",
        "default_shelf_life_days": 7,
        "storage_condition": "COOL_8_12C",
        "description": "Xoài cát Hòa Lộc loại 1, thịt vàng ươm, thơm đậm, ít xơ, độ ngọt tự nhiên cao.",
    },
    {
        "category_slug": "trai-cay-nhap-khau",
        "sku": "TAO-FUJI-01",
        "name": "Táo Fuji",
        "unit": "kg",
        "price": Decimal("85000.00"),
        "origin": "Aomori, Nhật Bản",
        "default_shelf_life_days": 21,
        "storage_condition": "COOL_2_8C",
        "description": "Táo Fuji giòn ngọt, mọng nước, bảo quản mát 2-8°C giữ độ giòn lâu.",
    },
    {
        "category_slug": "trai-cay-noi-dia",
        "sku": "CAM-SANH-01",
        "name": "Cam sành Hàm Yên",
        "unit": "kg",
        "price": Decimal("32000.00"),
        "origin": "Hàm Yên, Tuyên Quang",
        "default_shelf_life_days": 10,
        "storage_condition": "AMBIENT",
        "description": "Cam sành vỏ xanh sần, tép vàng mọng nước, giàu vitamin C thích hợp vắt nước.",
    },
    {
        "category_slug": "trai-cay-noi-dia",
        "sku": "CHUOI-LABA-01",
        "name": "Chuối Laba Đà Lạt",
        "unit": "kg",
        "price": Decimal("25000.00"),
        "origin": "Đơn Dương, Lâm Đồng",
        "default_shelf_life_days": 5,
        "storage_condition": "AMBIENT",
        "description": "Chuối Laba dẻo thơm đặc trưng vùng cao nguyên Lâm Đồng.",
    },
    {
        "category_slug": "hop-qua-trai-cay",
        "sku": "HOP-DAU-01",
        "name": "Dâu tây giống Nhật (Hộp 500g)",
        "unit": "hop",
        "price": Decimal("145000.00"),
        "origin": "Đà Lạt, Lâm Đồng",
        "default_shelf_life_days": 4,
        "storage_condition": "COOL_2_8C",
        "description": "Dâu tây Đà Lạt hái sáng sớm, đóng hộp 500g chống dập, bảo quản lạnh 2-8°C.",
    },
    {
        "category_slug": "trai-cay-noi-dia",
        "sku": "BUOI-DX-01",
        "name": "Bưởi da xanh Bến Tre (Loại 1.2 - 1.5kg/quả)",
        "unit": "qua",
        "price": Decimal("58000.00"),
        "origin": "Chợ Lách, Bến Tre",
        "default_shelf_life_days": 15,
        "storage_condition": "AMBIENT",
        "description": "Bưởi da xanh ruột hồng, không hạt, vị ngọt thanh không the đắng, bán theo quả.",
    },
]


async def seed_catalog_data(session: AsyncSession) -> None:
    """Khởi tạo danh mục và sản phẩm mẫu (idempotent - an toàn khi chạy lại)."""
    cat_repo = CategoryRepository(session)
    prod_repo = ProductRepository(session)

    cat_map = {}
    for name, slug, desc in SAMPLE_CATEGORIES:
        existing_cat = await cat_repo.get_by_slug(slug)
        if not existing_cat:
            existing_cat = await cat_repo.create(
                Category(name=name, slug=slug, description=desc, is_active=True)
            )
            print(f"[Catalog Seed] Đã tạo danh mục: {name}")
        cat_map[slug] = existing_cat

    for item in SAMPLE_PRODUCTS:
        existing_prod = await prod_repo.get_by_sku(item["sku"])
        if not existing_prod:
            cat = cat_map[item["category_slug"]]
            prod = Product(
                category_id=cat.id,
                sku=item["sku"],
                name=item["name"],
                slug=slugify_vietnamese(f"{item['name']}-{item['sku']}"),
                unit=item["unit"],
                price=item["price"],
                origin=item["origin"],
                default_shelf_life_days=item["default_shelf_life_days"],
                storage_condition=item["storage_condition"],
                description=item["description"],
                status="ACTIVE",
            )
            await prod_repo.create_product(prod)
            await prod_repo.add_price_history(
                PriceHistory(
                    product_id=prod.id,
                    old_price=item["price"],
                    new_price=item["price"],
                    changed_by_user_id=None,
                    reason="Giá khởi tạo dữ liệu mẫu ban đầu",
                )
            )
            print(f"[Catalog Seed] Đã tạo sản phẩm: {item['sku']} - {item['name']}")

    await session.commit()
    print("[Catalog Seed] Hoàn tất khởi tạo dữ liệu mẫu cho fruitstore_catalog_db.")


async def main() -> None:
    """Điểm chạy chính của lệnh `python -m app.scripts.seed`."""
    async with AsyncSessionLocal() as session:
        await seed_catalog_data(session)


if __name__ == "__main__":
    asyncio.run(main())


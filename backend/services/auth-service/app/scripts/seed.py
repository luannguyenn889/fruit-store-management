"""
Module: app.scripts.seed
Nhiệm vụ: Kịch bản khởi tạo dữ liệu mẫu tường minh (Idempotent Seed Script) cho `fruitstore_auth_db`.
          Tạo đủ 5 vai trò RBAC theo SRS v1.3 (`ADMIN`, `MANAGER`, `STAFF`, `WAREHOUSE`, `CUSTOMER`)
          và các tài khoản mẫu (`admin@fruitstore.com`, `manager@fruitstore.com`, `staff@fruitstore.com`,
          `warehouse@fruitstore.com`).
          Cách chạy: `python -m app.scripts.seed` từ thư mục `backend/services/auth-service`.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.repositories.user_repository import UserRepository

DEFAULT_ROLES = [
    (
        "ADMIN",
        "Quản trị viên",
        "Toàn quyền cấu hình hệ thống và quản trị tài khoản người dùng",
    ),
    (
        "MANAGER",
        "Quản lý cửa hàng",
        "Quản lý danh mục, sản phẩm, giá bán, kho hàng, nhà cung cấp và báo cáo",
    ),
    (
        "STAFF",
        "Nhân viên bán hàng",
        "Bán hàng tại quầy POS, xử lý đơn hàng và thanh toán",
    ),
    (
        "WAREHOUSE",
        "Nhân viên kho",
        "Nhập hàng theo lô, kiểm kê và xử lý trái cây hết hạn/hư hỏng",
    ),
    (
        "CUSTOMER",
        "Khách hàng",
        "Xem sản phẩm, đặt hàng trực tuyến và theo dõi đơn hàng",
    ),
]


async def seed_auth_data(session: AsyncSession) -> None:
    """Khởi tạo 5 vai trò RBAC và các tài khoản mẫu (an toàn khi chạy nhiều lần - idempotent)."""
    repo = UserRepository(session)
    roles_map = {}

    for code, name, desc in DEFAULT_ROLES:
        role = await repo.get_role_by_code(code)
        if not role:
            role = await repo.create_role(code=code, name=name, description=desc)
        roles_map[code] = role

    demo_accounts = [
        (
            "admin@fruitstore.com",
            "0901000001",
            "Quản trị viên Hệ thống",
            settings.SEED_ADMIN_PASSWORD,
            ["ADMIN", "MANAGER"],
        ),
        (
            "manager@fruitstore.com",
            "0901000002",
            "Nguyễn Thùy Mai (Quản lý)",
            settings.SEED_MANAGER_PASSWORD,
            ["MANAGER"],
        ),
        (
            "staff@fruitstore.com",
            "0901000003",
            "Trần Văn Minh (Thu ngân POS)",
            settings.SEED_STAFF_PASSWORD,
            ["STAFF"],
        ),
        (
            "warehouse@fruitstore.com",
            "0901000004",
            "Lê Hoàng Nam (Thủ kho)",
            settings.SEED_WAREHOUSE_PASSWORD,
            ["WAREHOUSE"],
        ),
    ]

    for email, phone, full_name, raw_password, role_codes in demo_accounts:
        existing_user = await repo.get_by_email(email)
        if not existing_user:
            user = User(
                email=email,
                phone=phone,
                password_hash=get_password_hash(raw_password),
                full_name=full_name,
                status="ACTIVE",
                roles=[roles_map[c] for c in role_codes],
            )
            await repo.create_user(user)
            print(f"[Auth Seed] Đã tạo tài khoản mẫu: {email} ({', '.join(role_codes)})")
        else:
            print(f"[Auth Seed] Tài khoản đã tồn tại, bỏ qua: {email}")

    await session.commit()
    print("[Auth Seed] Hoàn tất khởi tạo dữ liệu mẫu cho fruitstore_auth_db.")


async def main() -> None:
    """Hàm thực thi chính khi gọi `python -m app.scripts.seed`."""
    async with AsyncSessionLocal() as session:
        await seed_auth_data(session)


if __name__ == "__main__":
    asyncio.run(main())


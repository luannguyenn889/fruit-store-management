"""
Module: alembic.versions.0001_init_auth
Nhiệm vụ: Bản migration đầu tiên (`0001_init_auth`) của `fruitstore_auth_db`.
          Tạo các bảng `roles`, `users`, `user_roles`, `refresh_tokens` kèm các ràng buộc
          CHECK, UNIQUE, INDEX và dữ liệu 5 vai trò RBAC chuẩn theo SRS v1.3.
          Hỗ trợ `downgrade()` đầy đủ để có thể rollback độc lập (NFR-M02).

Revision ID: 0001_init_auth
Revises: None
Create Date: 2026-11-10
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_init_auth"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Nâng cấp schema: Tạo bảng roles, users, user_roles, refresh_tokens."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    uuid_default = sa.text("gen_random_uuid()") if is_postgres else None

    # 1. Bảng roles (Danh mục vai trò RBAC)
    roles_table = op.create_table(
        "roles",
        sa.Column(
            "id",
            sa.SmallInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    # 2. Bảng users (Tài khoản người dùng)
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'LOCKED', 'INACTIVE')",
            name="ck_users_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_status", "users", ["status"], unique=False)

    # 3. Bảng user_roles (Gán quyền người dùng)
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.SmallInteger(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    # 4. Bảng refresh_tokens (Quản lý phiên làm mới JWT)
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
    )

    # Khởi tạo 5 vai trò RBAC chuẩn theo SRS v1.3
    op.bulk_insert(
        roles_table,
        [
            {
                "code": "ADMIN",
                "name": "Quản trị viên",
                "description": "Toàn quyền cấu hình hệ thống và quản trị tài khoản",
            },
            {
                "code": "MANAGER",
                "name": "Quản lý cửa hàng",
                "description": "Quản lý danh mục, sản phẩm, giá bán, kho, nhà cung cấp và báo cáo",
            },
            {
                "code": "STAFF",
                "name": "Nhân viên bán hàng",
                "description": "Bán hàng tại quầy POS, xử lý đơn hàng và thanh toán",
            },
            {
                "code": "WAREHOUSE",
                "name": "Nhân viên kho",
                "description": "Nhập hàng theo lô, kiểm kê và xử lý trái cây hết hạn/hư hỏng",
            },
            {
                "code": "CUSTOMER",
                "name": "Khách hàng",
                "description": "Xem sản phẩm, đặt hàng trực tuyến và theo dõi đơn hàng",
            },
        ],
    )


def downgrade() -> None:
    """Hạ cấp schema: Xóa theo thứ tự ngược lại để đảm bảo toàn vẹn khóa ngoại (NFR-M02)."""
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_index("idx_users_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")

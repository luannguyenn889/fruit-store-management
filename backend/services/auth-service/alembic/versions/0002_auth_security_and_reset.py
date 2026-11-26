"""
Module: alembic.versions.0002_auth_security_and_reset
Nhiệm vụ: Nâng cấp `fruitstore_auth_db`:
          - Bổ sung `failed_login_attempts`, `locked_until` vào bảng `users` (FR-A07).
          - Tạo bảng `password_reset_tokens` cho Quên mật khẩu qua Email (FR-A10).
          - Tạo bảng `auth_audit_logs` lưu nhật ký kiểm toán bất biến (FR-H01, NFR-S11).

Revision ID: 0002_auth_security_and_reset
Revises: 0001_init_auth
Create Date: 2026-11-26
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_auth_security_and_reset"
down_revision: Union[str, None] = "0001_init_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Thêm cột khóa brute-force vào users và tạo bảng password_reset_tokens, auth_audit_logs."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    uuid_default = sa.text("gen_random_uuid()") if is_postgres else None

    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_hash"),
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )

    op.create_table(
        "auth_audit_logs",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("target_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_audit_logs_actor_user_id",
        "auth_audit_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_auth_audit_logs_target_user_id",
        "auth_audit_logs",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_auth_audit_logs_action",
        "auth_audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_auth_audit_logs_created_at",
        "auth_audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Rollback: xóa bảng auth_audit_logs, password_reset_tokens và 2 cột brute-force."""
    op.drop_table("auth_audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")

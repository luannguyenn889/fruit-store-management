"""Bổ sung guest_token cho chat_sessions và token_usage_json cho chat_messages.

Revision ID: 0002_add_guest_token_and_usage
Revises: 0001_init_chatbot
Create Date: 2026-11-28
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_guest_token_and_usage"
down_revision: Union[str, None] = "0001_init_chatbot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("guest_token", sa.String(length=64), nullable=True))
    op.add_column("chat_messages", sa.Column("token_usage_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "token_usage_json")
    op.drop_column("chat_sessions", "guest_token")

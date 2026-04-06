"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(100), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_id", "users", ["id"])

    # ── user_settings ──────────────────────────────────────────────────────────
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("theme", sa.String(20), nullable=False, default="light"),
        sa.Column("language", sa.String(10), nullable=False, default="en"),
        sa.Column("search_preferences", sa.JSON(), nullable=False, default={}),
        sa.Column("notification_settings", sa.JSON(), nullable=False, default={}),
        sa.Column("other_settings", sa.JSON(), nullable=False, default={}),
    )

    # ── friends ────────────────────────────────────────────────────────────────
    op.create_table(
        "friends",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("friend_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("action_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "friend_id", name="uq_friends_pair"),
    )
    op.create_index("ix_friends_user_id", "friends", ["user_id"])
    op.create_index("ix_friends_friend_id", "friends", ["friend_id"])

    # ── chat_messages ──────────────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("from_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, default=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_to_unread", "chat_messages", ["to_user_id", "is_read", "created_at"])
    op.create_index("ix_chat_messages_from_user_id", "chat_messages", ["from_user_id"])

    # ── game_scores ────────────────────────────────────────────────────────────
    op.create_table(
        "game_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_name", sa.String(50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, default=0),
        sa.Column("extra_data", sa.JSON(), nullable=False, default={}),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_game_scores_user_id", "game_scores", ["user_id"])
    op.create_index("ix_game_scores_game_name", "game_scores", ["game_name"])
    op.create_index("ix_game_scores_game_score", "game_scores", ["game_name", "score"])

    # ── wallets ────────────────────────────────────────────────────────────────
    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("balance", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── recharge_orders ────────────────────────────────────────────────────────
    op.create_table(
        "recharge_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_no", sa.String(64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("order_no", name="uq_recharge_orders_order_no"),
    )
    op.create_index("ix_recharge_orders_user_id", "recharge_orders", ["user_id"])
    op.create_index("ix_recharge_orders_order_no", "recharge_orders", ["order_no"], unique=True)


def downgrade() -> None:
    op.drop_table("recharge_orders")
    op.drop_table("wallets")
    op.drop_table("game_scores")
    op.drop_table("chat_messages")
    op.drop_table("friends")
    op.drop_table("user_settings")
    op.drop_table("users")

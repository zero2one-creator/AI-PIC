"""Create PicKitchen tables (Snowflake BIGINT IDs)

Revision ID: 3f3b0d1a9c61
Revises: 1a31ce608336
Create Date: 2026-01-19

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f3b0d1a9c61"
down_revision = "1a31ce608336"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop template tables (if they exist) to avoid keeping unused schema.
    op.execute('DROP TABLE IF EXISTS item CASCADE')
    op.execute('DROP TABLE IF EXISTS "user" CASCADE')

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("nickname", sa.String(length=64), nullable=True),
        sa.Column("is_vip", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("vip_type", sa.String(length=16), nullable=True),
        sa.Column("vip_expire_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", name="uq_users_device_id"),
    )
    op.create_index("ix_users_device_id", "users", ["device_id"], unique=True)

    op.create_table(
        "user_points",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_points_user_id"),
    )
    op.create_index("ix_user_points_user_id", "user_points", ["user_id"], unique=True)

    op.create_table(
        "point_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=True),
        sa.Column("order_no", sa.String(length=64), nullable=True),
        sa.Column("reward_week", sa.String(length=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "type", "reward_week", name="uq_points_reward_week"),
    )
    op.create_index(
        "ix_point_transactions_user_id", "point_transactions", ["user_id"], unique=False
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("rc_subscriber_id", sa.String(length=128), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("plan_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("will_renew", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_subscriptions_user_product"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("product_type", sa.String(length=16), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payment_channel", sa.String(length=32), nullable=True),
        sa.Column("transaction_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("order_no", name="uq_orders_order_no"),
    )
    op.create_index("ix_orders_order_no", "orders", ["order_no"], unique=True)
    op.create_index("ix_orders_user_id", "orders", ["user_id"], unique=False)

    op.create_table(
        "emoji_tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("driven_id", sa.String(length=64), nullable=False),
        sa.Column("style_name", sa.String(length=64), nullable=True),
        sa.Column("source_image_url", sa.String(length=512), nullable=False),
        sa.Column("detect_result", sa.JSON(), nullable=True),
        sa.Column("aliyun_task_id", sa.String(length=128), nullable=True),
        sa.Column("result_url", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("points_cost", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_emoji_tasks_user_id", "emoji_tasks", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_emoji_tasks_user_id", table_name="emoji_tasks")
    op.drop_table("emoji_tasks")

    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_index("ix_orders_order_no", table_name="orders")
    op.drop_table("orders")

    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_point_transactions_user_id", table_name="point_transactions")
    op.drop_table("point_transactions")

    op.drop_index("ix_user_points_user_id", table_name="user_points")
    op.drop_table("user_points")

    op.drop_index("ix_users_device_id", table_name="users")
    op.drop_table("users")


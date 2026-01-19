"""Add PicKitchen models

Revision ID: pk001_add_pickitchen_models
Revises: 1a31ce608336
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'pk001_add_pickitchen_models'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### 1. 修改 user 表 ###
    # 删除旧的 UUID 主键,添加 BIGINT 主键
    op.execute('ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_pkey CASCADE')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS id CASCADE')
    op.add_column('user', sa.Column('id', sa.BigInteger(), nullable=False, primary_key=True))
    op.create_primary_key('user_pkey', 'user', ['id'])

    # 添加新字段
    op.add_column('user', sa.Column('device_id', sa.String(length=128), nullable=True))
    op.add_column('user', sa.Column('nickname', sa.String(length=64), nullable=True))
    op.add_column('user', sa.Column('is_vip', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('user', sa.Column('vip_type', sa.String(length=20), nullable=True))
    op.add_column('user', sa.Column('vip_expire_time', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))
    op.add_column('user', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))

    # 修改现有字段为可空
    op.alter_column('user', 'email', nullable=True)
    op.alter_column('user', 'hashed_password', nullable=True)

    # 创建索引
    op.create_index('ix_user_device_id', 'user', ['device_id'], unique=True)
    op.create_index('ix_user_email', 'user', ['email'], unique=True)

    # ### 2. 修改 item 表 ###
    op.execute('ALTER TABLE item DROP CONSTRAINT IF EXISTS item_pkey CASCADE')
    op.execute('ALTER TABLE item DROP CONSTRAINT IF EXISTS item_owner_id_fkey CASCADE')
    op.execute('ALTER TABLE item DROP COLUMN IF EXISTS id CASCADE')
    op.execute('ALTER TABLE item DROP COLUMN IF EXISTS owner_id CASCADE')

    op.add_column('item', sa.Column('id', sa.BigInteger(), nullable=False, primary_key=True))
    op.add_column('item', sa.Column('owner_id', sa.BigInteger(), nullable=False))

    op.create_primary_key('item_pkey', 'item', ['id'])
    op.create_foreign_key('item_owner_id_fkey', 'item', 'user', ['owner_id'], ['id'], ondelete='CASCADE')

    # ### 3. 创建 subscription 表 ###
    op.create_table(
        'subscription',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('rc_subscriber_id', sa.String(length=128), nullable=False),
        sa.Column('product_id', sa.String(length=64), nullable=False),
        sa.Column('plan_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('will_renew', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_subscription_user_id', 'subscription', ['user_id'])

    # ### 4. 创建 order 表 ###
    op.create_table(
        'order',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('order_no', sa.String(length=64), nullable=False),
        sa.Column('product_type', sa.String(length=20), nullable=False),
        sa.Column('product_id', sa.String(length=64), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('payment_channel', sa.String(length=32), nullable=False),
        sa.Column('transaction_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_order_order_no', 'order', ['order_no'], unique=True)
    op.create_index('ix_order_user_id', 'order', ['user_id'])

    # ### 5. 创建 userpoints 表 ###
    op.create_table(
        'userpoints',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('balance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_userpoints_user_id', 'userpoints', ['user_id'], unique=True)

    # ### 6. 创建 pointtransaction 表 ###
    op.create_table(
        'pointtransaction',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(length=32), nullable=True),
        sa.Column('order_id', sa.String(length=64), nullable=True),
        sa.Column('reward_week', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_pointtransaction_user_id', 'pointtransaction', ['user_id'])
    # 唯一约束:防止同一周重复发放奖励
    op.create_index(
        'ix_pointtransaction_unique_reward',
        'pointtransaction',
        ['user_id', 'type', 'reward_week'],
        unique=True,
        postgresql_where=sa.text("type = 'reward' AND reward_week IS NOT NULL")
    )

    # ### 7. 创建 emojitask 表 ###
    op.create_table(
        'emojitask',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('task_type', sa.String(length=20), nullable=False),
        sa.Column('source_image_url', sa.String(length=512), nullable=False),
        sa.Column('driven_id', sa.String(length=64), nullable=False),
        sa.Column('face_bbox', sa.String(), nullable=True),
        sa.Column('ext_bbox', sa.String(), nullable=True),
        sa.Column('ali_task_id', sa.String(length=128), nullable=True),
        sa.Column('result_url', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('points_cost', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_emojitask_user_id', 'emojitask', ['user_id'])


def downgrade() -> None:
    # 删除新表
    op.drop_table('emojitask')
    op.drop_table('pointtransaction')
    op.drop_table('userpoints')
    op.drop_table('order')
    op.drop_table('subscription')

    # 恢复 user 表(简化版,实际生产环境需要更复杂的回滚逻辑)
    op.drop_column('user', 'updated_at')
    op.drop_column('user', 'created_at')
    op.drop_column('user', 'vip_expire_time')
    op.drop_column('user', 'vip_type')
    op.drop_column('user', 'is_vip')
    op.drop_column('user', 'nickname')
    op.drop_column('user', 'device_id')

    # 恢复 item 表
    # 注意:这里简化处理,实际需要数据迁移

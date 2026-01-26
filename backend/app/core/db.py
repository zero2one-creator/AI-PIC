"""
数据库连接模块

管理数据库引擎和会话的创建。
使用 SQLModel 的 create_engine 创建数据库连接池。

重要提示：
- 数据库表结构通过 Alembic 迁移管理，不要在这里创建表
- 确保在使用前导入所有模型（app.models），否则关系可能无法正确初始化
"""
from sqlmodel import Session, create_engine  # SQLModel 的数据库工具

from app.core.config import settings

# 创建数据库引擎（连接池）
# create_engine 会创建一个连接池，自动管理数据库连接
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# 重要提示：
# 在使用数据库前，确保所有 SQLModel 模型都已导入（app.models）
# 否则 SQLModel 可能无法正确初始化表之间的关系
# 更多详情：https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    """
    初始化数据库（占位函数）

    注意：数据库表应该通过 Alembic 迁移创建，不要在这里创建表。
    这个函数保留用于未来可能的初始数据填充（seed data）。
    当前版本（V1.0）不需要数据库种子数据。

    Args:
        session: 数据库会话（当前未使用）
    """
    # Tables should be created with Alembic migrations.
    # Keep this hook for future seed data; V1.0 doesn't require DB seeding.
    _ = session  # 占位，避免未使用变量警告

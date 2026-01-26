"""
初始数据脚本

在应用启动时创建初始数据（如种子数据）。
当前版本（V1.0）不需要初始数据，此脚本保留用于未来扩展。

执行时机：
- 在数据库迁移完成后执行（见 scripts/prestart.sh）
- 用于创建默认配置、管理员账户等初始数据
"""
import logging  # 日志记录

from sqlmodel import Session  # 数据库会话

from app.core.db import engine, init_db  # 数据库引擎和初始化函数

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    """
    初始化数据

    创建数据库初始数据。当前版本为空实现，保留用于未来扩展。
    """
    with Session(engine) as session:
        init_db(session)  # 调用初始化函数（当前为空实现）


def main() -> None:
    """
    主函数

    执行初始数据创建。
    """
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":  # pragma: no cover
    # 允许直接运行此脚本
    # pragma: no cover 表示这行代码在测试覆盖率中忽略
    main()

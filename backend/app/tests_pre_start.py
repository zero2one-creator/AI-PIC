"""
测试启动前检查脚本

在运行测试前检查数据库连接是否可用。
与 backend_pre_start.py 功能相同，但用于测试环境。

使用场景：
- 运行测试前确保数据库已就绪
- 在 CI/CD 环境中等待数据库容器启动
"""
import logging  # 日志记录

from sqlalchemy import Engine  # SQLAlchemy 引擎类型
from sqlmodel import Session, select  # SQLModel 会话和查询
from tenacity import (  # 重试库
    after_log,  # 重试后的日志记录
    before_log,  # 重试前的日志记录
    retry,  # 重试装饰器
    stop_after_attempt,  # 停止条件
    wait_fixed,  # 等待策略
)

from app.core.db import engine  # 数据库引擎

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 重试配置
max_tries = 60 * 5  # 最大尝试次数：300 次（5 分钟）
wait_seconds = 1  # 每次重试间隔：1 秒


@retry(
    stop=stop_after_attempt(max_tries),  # 最多尝试 300 次
    wait=wait_fixed(wait_seconds),  # 每次重试前等待 1 秒
    before=before_log(logger, logging.INFO),  # 重试前记录日志
    after=after_log(logger, logging.WARN),  # 重试后记录日志
)
def init(db_engine: Engine) -> None:
    """
    初始化数据库连接检查

    检查数据库是否可用，失败时自动重试。

    Args:
        db_engine: 数据库引擎实例

    Raises:
        Exception: 当数据库连接失败且达到最大重试次数时
    """
    try:
        # 尝试创建会话并执行简单查询，检查数据库是否已就绪
        with Session(db_engine) as session:
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e


def main() -> None:
    """
    主函数

    执行数据库连接检查。
    """
    logger.info("Initializing service")
    init(engine)
    logger.info("Service finished initializing")


if __name__ == "__main__":  # pragma: no cover
    # 允许直接运行此脚本
    # pragma: no cover 表示这行代码在测试覆盖率中忽略
    main()

"""
应用启动前检查脚本

在应用启动前检查数据库连接是否可用。
主要用于 Docker Compose 环境，确保数据库服务已启动后再启动应用。

使用场景：
- Docker Compose 启动时，数据库容器可能还在初始化
- 应用需要等待数据库就绪后才能启动
- 通过重试机制避免启动失败

执行流程：
1. 脚本在应用启动前被调用（见 scripts/prestart.sh）
2. 不断重试连接数据库，直到成功或超时
3. 成功后继续执行数据库迁移和初始化
"""
import logging  # 日志记录

from sqlalchemy import Engine  # SQLAlchemy 引擎类型
from sqlmodel import Session, select  # SQLModel 会话和查询
from tenacity import (  # 重试库，用于实现重试机制
    after_log,  # 重试后的日志记录
    before_log,  # 重试前的日志记录
    retry,  # 重试装饰器
    stop_after_attempt,  # 停止条件：达到最大尝试次数
    wait_fixed,  # 等待策略：固定间隔
)

from app.core.db import engine  # 数据库引擎

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 重试配置
max_tries = 60 * 5  # 最大尝试次数：300 次（5 分钟，每秒一次）
wait_seconds = 1  # 每次重试间隔：1 秒


@retry(
    stop=stop_after_attempt(max_tries),  # 最多尝试 300 次后停止
    wait=wait_fixed(wait_seconds),  # 每次重试前等待 1 秒
    before=before_log(logger, logging.INFO),  # 重试前记录 INFO 级别日志
    after=after_log(logger, logging.WARN),  # 重试后记录 WARN 级别日志
)
def init(db_engine: Engine) -> None:
    """
    初始化数据库连接检查

    尝试创建数据库会话并执行简单查询，验证数据库是否可用。
    如果失败会触发重试机制，最多重试 5 分钟。

    Args:
        db_engine: 数据库引擎实例

    Raises:
        Exception: 当数据库连接失败时，会触发重试机制
                   如果达到最大重试次数仍失败，会抛出异常

    工作原理：
    1. 创建数据库会话
    2. 执行简单查询（select(1)）验证连接
    3. 如果失败，tenacity 会自动重试
    4. 直到成功或达到最大重试次数
    """
    try:
        with Session(db_engine) as session:
            # 尝试执行简单查询，检查数据库是否已就绪
            # select(1) 是最简单的查询，只返回数字 1
            # 如果数据库未就绪，这里会抛出异常，触发重试机制
            session.exec(select(1))
    except Exception as e:
        # 记录错误日志
        logger.error(e)
        # 重新抛出异常，让 tenacity 重试机制处理
        raise e


def main() -> None:
    """
    主函数

    执行数据库连接检查，确保数据库可用后再继续。
    通常在应用启动脚本中被调用（如 scripts/prestart.sh）。
    """
    logger.info("Initializing service")
    # 检查数据库连接，如果失败会自动重试
    init(engine)
    logger.info("Service finished initializing")


if __name__ == "__main__":  # pragma: no cover
    # 允许直接运行此脚本进行测试
    # pragma: no cover 表示这行代码在测试覆盖率中忽略
    main()

"""
基础模型模块

定义所有模型共用的基础类和工具函数。
"""
from datetime import datetime, timezone

from sqlmodel import SQLModel


def utc_now() -> datetime:
    """
    获取当前 UTC 时间

    Returns:
        当前 UTC 时区的日期时间对象
    """
    return datetime.now(timezone.utc)


# 导出 SQLModel 供其他模块使用
__all__ = ["SQLModel", "utc_now"]

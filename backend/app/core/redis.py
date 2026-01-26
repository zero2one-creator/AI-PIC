"""
Redis 缓存连接模块

管理 Redis 客户端连接，使用单例模式确保全局只有一个连接实例。
Redis 用于：
- 缓存数据
- 消息队列（Redis Streams）
- 分布式锁
- 会话存储

使用 @lru_cache 装饰器实现单例模式，避免重复创建连接。
"""
from __future__ import annotations

from functools import lru_cache  # 缓存装饰器，用于实现单例模式

import redis  # Redis 客户端库

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    """
    获取 Redis 客户端实例（单例模式）

    使用 @lru_cache 装饰器确保全局只有一个 Redis 连接实例。
    第一次调用时创建连接，后续调用返回缓存的实例。

    Returns:
        Redis 客户端实例

    配置说明：
    - decode_responses=True: 自动将字节响应解码为字符串
    - 连接参数从 settings 读取
    """
    return redis.Redis(
        host=settings.REDIS_HOST,  # Redis 服务器地址
        port=settings.REDIS_PORT,  # Redis 端口
        db=settings.REDIS_DB,  # Redis 数据库编号（0-15）
        password=settings.REDIS_PASSWORD,  # Redis 密码（可选）
        decode_responses=True,  # 自动解码响应为字符串（而不是字节）
    )


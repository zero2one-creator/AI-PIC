"""
Redis 客户端

提供缓存、队列和分布式锁功能
"""

import json
import logging
from typing import Any

import redis
from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端封装"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        decode_responses: bool = True,
    ):
        """
        初始化 Redis 客户端

        Args:
            host: Redis 主机地址
            port: Redis 端口
            db: 数据库编号
            password: 密码
            decode_responses: 是否自动解码响应
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password

        # 同步客户端
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
        )

        # 异步客户端
        self.async_client = AsyncRedis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
        )

        logger.info(f"Redis client initialized: {host}:{port}/{db}")

    def ping(self) -> bool:
        """
        测试连接

        Returns:
            是否连接成功
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    # ========================================================================
    # 缓存操作
    # ========================================================================

    def get(self, key: str) -> str | None:
        """获取缓存"""
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return None

    def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        px: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        设置缓存

        Args:
            key: 键
            value: 值
            ex: 过期时间(秒)
            px: 过期时间(毫秒)
            nx: 仅当键不存在时设置
            xx: 仅当键存在时设置

        Returns:
            是否成功
        """
        try:
            return self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            return False

    def delete(self, *keys: str) -> int:
        """
        删除缓存

        Args:
            keys: 键列表

        Returns:
            删除的键数量
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """
        检查键是否存在

        Args:
            keys: 键列表

        Returns:
            存在的键数量
        """
        try:
            return self.client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis exists failed: {e}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """
        设置过期时间

        Args:
            key: 键
            seconds: 秒数

        Returns:
            是否成功
        """
        try:
            return self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire failed: {e}")
            return False

    def ttl(self, key: str) -> int:
        """
        获取剩余过期时间

        Args:
            key: 键

        Returns:
            剩余秒数,-1 表示永不过期,-2 表示不存在
        """
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl failed: {e}")
            return -2

    # ========================================================================
    # JSON 缓存操作
    # ========================================================================

    def get_json(self, key: str) -> Any | None:
        """获取 JSON 缓存"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
        return None

    def set_json(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
    ) -> bool:
        """设置 JSON 缓存"""
        try:
            json_str = json.dumps(value)
            return self.set(key, json_str, ex=ex)
        except Exception as e:
            logger.error(f"Failed to set JSON: {e}")
            return False

    # ========================================================================
    # 分布式锁
    # ========================================================================

    def acquire_lock(
        self,
        lock_key: str,
        lock_value: str,
        expire_seconds: int = 60,
    ) -> bool:
        """
        获取分布式锁

        Args:
            lock_key: 锁键
            lock_value: 锁值(用于释放时验证)
            expire_seconds: 锁过期时间(秒)

        Returns:
            是否获取成功
        """
        try:
            return self.set(lock_key, lock_value, ex=expire_seconds, nx=True)
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False

    def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """
        释放分布式锁

        Args:
            lock_key: 锁键
            lock_value: 锁值(必须匹配才能释放)

        Returns:
            是否释放成功
        """
        try:
            # Lua 脚本保证原子性
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = self.client.eval(lua_script, 1, lock_key, lock_value)
            return result == 1
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
            return False

    # ========================================================================
    # Redis Streams (消息队列)
    # ========================================================================

    def xadd(
        self,
        stream_key: str,
        fields: dict[str, str],
        message_id: str = "*",
        maxlen: int | None = None,
    ) -> str | None:
        """
        添加消息到 Stream

        Args:
            stream_key: Stream 键
            fields: 消息字段
            message_id: 消息 ID,默认 "*" 自动生成
            maxlen: 最大长度,超过则删除旧消息

        Returns:
            消息 ID
        """
        try:
            return self.client.xadd(stream_key, fields, id=message_id, maxlen=maxlen)
        except Exception as e:
            logger.error(f"Redis xadd failed: {e}")
            return None

    def xread(
        self,
        streams: dict[str, str],
        count: int | None = None,
        block: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        """
        从 Stream 读取消息

        Args:
            streams: Stream 键和起始 ID 的字典
            count: 最多读取的消息数
            block: 阻塞时间(毫秒),None 表示不阻塞

        Returns:
            消息列表
        """
        try:
            return self.client.xread(streams, count=count, block=block)
        except Exception as e:
            logger.error(f"Redis xread failed: {e}")
            return []

    def xack(self, stream_key: str, group_name: str, *message_ids: str) -> int:
        """
        确认消息已处理

        Args:
            stream_key: Stream 键
            group_name: 消费者组名
            message_ids: 消息 ID 列表

        Returns:
            确认的消息数
        """
        try:
            return self.client.xack(stream_key, group_name, *message_ids)
        except Exception as e:
            logger.error(f"Redis xack failed: {e}")
            return 0

    def xgroup_create(
        self,
        stream_key: str,
        group_name: str,
        message_id: str = "0",
        mkstream: bool = True,
    ) -> bool:
        """
        创建消费者组

        Args:
            stream_key: Stream 键
            group_name: 消费者组名
            message_id: 起始消息 ID
            mkstream: 如果 Stream 不存在是否创建

        Returns:
            是否成功
        """
        try:
            self.client.xgroup_create(stream_key, group_name, id=message_id, mkstream=mkstream)
            return True
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # 消费者组已存在
                return True
            logger.error(f"Redis xgroup_create failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis xgroup_create failed: {e}")
            return False

    def xreadgroup(
        self,
        group_name: str,
        consumer_name: str,
        streams: dict[str, str],
        count: int | None = None,
        block: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        """
        从消费者组读取消息

        Args:
            group_name: 消费者组名
            consumer_name: 消费者名
            streams: Stream 键和起始 ID 的字典
            count: 最多读取的消息数
            block: 阻塞时间(毫秒)

        Returns:
            消息列表
        """
        try:
            return self.client.xreadgroup(
                group_name,
                consumer_name,
                streams,
                count=count,
                block=block,
            )
        except Exception as e:
            logger.error(f"Redis xreadgroup failed: {e}")
            return []

    # ========================================================================
    # 哈希操作
    # ========================================================================

    def hget(self, key: str, field: str) -> str | None:
        """获取哈希字段值"""
        try:
            return self.client.hget(key, field)
        except Exception as e:
            logger.error(f"Redis hget failed: {e}")
            return None

    def hset(self, key: str, field: str, value: str) -> int:
        """设置哈希字段值"""
        try:
            return self.client.hset(key, field, value)
        except Exception as e:
            logger.error(f"Redis hset failed: {e}")
            return 0

    def hgetall(self, key: str) -> dict[str, str]:
        """获取哈希所有字段"""
        try:
            return self.client.hgetall(key)
        except Exception as e:
            logger.error(f"Redis hgetall failed: {e}")
            return {}

    def close(self) -> None:
        """关闭连接"""
        try:
            self.client.close()
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Failed to close Redis client: {e}")


# 全局 Redis 客户端实例
_redis_client: RedisClient | None = None


def init_redis_client(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
) -> RedisClient:
    """
    初始化全局 Redis 客户端

    Args:
        host: Redis 主机地址
        port: Redis 端口
        db: 数据库编号
        password: 密码

    Returns:
        Redis 客户端实例
    """
    global _redis_client
    _redis_client = RedisClient(
        host=host,
        port=port,
        db=db,
        password=password,
    )
    return _redis_client


def get_redis_client() -> RedisClient:
    """
    获取全局 Redis 客户端实例

    Returns:
        Redis 客户端实例

    Raises:
        RuntimeError: 如果客户端未初始化
    """
    if _redis_client is not None:
        return _redis_client

    # 尝试从配置初始化
    from app.core.config import settings

    return init_redis_client(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )

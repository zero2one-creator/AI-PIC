from datetime import datetime, timedelta, timezone
from typing import Any
import threading
import time

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


class SnowflakeIDGenerator:
    """
    Snowflake ID 生成器

    生成 64 位唯一 ID:
    - 1 bit: 符号位(始终为0)
    - 41 bits: 时间戳(毫秒级)
    - 10 bits: 机器ID (5 bits datacenter + 5 bits worker)
    - 12 bits: 序列号

    特点:
    - 时间有序
    - 分布式唯一
    - 高性能(本地生成)
    """

    # 起始时间戳 (2024-01-01 00:00:00 UTC)
    EPOCH = 1704067200000

    # 各部分位数
    WORKER_ID_BITS = 5
    DATACENTER_ID_BITS = 5
    SEQUENCE_BITS = 12

    # 最大值
    MAX_WORKER_ID = (1 << WORKER_ID_BITS) - 1  # 31
    MAX_DATACENTER_ID = (1 << DATACENTER_ID_BITS) - 1  # 31
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1  # 4095

    # 位移
    WORKER_ID_SHIFT = SEQUENCE_BITS
    DATACENTER_ID_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS
    TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS + DATACENTER_ID_BITS

    def __init__(self, datacenter_id: int = 0, worker_id: int = 0):
        """
        初始化 Snowflake ID 生成器

        Args:
            datacenter_id: 数据中心ID (0-31)
            worker_id: 工作机器ID (0-31)
        """
        if datacenter_id > self.MAX_DATACENTER_ID or datacenter_id < 0:
            raise ValueError(f"datacenter_id must be between 0 and {self.MAX_DATACENTER_ID}")
        if worker_id > self.MAX_WORKER_ID or worker_id < 0:
            raise ValueError(f"worker_id must be between 0 and {self.MAX_WORKER_ID}")

        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

    def _current_millis(self) -> int:
        """获取当前时间戳(毫秒)"""
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        """等待下一毫秒"""
        timestamp = self._current_millis()
        while timestamp <= last_timestamp:
            timestamp = self._current_millis()
        return timestamp

    def generate_id(self) -> int:
        """
        生成唯一ID

        Returns:
            64位整数ID
        """
        with self.lock:
            timestamp = self._current_millis()

            # 时钟回拨检测
            if timestamp < self.last_timestamp:
                raise Exception(
                    f"Clock moved backwards. Refusing to generate id for "
                    f"{self.last_timestamp - timestamp} milliseconds"
                )

            # 同一毫秒内
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                # 序列号溢出,等待下一毫秒
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                # 新的毫秒,序列号重置
                self.sequence = 0

            self.last_timestamp = timestamp

            # 组装ID
            snowflake_id = (
                ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT) |
                (self.datacenter_id << self.DATACENTER_ID_SHIFT) |
                (self.worker_id << self.WORKER_ID_SHIFT) |
                self.sequence
            )

            return snowflake_id


# 全局 Snowflake ID 生成器实例
# datacenter_id 和 worker_id 可以从配置中读取
_snowflake_generator = SnowflakeIDGenerator(
    datacenter_id=getattr(settings, 'DATACENTER_ID', 0),
    worker_id=getattr(settings, 'WORKER_ID', 0)
)


def generate_snowflake_id() -> int:
    """
    生成 Snowflake ID

    Returns:
        64位整数ID
    """
    return _snowflake_generator.generate_id()


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

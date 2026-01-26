"""
Snowflake ID 生成器模块

实现 Twitter Snowflake 算法，生成分布式唯一 ID。
适用于分布式系统，确保在不同服务器上生成的 ID 不会重复。

ID 结构（64 位）：
- 41 位：时间戳（毫秒，从自定义起始时间开始）
- 10 位：节点 ID（0-1023，每个服务器实例不同）
- 12 位：序列号（同一毫秒内的序号，0-4095）

优势：
- 全局唯一（通过节点 ID 区分不同服务器）
- 按时间排序（ID 包含时间戳）
- 高性能（本地生成，无需数据库）
"""
from __future__ import annotations

import threading  # 线程锁，用于并发安全
import time  # 时间处理

from app.core.config import settings

# 自定义起始时间（2024-01-01T00:00:00Z）的毫秒时间戳
# 使用较近的起始时间可以让生成的 ID 更小
_EPOCH_MS = 1704067200000


class Snowflake:
    """
    64 位 Snowflake ID 生成器

    ID 结构：
    - 41 位：时间戳（毫秒，从 _EPOCH_MS 开始）
    - 10 位：节点 ID（0-1023，每个服务器实例不同）
    - 12 位：序列号（同一毫秒内的序号，0-4095）

    每个节点每秒最多可生成 4096 个 ID（4095 + 1）。
    """

    def __init__(self, *, node_id: int) -> None:
        """
        初始化 Snowflake 生成器

        Args:
            node_id: 节点 ID（0-1023），每个服务器实例必须不同

        Raises:
            ValueError: 当节点 ID 不在有效范围内时
        """
        if not (0 <= node_id <= 1023):
            raise ValueError("SNOWFLAKE_NODE_ID must be in [0, 1023]")
        self._node_id = node_id  # 节点 ID（10 位）
        self._lock = threading.Lock()  # 线程锁，确保并发安全
        self._last_ts = -1  # 上次生成 ID 的时间戳（毫秒）
        self._seq = 0  # 序列号（12 位，0-4095）

    @staticmethod
    def _now_ms() -> int:
        """
        获取当前时间的毫秒时间戳

        Returns:
            当前时间的毫秒时间戳
        """
        return int(time.time() * 1000)

    def next_id(self) -> int:
        """
        生成下一个唯一 ID

        线程安全，支持并发调用。
        处理时钟回拨情况，防止生成重复 ID。

        Returns:
            64 位唯一 ID

        Raises:
            RuntimeError: 当时钟回拨超过 5 秒时

        算法说明：
        1. 获取当前时间戳
        2. 如果时间戳小于上次时间，说明时钟回拨
        3. 如果回拨超过 5 秒，抛出错误（可能是系统时间配置错误）
        4. 如果回拨小于 5 秒，等待时间恢复
        5. 如果时间戳相同，递增序列号
        6. 如果序列号溢出（达到 4096），等待下一毫秒
        7. 组合时间戳、节点 ID 和序列号生成最终 ID
        """
        with self._lock:  # 加锁，确保线程安全
            ts = self._now_ms()
            if ts < self._last_ts:
                # 时钟回拨检测
                # 在生产环境，这应该触发监控/告警
                diff = self._last_ts - ts
                if diff > 5000:  # 回拨超过 5 秒
                    raise RuntimeError(
                        f"Clock moved backwards by {diff}ms. "
                        "Refusing to generate IDs to prevent duplicates."
                    )
                # 对于小的时钟漂移（< 5 秒），等待时间恢复
                ts = self._wait_until(self._last_ts)

            if ts == self._last_ts:
                # 同一毫秒内，递增序列号
                self._seq = (self._seq + 1) & 0xFFF  # 0xFFF = 4095，确保不超过 12 位
                if self._seq == 0:
                    # 序列号溢出，等待下一毫秒
                    ts = self._wait_until(self._last_ts + 1)
            else:
                # 新的毫秒，重置序列号
                self._seq = 0

            self._last_ts = ts
            # 组合生成最终 ID：
            # (时间戳 - 起始时间) 左移 22 位 | 节点 ID 左移 12 位 | 序列号
            return ((ts - _EPOCH_MS) << 22) | (self._node_id << 12) | self._seq

    @classmethod
    def _wait_until(cls, target_ms: int) -> int:
        """
        等待直到指定时间戳

        用于处理时钟回拨或序列号溢出的情况。

        Args:
            target_ms: 目标时间戳（毫秒）

        Returns:
            当前时间戳（确保 >= target_ms）
        """
        ts = cls._now_ms()
        while ts < target_ms:
            time.sleep(0.001)  # 休眠 1 毫秒
            ts = cls._now_ms()
        return ts


# 全局生成器实例（单例模式）
_GENERATOR: Snowflake | None = None


def _get_generator() -> Snowflake:
    """
    获取全局 Snowflake 生成器实例（单例模式）

    第一次调用时创建实例，后续调用返回同一个实例。
    使用全局变量实现单例模式。

    Returns:
        Snowflake 生成器实例
    """
    global _GENERATOR
    if _GENERATOR is None:
        # 从配置读取节点 ID 并创建生成器
        _GENERATOR = Snowflake(node_id=settings.SNOWFLAKE_NODE_ID)
    return _GENERATOR


def generate_id() -> int:
    """
    生成唯一 ID（便捷函数）

    这是对外提供的接口，内部使用单例的 Snowflake 生成器。

    Returns:
        64 位唯一 ID

    示例：
        >>> user_id = generate_id()
        >>> # 返回类似: 1234567890123456789
    """
    return _get_generator().next_id()


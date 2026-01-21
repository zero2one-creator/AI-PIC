"""
Nacos 配置中心客户端

提供配置拉取、监听和缓存功能
"""

import json
import logging
from typing import Any, Callable

import nacos

logger = logging.getLogger(__name__)


class NacosClient:
    """Nacos 配置中心客户端"""

    def __init__(
        self,
        server_addresses: str,
        namespace: str = "",
        username: str | None = None,
        password: str | None = None,
    ):
        """
        初始化 Nacos 客户端

        Args:
            server_addresses: Nacos 服务器地址,如 "127.0.0.1:8848"
            namespace: 命名空间 ID
            username: 用户名
            password: 密码
        """
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.username = username
        self.password = password

        # 初始化 Nacos 客户端
        self.client = nacos.NacosClient(
            server_addresses=server_addresses,
            namespace=namespace,
            username=username,
            password=password,
        )

        # 配置缓存
        self._config_cache: dict[str, Any] = {}

        logger.info(
            f"Nacos client initialized: server={server_addresses}, namespace={namespace}"
        )

    def get_config(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        timeout: int = 3,
    ) -> str | None:
        """
        获取配置

        Args:
            data_id: 配置 ID
            group: 配置分组
            timeout: 超时时间(秒)

        Returns:
            配置内容字符串,失败返回 None
        """
        try:
            config = self.client.get_config(data_id, group, timeout)
            if config:
                # 缓存配置
                cache_key = f"{group}:{data_id}"
                self._config_cache[cache_key] = config
                logger.info(f"Config loaded: {data_id} (group={group})")
            return config
        except Exception as e:
            logger.error(f"Failed to get config {data_id}: {e}")
            # 返回缓存的配置
            cache_key = f"{group}:{data_id}"
            return self._config_cache.get(cache_key)

    def get_config_json(
        self,
        data_id: str,
        group: str = "DEFAULT_GROUP",
        timeout: int = 3,
    ) -> dict[str, Any] | None:
        """
        获取 JSON 格式配置

        Args:
            data_id: 配置 ID
            group: 配置分组
            timeout: 超时时间(秒)

        Returns:
            配置字典,失败返回 None
        """
        config_str = self.get_config(data_id, group, timeout)
        if config_str:
            try:
                return json.loads(config_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON config {data_id}: {e}")
        return None

    def add_config_watcher(
        self,
        data_id: str,
        group: str,
        callback: Callable[[str], None],
    ) -> None:
        """
        添加配置监听器

        Args:
            data_id: 配置 ID
            group: 配置分组
            callback: 配置变更回调函数,接收新配置内容
        """
        try:
            self.client.add_config_watcher(data_id, group, callback)
            logger.info(f"Config watcher added: {data_id} (group={group})")
        except Exception as e:
            logger.error(f"Failed to add config watcher {data_id}: {e}")

    def remove_config_watcher(
        self,
        data_id: str,
        group: str,
        callback: Callable[[str], None] | None = None,
    ) -> None:
        """
        移除配置监听器

        Args:
            data_id: 配置 ID
            group: 配置分组
            callback: 回调函数,None 则移除所有监听器
        """
        try:
            self.client.remove_config_watcher(data_id, group, callback)
            logger.info(f"Config watcher removed: {data_id} (group={group})")
        except Exception as e:
            logger.error(f"Failed to remove config watcher {data_id}: {e}")

    def publish_config(
        self,
        data_id: str,
        group: str,
        content: str,
        timeout: int = 3,
    ) -> bool:
        """
        发布配置

        Args:
            data_id: 配置 ID
            group: 配置分组
            content: 配置内容
            timeout: 超时时间(秒)

        Returns:
            是否成功
        """
        try:
            result = self.client.publish_config(data_id, group, content, timeout)
            if result:
                logger.info(f"Config published: {data_id} (group={group})")
            return result
        except Exception as e:
            logger.error(f"Failed to publish config {data_id}: {e}")
            return False

    def remove_config(
        self,
        data_id: str,
        group: str,
        timeout: int = 3,
    ) -> bool:
        """
        删除配置

        Args:
            data_id: 配置 ID
            group: 配置分组
            timeout: 超时时间(秒)

        Returns:
            是否成功
        """
        try:
            result = self.client.remove_config(data_id, group, timeout)
            if result:
                logger.info(f"Config removed: {data_id} (group={group})")
                # 清除缓存
                cache_key = f"{group}:{data_id}"
                self._config_cache.pop(cache_key, None)
            return result
        except Exception as e:
            logger.error(f"Failed to remove config {data_id}: {e}")
            return False


# 全局 Nacos 客户端实例
_nacos_client: NacosClient | None = None


def init_nacos_client(
    server_addresses: str,
    namespace: str = "",
    username: str | None = None,
    password: str | None = None,
) -> NacosClient:
    """
    初始化全局 Nacos 客户端

    Args:
        server_addresses: Nacos 服务器地址
        namespace: 命名空间 ID
        username: 用户名
        password: 密码

    Returns:
        Nacos 客户端实例
    """
    global _nacos_client
    _nacos_client = NacosClient(
        server_addresses=server_addresses,
        namespace=namespace,
        username=username,
        password=password,
    )
    return _nacos_client


def get_nacos_client() -> NacosClient:
    """
    获取全局 Nacos 客户端实例

    Returns:
        Nacos 客户端实例

    Raises:
        RuntimeError: 如果客户端未初始化
    """
    if _nacos_client is None:
        raise RuntimeError("Nacos client not initialized. Call init_nacos_client first.")
    return _nacos_client

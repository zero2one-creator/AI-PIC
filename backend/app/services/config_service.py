"""
配置服务模块

提供本地 JSON 配置管理功能，从文件读取配置。
配置会被缓存，避免频繁读取。

配置内容：
- banners: 轮播图列表
- styles: 表情风格列表
- points_rules: 积分规则
- weekly_reward: 周奖励配置
- vip_products: VIP 产品配置
- points_packs: 积分包配置
"""
from __future__ import annotations

import json  # JSON 处理
from pathlib import Path  # 路径处理
from threading import Lock  # 线程锁
from typing import Any  # 任意类型

# 全局变量（使用锁保护）
_lock = Lock()  # 线程锁，确保线程安全
_config: dict[str, Any] | None = None  # 配置缓存


def get_config() -> dict[str, Any]:
    """
    获取配置（带缓存）

    从本地文件读取配置，并缓存结果。

    Returns:
        dict[str, Any]: 配置字典

    配置结构：
        {
            "banners": [...],
            "styles": [...],
            "points_rules": {...},
            "weekly_reward": {...},
            "vip_products": {...},
            "points_packs": {...}
        }
    """
    global _config
    with _lock:
        if _config is not None:
            return _config

        _config = _load_from_file()
        return _config


def refresh_config() -> dict[str, Any]:
    """
    刷新配置缓存

    强制重新加载配置（从本地文件），并更新缓存。

    Returns:
        dict[str, Any]: 新的配置字典

    使用场景：
    - 配置更新后需要立即生效
    - 测试时需要重置配置
    """
    global _config
    with _lock:
        _config = _load_from_file()
        return _config


def _load_from_file() -> dict[str, Any]:
    """
    从本地文件加载配置

    读取 backend/app/config/default_config.json 文件。

    Returns:
        dict[str, Any]: 配置字典，如果文件不存在则返回默认配置
    """
    # 获取配置文件路径：backend/app/config/default_config.json
    path = Path(__file__).resolve().parents[1] / "config" / "default_config.json"
    if not path.exists():
        # 文件不存在，返回默认配置
        return {"banners": [], "styles": [], "points_rules": {}}
    return json.loads(path.read_text(encoding="utf-8"))

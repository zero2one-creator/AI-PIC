"""
配置路由模块

提供应用配置信息的 API 端点。
配置信息包括：轮播图、表情风格、积分规则、VIP 产品、积分包等。
配置可以从 Nacos 动态获取，或从本地文件读取。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import ApiEnvelope, ConfigData
from app.services.config_service import get_config  # 配置服务

router = APIRouter(tags=["config"])


@router.get("/config", response_model=ApiEnvelope)
def config() -> ApiEnvelope:
    """
    获取应用配置

    返回前端需要的所有配置信息，包括：
    - 轮播图列表
    - 表情风格列表
    - 积分规则
    - 周奖励配置
    - VIP 产品配置
    - 积分包配置

    请求路径: GET /api/v1/config

    Returns:
        ApiEnvelope: 包含配置信息的响应

    配置来源：
    - 优先从 Nacos 配置中心获取（如果启用）
    - 否则从本地 default_config.json 文件读取
    """
    cfg = get_config()
    data = ConfigData(
        banners=cfg.get("banners", []),  # 轮播图
        styles=cfg.get("styles", []),  # 表情风格
        points_rules=cfg.get("points_rules", {}),  # 积分规则
        weekly_reward=cfg.get("weekly_reward", {}),  # 周奖励配置
        vip_products=cfg.get("vip_products", {}),  # VIP 产品配置
        points_packs=cfg.get("points_packs", {}),  # 积分包配置
    )
    return ApiEnvelope(data=data)

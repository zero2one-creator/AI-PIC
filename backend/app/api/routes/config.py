from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import ApiEnvelope, ConfigData
from app.services.config_service import get_config

router = APIRouter(tags=["config"])


@router.get("/config", response_model=ApiEnvelope)
def config() -> ApiEnvelope:
    cfg = get_config()
    data = ConfigData(
        banners=cfg.get("banners", []),
        styles=cfg.get("styles", []),
        points_rules=cfg.get("points_rules", {}),
        weekly_reward=cfg.get("weekly_reward", {}),
        vip_products=cfg.get("vip_products", {}),
        points_packs=cfg.get("points_packs", {}),
    )
    return ApiEnvelope(data=data)

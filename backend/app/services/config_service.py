from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings

try:
    import nacos  # type: ignore
except Exception:  # pragma: no cover
    nacos = None

_lock = Lock()
_nacos_client: Any | None = None
_config: dict[str, Any] | None = None


def get_config() -> dict[str, Any]:
    """
    Prefer Nacos when enabled, fallback to local file.
    """
    global _config
    with _lock:
        if _config is not None:
            return _config

        cfg = _load_from_nacos() or _load_from_file()
        _config = cfg
        return cfg


def refresh_config() -> dict[str, Any]:
    global _config
    with _lock:
        _config = _load_from_nacos() or _load_from_file()
        return _config


def _load_from_file() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "config" / "default_config.json"
    if not path.exists():
        return {"banners": [], "styles": [], "points_rules": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _get_nacos_client() -> Any | None:
    global _nacos_client
    if _nacos_client is not None:
        return _nacos_client
    if not settings.NACOS_ENABLED:
        return None
    if nacos is None:
        return None
    if not settings.NACOS_SERVER_ADDR:
        return None

    _nacos_client = nacos.NacosClient(
        server_addresses=settings.NACOS_SERVER_ADDR,
        namespace=settings.NACOS_NAMESPACE or "",
        username=settings.NACOS_USERNAME,
        password=settings.NACOS_PASSWORD,
    )
    return _nacos_client


def _load_json_config(data_id: str, group: str) -> dict[str, Any] | None:
    client = _get_nacos_client()
    if client is None:
        return None
    try:
        content = client.get_config(data_id, group)
    except Exception:
        return None
    if not content:
        return None
    try:
        return json.loads(content)
    except Exception:
        return None


def _load_from_nacos() -> dict[str, Any] | None:
    client = _get_nacos_client()
    if client is None:
        return None

    banners = _load_json_config("pickitchen-banners.json", settings.NACOS_GROUP_BUSINESS) or {}
    styles = _load_json_config("pickitchen-styles.json", settings.NACOS_GROUP_BUSINESS) or {}
    points = _load_json_config("pickitchen-points.json", settings.NACOS_GROUP_BUSINESS) or {}

    # Normalize shape to what /config expects.
    cfg: dict[str, Any] = {"banners": [], "styles": [], "points_rules": {}}
    if isinstance(banners, dict):
        cfg["banners"] = banners.get("banners", banners.get("data", banners)) if banners else []
    if isinstance(styles, dict):
        cfg["styles"] = styles.get("styles", styles.get("data", styles)) if styles else []
    if isinstance(points, dict):
        cfg["points_rules"] = points.get("points_rules", points.get("rules", points.get("points", {}))) or {}
        if "points_packs" in points:
            cfg["points_packs"] = points["points_packs"]
        if "weekly_reward" in points:
            cfg["weekly_reward"] = points["weekly_reward"]
        if "vip_products" in points:
            cfg["vip_products"] = points["vip_products"]

    return cfg

"""
配置管理 API 路由
"""

from fastapi import APIRouter

from app.models import Message

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config() -> dict:
    """
    获取全量配置

    返回:
    - banners: Banner 列表
    - styles: 风格模板配置
    - points_rules: 积分规则
    """
    # TODO: 从 Nacos 读取配置
    # 目前返回模拟数据
    return {
        "banners": [
            {
                "id": 1,
                "image_url": "https://example.com/banner1.jpg",
                "link": "",
                "sort": 1,
            }
        ],
        "styles": [
            {
                "category": "搞怪",
                "templates": [
                    {
                        "driven_id": "emoji_001",
                        "name": "吐舌头",
                        "preview_url": "https://example.com/preview1.jpg",
                    }
                ],
            }
        ],
        "points_rules": {
            "emoji": 10,
            "avatar": 20,
        },
    }

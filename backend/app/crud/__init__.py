"""CRUD 操作模块"""
from .emoji import create_task as create_emoji_task
from .points import change_points, get_user_points
from .user import (
    create as create_user,
)
from .user import (
    get_by_device_id as get_user_by_device_id,
)
from .user import (
    get_or_create_by_device_id as get_or_create_user_by_device_id,
)
from .user import (
    update_vip as update_user_vip,
)

__all__ = [
    "create_emoji_task",
    "change_points",
    "get_user_points",
    "create_user",
    "get_user_by_device_id",
    "get_or_create_user_by_device_id",
    "update_user_vip",
]

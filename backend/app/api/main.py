from fastapi import APIRouter

from app.api.routes import config, emoji, items, login, points, private, subscription, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(points.router)
api_router.include_router(config.router)
api_router.include_router(emoji.router)
api_router.include_router(subscription.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)

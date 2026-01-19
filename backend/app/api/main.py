from fastapi import APIRouter

from app.api.routes import (
    auth,
    config,
    emoji,
    orders,
    points,
    subscription,
    user,
    utils,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(points.router)
api_router.include_router(config.router)
api_router.include_router(emoji.router)
api_router.include_router(subscription.router)
api_router.include_router(orders.router)
api_router.include_router(utils.router)

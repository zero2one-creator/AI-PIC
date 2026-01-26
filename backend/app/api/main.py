"""
API 路由聚合模块

将所有业务路由模块聚合到一个统一的 router 中。
这个 router 会被注册到主应用（app/main.py）上。

路由模块说明：
- auth: 认证相关（登录）
- user: 用户相关（资料、更新）
- points: 积分相关（余额、交易历史）
- config: 配置相关（获取应用配置）
- emoji: 表情相关（检测、创建、历史）
- subscription: 订阅相关（VIP 状态、RevenueCat webhook）
- orders: 订单相关（创建、查询）
- utils: 工具相关（健康检查等）
"""
from fastapi import APIRouter

from app.api.routes import (
    auth,  # 认证路由
    config,  # 配置路由
    emoji,  # 表情路由
    orders,  # 订单路由
    points,  # 积分路由
    subscription,  # 订阅路由
    user,  # 用户路由
    utils,  # 工具路由
)

# 创建主 API 路由器
api_router = APIRouter()

# 注册所有业务路由模块
# 每个模块的路径前缀在各自的 router 中定义
api_router.include_router(auth.router)  # /auth/*
api_router.include_router(user.router)  # /user/*
api_router.include_router(points.router)  # /points/*
api_router.include_router(config.router)  # /config/*
api_router.include_router(emoji.router)  # /emoji/*
api_router.include_router(subscription.router)  # /subscription/*
api_router.include_router(orders.router)  # /orders/*
api_router.include_router(utils.router)  # /utils/*

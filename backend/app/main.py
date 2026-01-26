"""
FastAPI 应用主入口

这是应用的启动文件，负责：
1. 创建 FastAPI 应用实例
2. 配置全局中间件（CORS、Sentry）
3. 注册全局异常处理器
4. 注册 API 路由

运行方式：
    uvicorn app.main:app --reload  # 开发模式
    fastapi dev app/main.py  # 或使用 FastAPI CLI
"""
from typing import Any

import sentry_sdk  # Sentry 错误监控
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError  # 请求验证错误
from fastapi.middleware.cors import CORSMiddleware  # CORS 中间件
from fastapi.responses import JSONResponse  # JSON 响应
from fastapi.routing import APIRoute  # 路由类型

from app.api.errors import AppError
from app.api.main import api_router
from app.core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    """
    自定义 OpenAPI 操作 ID 生成函数

    用于 Swagger UI 中显示更友好的操作 ID。
    格式：{tag}-{route_name}

    Args:
        route: FastAPI 路由对象

    Returns:
        操作 ID 字符串

    示例：
        "auth-login"  # tag="auth", name="login"
    """
    return f"{route.tags[0]}-{route.name}"


# 初始化 Sentry 错误监控（仅在生产/测试环境）
# pragma: no cover 表示这行代码在测试覆盖率中忽略
if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":  # pragma: no cover
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,  # API 文档标题
    openapi_url=f"{settings.API_V1_STR}/openapi.json",  # OpenAPI 规范 URL
    generate_unique_id_function=custom_generate_unique_id,  # 自定义操作 ID
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """
    应用自定义异常处理器

    捕获所有 AppError 异常，返回统一的错误响应格式。

    Args:
        _: 请求对象（未使用）
        exc: AppError 异常实例

    Returns:
        JSONResponse: 统一的错误响应
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP 异常处理器

    捕获 FastAPI 的 HTTPException，转换为统一的响应格式。
    支持两种格式的 detail：
    1. 字典格式：{"code": 123, "message": "错误消息"}
    2. 字符串格式：自动生成错误码

    Args:
        _: 请求对象（未使用）
        exc: HTTPException 异常实例

    Returns:
        JSONResponse: 统一的错误响应
    """
    payload: dict[str, Any]
    if isinstance(exc.detail, dict) and {"code", "message"} <= set(exc.detail.keys()):
        # 如果 detail 是包含 code 和 message 的字典，直接使用
        # 统一为 dict[str, Any]，避免类型检查把其推断成 list/str 等不可下标类型
        payload = {"code": exc.detail.get("code"), "message": exc.detail.get("message")}
    else:
        # 如果 detail 是字符串，自动生成错误码（状态码 * 1000）
        payload = {"code": exc.status_code * 1000, "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": payload["code"], "message": payload["message"], "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """
    请求验证错误处理器

    捕获 Pydantic 的验证错误（如字段类型错误、必填字段缺失等），
    返回详细的验证错误信息。

    Args:
        _: 请求对象（未使用）
        exc: RequestValidationError 异常实例

    Returns:
        JSONResponse: 包含验证错误的响应
    """
    return JSONResponse(
        status_code=422,  # 422 Unprocessable Entity
        content={
            "code": 422000,
            "message": "Validation error",
            "data": {"errors": exc.errors()},  # 详细的验证错误列表
        },
    )

# 配置 CORS（跨域资源共享）中间件
# 允许前端从不同域名访问 API
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,  # 允许的源（域名列表）
        allow_credentials=True,  # 允许携带凭证（如 cookies）
        allow_methods=["*"],  # 允许所有 HTTP 方法
        allow_headers=["*"],  # 允许所有请求头
    )

# 注册 API 路由
# 所有路由都会添加 /api/v1 前缀
app.include_router(api_router, prefix=settings.API_V1_STR)

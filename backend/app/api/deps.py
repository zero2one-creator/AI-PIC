"""
FastAPI 依赖注入模块

提供可复用的依赖项，用于路由处理函数中。
FastAPI 的依赖注入系统会自动处理这些依赖的创建和注入。

关键概念：
- Depends: FastAPI 的依赖注入装饰器
- Generator: 用于创建需要清理的资源（如数据库会话）
- OAuth2PasswordBearer: OAuth2 密码流，用于从请求头提取 token
"""
from collections.abc import Generator  # 生成器类型，用于资源管理
from typing import Annotated  # 类型注解，用于依赖注入

import jwt  # JWT 解析库
from fastapi import Depends, HTTPException, status  # FastAPI 核心功能
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # Bearer 方案
from jwt.exceptions import InvalidTokenError  # JWT 无效异常
from pydantic import ValidationError  # Pydantic 验证异常
from sqlmodel import Session  # 数据库会话

from app.api.schemas import TokenPayload
from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import User

# Bearer 认证配置
# 告诉 FastAPI 从请求头的 Authorization: Bearer <token> 中提取 token
reusable_oauth2 = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）

    这是一个生成器函数，使用 yield 确保会话在使用后自动关闭。
    FastAPI 会在请求处理完成后自动调用生成器的清理逻辑。

    Yields:
        Session: 数据库会话对象

    使用示例：
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            # 使用 db 进行数据库操作
            return db.query(User).all()
    """
    with Session(engine) as session:
        yield session  # yield 确保会话在请求结束后自动关闭


# 类型别名，简化依赖注入的写法
SessionDep = Annotated[Session, Depends(get_db)]  # 数据库会话依赖
TokenDep = Annotated[
    HTTPAuthorizationCredentials, Depends(reusable_oauth2)
]  # JWT token 依赖


def get_current_user(
    session: SessionDep, token: TokenDep
) -> User:
    """
    获取当前登录用户（依赖注入）

    从 JWT token 中解析用户信息，并查询数据库获取完整用户对象。
    如果 token 无效或用户不存在，抛出 401 未授权错误。

    Args:
        session: 数据库会话（自动注入）
        token: JWT token（自动从请求头提取）

    Returns:
        User: 当前登录的用户对象

    Raises:
        HTTPException: 当 token 无效、用户不存在或认证失败时

    使用示例：
        @app.get("/profile")
        def get_profile(user: User = Depends(get_current_user)):
            return user
    """
    try:
        # 解析 JWT token
        token_str = token.credentials
        payload = jwt.decode(
            token_str, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        # 验证 payload 格式
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        # token 格式错误或验证失败
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    if not token_data.sub:
        # token 中没有用户标识
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    try:
        # 将用户标识转换为整数 ID
        user_id = int(token_data.sub)
    except ValueError:
        # 用户标识格式错误
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    # 从数据库查询用户
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# 类型别名，简化需要认证的路由写法
CurrentUser = Annotated[User, Depends(get_current_user)]

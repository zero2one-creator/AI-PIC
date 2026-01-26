"""
安全认证模块

处理 JWT（JSON Web Token）的生成和验证。
JWT 用于用户身份认证，包含用户信息和过期时间。

JWT 结构：
- Header: 算法类型（HS256）
- Payload: 数据（用户 ID、过期时间等）
- Signature: 签名（使用 SECRET_KEY 加密）
"""
from datetime import datetime, timedelta, timezone  # 时间处理
from typing import Any  # 类型注解

import jwt  # JWT 库，用于生成和解析 token

from app.core.config import settings

ALGORITHM = "HS256"  # JWT 签名算法（HMAC SHA256）


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    """
    创建 JWT 访问令牌

    生成一个包含用户标识和过期时间的 JWT token。
    token 使用 HS256 算法签名，确保不被篡改。

    Args:
        subject: 主题（通常是用户 ID 或设备 ID）
        expires_delta: 过期时间间隔（如 timedelta(days=7)）

    Returns:
        编码后的 JWT token 字符串

    示例：
        >>> token = create_access_token("user123", timedelta(days=7))
        >>> # 返回类似: "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    """
    # 计算过期时间：当前时间 + 过期间隔
    expire = datetime.now(timezone.utc) + expires_delta
    # 构建 JWT payload（载荷）
    to_encode = {
        "exp": expire,  # 过期时间（expiration time）
        "sub": str(subject),  # 主题（subject，通常是用户 ID）
    }
    # 使用密钥签名并编码 token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

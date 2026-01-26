"""
自定义异常模块

定义应用特定的异常类，用于统一的错误处理。
所有业务异常都继承自 AppError，在 main.py 中有统一的异常处理器。
"""
from __future__ import annotations


class AppError(Exception):
    """
    应用自定义异常类

    用于业务逻辑中的错误处理，包含：
    - code: 业务错误码（用于前端区分不同错误）
    - message: 错误消息（用户友好的提示）
    - status_code: HTTP 状态码（400, 404, 500 等）

    使用示例：
        raise AppError(code=402001, message="积分不足", status_code=400)
    """

    def __init__(self, *, code: int, message: str, status_code: int = 400) -> None:
        """
        初始化异常

        Args:
            code: 业务错误码（如 402001 表示积分不足）
            message: 错误消息
            status_code: HTTP 状态码（默认 400）
        """
        super().__init__(message)  # 调用父类构造函数
        self.code = code
        self.message = message
        self.status_code = status_code


def insufficient_points() -> AppError:
    """
    创建"积分不足"异常（便捷函数）

    虽然 HTTP 402 Payment Required 在语义上更准确，
    但很多客户端会特殊处理 402，所以使用 400。

    Returns:
        AppError: 积分不足异常实例

    使用示例：
        if balance < cost:
            raise insufficient_points()
    """
    # 402 is semantically accurate, but many clients treat it specially.
    return AppError(code=402001, message="Insufficient points", status_code=400)


from __future__ import annotations


class AppError(Exception):
    def __init__(self, *, code: int, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def insufficient_points() -> AppError:
    # 402 is semantically accurate, but many clients treat it specially.
    return AppError(code=402001, message="Insufficient points", status_code=400)


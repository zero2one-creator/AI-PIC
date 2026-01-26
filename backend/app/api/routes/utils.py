"""
工具路由模块

提供系统工具类的 API 端点，如健康检查等。
"""
from fastapi import APIRouter

router = APIRouter(prefix="/utils", tags=["utils"])


@router.get("/health-check/")
async def health_check() -> bool:
    """
    健康检查端点

    用于监控系统是否正常运行。
    返回 True 表示服务正常。

    请求路径: GET /api/v1/utils/health-check/

    Returns:
        bool: 总是返回 True，表示服务正常

    使用场景：
    - 负载均衡器健康检查
    - 监控系统探活
    - 容器编排系统（如 Kubernetes）的存活探针
    """
    return True

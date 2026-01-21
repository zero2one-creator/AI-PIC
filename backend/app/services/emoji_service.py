"""
阿里云 Emoji AI 服务

基于阿里云模型服务平台的表情包生成 API
文档: https://help.aliyun.com/zh/model-studio/emoji-quick-start/
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmojiService:
    """阿里云 Emoji AI 服务封装"""

    def __init__(self, api_key: str, endpoint: str):
        """
        初始化 Emoji 服务

        Args:
            api_key: 阿里云 API Key
            endpoint: API 端点
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        logger.info("Emoji service initialized")

    async def detect_image(self, image_url: str) -> dict[str, Any]:
        """
        图像检测 API

        检测图片中的人脸和表情,返回人脸框和扩展框坐标

        文档: https://help.aliyun.com/zh/model-studio/emoji-detect-api

        Args:
            image_url: 图片 URL

        Returns:
            {
                "success": bool,
                "face_bbox": [x1, y1, x2, y2],  # 人脸框坐标
                "ext_bbox": [x1, y1, x2, y2],   # 扩展框坐标
                "error": str | None
            }
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.endpoint}/api/v1/emoji/detect",
                    headers=self.headers,
                    json={"image_url": image_url},
                )

                if response.status_code == 200:
                    data = response.json()
                    # 根据实际 API 响应格式调整
                    if data.get("code") == 0 or data.get("success"):
                        result = data.get("data", {})
                        return {
                            "success": True,
                            "face_bbox": result.get("face_bbox"),
                            "ext_bbox": result.get("ext_bbox"),
                            "error": None,
                        }
                    else:
                        return {
                            "success": False,
                            "face_bbox": None,
                            "ext_bbox": None,
                            "error": data.get("message", "Detection failed"),
                        }
                else:
                    logger.error(f"Detect API error: {response.status_code} {response.text}")
                    return {
                        "success": False,
                        "face_bbox": None,
                        "ext_bbox": None,
                        "error": f"API error: {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Failed to detect image: {e}")
            return {
                "success": False,
                "face_bbox": None,
                "ext_bbox": None,
                "error": str(e),
            }

    async def create_video_task(
        self,
        image_url: str,
        driven_id: str,
        face_bbox: list[float] | None = None,
        ext_bbox: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        创建视频生成任务

        文档: https://help.aliyun.com/zh/model-studio/emoji-api

        Args:
            image_url: 图片 URL
            driven_id: 驱动模板 ID
            face_bbox: 人脸框坐标 [x1, y1, x2, y2]
            ext_bbox: 扩展框坐标 [x1, y1, x2, y2]

        Returns:
            {
                "success": bool,
                "task_id": str | None,  # 阿里云任务 ID
                "error": str | None
            }
        """
        try:
            payload = {
                "image_url": image_url,
                "driven_id": driven_id,
            }

            if face_bbox:
                payload["face_bbox"] = face_bbox
            if ext_bbox:
                payload["ext_bbox"] = ext_bbox

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.endpoint}/api/v1/emoji/create",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0 or data.get("success"):
                        result = data.get("data", {})
                        return {
                            "success": True,
                            "task_id": result.get("task_id"),
                            "error": None,
                        }
                    else:
                        return {
                            "success": False,
                            "task_id": None,
                            "error": data.get("message", "Task creation failed"),
                        }
                else:
                    logger.error(f"Create task API error: {response.status_code} {response.text}")
                    return {
                        "success": False,
                        "task_id": None,
                        "error": f"API error: {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Failed to create video task: {e}")
            return {
                "success": False,
                "task_id": None,
                "error": str(e),
            }

    async def query_task_status(self, task_id: str) -> dict[str, Any]:
        """
        查询任务状态

        Args:
            task_id: 阿里云任务 ID

        Returns:
            {
                "success": bool,
                "status": str,  # PENDING/RUNNING/SUCCEEDED/FAILED
                "video_url": str | None,  # 生成的视频 URL (有效期 24h)
                "error": str | None
            }
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.endpoint}/api/v1/emoji/task/{task_id}",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0 or data.get("success"):
                        result = data.get("data", {})
                        return {
                            "success": True,
                            "status": result.get("status", "UNKNOWN"),
                            "video_url": result.get("video_url"),
                            "error": result.get("error_message"),
                        }
                    else:
                        return {
                            "success": False,
                            "status": "FAILED",
                            "video_url": None,
                            "error": data.get("message", "Query failed"),
                        }
                else:
                    logger.error(f"Query task API error: {response.status_code} {response.text}")
                    return {
                        "success": False,
                        "status": "FAILED",
                        "video_url": None,
                        "error": f"API error: {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"Failed to query task status: {e}")
            return {
                "success": False,
                "status": "FAILED",
                "video_url": None,
                "error": str(e),
            }


# 全局 Emoji 服务实例
_emoji_service: EmojiService | None = None


def init_emoji_service(api_key: str, endpoint: str) -> EmojiService:
    """
    初始化全局 Emoji 服务

    Args:
        api_key: 阿里云 API Key
        endpoint: API 端点

    Returns:
        Emoji 服务实例
    """
    global _emoji_service
    _emoji_service = EmojiService(api_key=api_key, endpoint=endpoint)
    return _emoji_service


def get_emoji_service() -> EmojiService:
    """
    获取全局 Emoji 服务实例

    Returns:
        Emoji 服务实例

    Raises:
        RuntimeError: 如果服务未初始化
    """
    if _emoji_service is None:
        # 尝试从配置初始化
        if settings.ALIYUN_AI_API_KEY and settings.ALIYUN_AI_ENDPOINT:
            return init_emoji_service(
                api_key=settings.ALIYUN_AI_API_KEY,
                endpoint=settings.ALIYUN_AI_ENDPOINT,
            )
        raise RuntimeError("Emoji service not initialized and config not available.")
    return _emoji_service

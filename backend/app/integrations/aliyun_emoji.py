"""
阿里云 DashScope 表情生成 API 集成模块

封装阿里云 DashScope 的表情生成相关 API，包括：
- 人脸检测（face-detect）
- 视频合成任务创建（video-synthesis）
- 任务状态查询（task）

DashScope 是阿里云的大模型服务，提供 AI 能力。
表情生成使用 image2video 模型，将静态图片转换为动态表情视频。

支持模拟模式（mock），用于本地开发时不需要真实 API 调用。
"""
from __future__ import annotations

from dataclasses import dataclass  # 数据类
from typing import Any  # 任意类型

import httpx  # HTTP 客户端

from app.api.errors import AppError  # 自定义异常
from app.core.config import settings  # 配置

# API 路径常量
_FACE_DETECT_PATH = "/api/v1/services/aigc/image2video/face-detect"  # 人脸检测接口
_VIDEO_SYNTHESIS_PATH = "/api/v1/services/aigc/image2video/video-synthesis"  # 视频合成接口
_TASK_PATH = "/api/v1/tasks/{task_id}"  # 任务查询接口


@dataclass(frozen=True)
class EmojiDetectResult:
    """
    表情检测结果数据类

    包含人脸检测的结果信息。
    """
    passed: bool  # 是否通过检测
    face_bbox: list[int] | None = None  # 人脸边界框 [x, y, width, height]
    ext_bbox: list[int] | None = None  # 扩展边界框
    error_code: str | None = None  # 错误码（如果失败）
    error_message: str | None = None  # 错误消息（如果失败）
    raw: dict[str, Any] | None = None  # 原始响应数据


@dataclass(frozen=True)
class EmojiCreateResult:
    """
    表情创建任务结果数据类

    包含创建表情生成任务后的信息。
    """
    task_id: str  # 任务 ID
    task_status: str  # 任务状态
    request_id: str | None = None  # 请求 ID
    raw: dict[str, Any] | None = None  # 原始响应数据


@dataclass(frozen=True)
class EmojiTaskResult:
    """
    表情任务查询结果数据类

    包含查询任务状态后的信息。
    """
    task_status: str  # 任务状态（如 SUCCEEDED、FAILED）
    video_url: str | None = None  # 生成的视频 URL（成功时）
    error_code: str | None = None  # 错误码（失败时）
    error_message: str | None = None  # 错误消息（失败时）
    request_id: str | None = None  # 请求 ID
    raw: dict[str, Any] | None = None  # 原始响应数据


class AliyunEmojiClient:
    """
    阿里云 DashScope 表情 API 客户端

    封装 DashScope 表情生成相关的 API 调用。

    API 文档：
    - face-detect: POST /services/aigc/image2video/face-detect (模型 emoji-detect-v1)
    - video-synthesis: POST /services/aigc/image2video/video-synthesis (模型 emoji-v1，异步模式)
    - task: GET /tasks/{task_id} (查询任务状态)
    """

    def __init__(self) -> None:
        """
        初始化客户端

        从配置读取 API 密钥和基础 URL。
        """
        self._mock = settings.ALIYUN_EMOJI_MOCK  # 是否使用模拟模式
        self._base_url = settings.DASHSCOPE_BASE_URL.rstrip("/")  # API 基础 URL
        self._api_key = settings.DASHSCOPE_API_KEY  # API 密钥

    def _headers(self, *, async_enable: bool = False) -> dict[str, str]:
        """
        构建请求头

        Args:
            async_enable: 是否启用异步模式（用于视频合成）

        Returns:
            dict[str, str]: 请求头字典

        Raises:
            AppError: 当 API 密钥未配置时抛出 500101 错误
        """
        if not self._api_key:
            raise AppError(code=500101, message="DASHSCOPE_API_KEY not configured", status_code=500)
        headers = {
            "Authorization": f"Bearer {self._api_key}",  # Bearer token 认证
            "Content-Type": "application/json",
        }
        if async_enable:
            # 启用异步模式（视频合成是异步任务）
            headers["X-DashScope-Async"] = "enable"
        return headers

    def detect(self, *, image_url: str, ratio: str = "1:1") -> EmojiDetectResult:
        """
        人脸检测

        检测图片是否包含人脸，并返回人脸位置信息。

        Args:
            image_url: 图片 URL
            ratio: 图片比例（默认 "1:1"）

        Returns:
            EmojiDetectResult: 检测结果

        Raises:
            AppError: 当 API 调用失败时抛出相应错误码
        """
        if self._mock:
            # 模拟模式：返回模拟数据
            return EmojiDetectResult(
                passed=True,
                face_bbox=[0, 0, 100, 100],
                ext_bbox=[0, 0, 120, 120],
                raw={"mock": True},
            )

        url = f"{self._base_url}{_FACE_DETECT_PATH}"
        payload = {
            "model": "emoji-detect-v1",
            "input": {"image_url": image_url},
            "parameters": {"ratio": ratio},
        }

        try:
            with httpx.Client(timeout=20) as client:
                r = client.post(url, json=payload, headers=self._headers())
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            raise AppError(code=502101, message=f"DashScope detect error: {e}", status_code=502)

        output = data.get("output") if isinstance(data, dict) else None
        if isinstance(output, dict) and "bbox_face" in output and "ext_bbox_face" in output:
            return EmojiDetectResult(
                passed=True,
                face_bbox=output.get("bbox_face"),
                ext_bbox=output.get("ext_bbox_face"),
                raw=data,
            )

        if isinstance(output, dict) and (output.get("code") or output.get("message")):
            return EmojiDetectResult(
                passed=False,
                error_code=str(output.get("code")) if output.get("code") is not None else None,
                error_message=str(output.get("message")) if output.get("message") is not None else None,
                raw=data,
            )

        # Unexpected response
        raise AppError(code=502102, message="DashScope detect invalid response", status_code=502)

    def create_task(
        self,
        *,
        image_url: str,
        driven_id: str,
        face_bbox: list[int],
        ext_bbox: list[int],
    ) -> EmojiCreateResult:
        """
        创建表情生成任务

        提交表情生成任务，返回任务 ID。任务会异步处理。

        Args:
            image_url: 源图片 URL
            driven_id: 驱动图片 ID（用于表情生成）
            face_bbox: 人脸边界框 [x, y, width, height]
            ext_bbox: 扩展边界框 [x, y, width, height]

        Returns:
            EmojiCreateResult: 任务创建结果

        Raises:
            AppError: 当 API 调用失败时抛出相应错误码
        """
        if self._mock:
            # 模拟模式：返回模拟任务 ID
            return EmojiCreateResult(task_id="mock_task", task_status="SUCCEEDED", raw={"mock": True})

        url = f"{self._base_url}{_VIDEO_SYNTHESIS_PATH}"
        payload = {
            "model": "emoji-v1",
            "input": {
                "image_url": image_url,
                "driven_id": driven_id,
                "face_bbox": face_bbox,
                "ext_bbox": ext_bbox,
            },
        }

        try:
            with httpx.Client(timeout=30) as client:
                r = client.post(url, json=payload, headers=self._headers(async_enable=True))
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            raise AppError(code=502201, message=f"DashScope create task error: {e}", status_code=502)

        output = data.get("output") if isinstance(data, dict) else None
        if not isinstance(output, dict) or not output.get("task_id"):
            raise AppError(code=502202, message="DashScope create task invalid response", status_code=502)

        return EmojiCreateResult(
            task_id=str(output.get("task_id")),
            task_status=str(output.get("task_status") or ""),
            request_id=str(data.get("request_id")) if data.get("request_id") is not None else None,
            raw=data,
        )

    def get_task(self, *, task_id: str) -> EmojiTaskResult:
        """
        查询任务状态

        查询表情生成任务的状态和结果。

        Args:
            task_id: 任务 ID

        Returns:
            EmojiTaskResult: 任务查询结果

        Raises:
            AppError: 当 API 调用失败时抛出相应错误码
        """
        if self._mock:
            # 模拟模式：返回模拟结果
            return EmojiTaskResult(
                task_status="SUCCEEDED",
                video_url="https://example.com/mock-result.mp4",
                raw={"mock": True},
            )

        url = f"{self._base_url}{_TASK_PATH.format(task_id=task_id)}"
        try:
            with httpx.Client(timeout=20) as client:
                r = client.get(url, headers=self._headers())
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            raise AppError(code=502301, message=f"DashScope get task error: {e}", status_code=502)

        output = data.get("output") if isinstance(data, dict) else None
        if not isinstance(output, dict):
            raise AppError(code=502302, message="DashScope get task invalid response", status_code=502)

        status = str(output.get("task_status") or "")
        # 文档显示 `output.video_url`；保留对旧格式 `output.results[0].video_url` 的回退支持
        video_url = output.get("video_url")
        if not video_url:
            # 尝试从旧格式中获取视频 URL
            results = output.get("results")
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, dict):
                    video_url = first.get("video_url")

        return EmojiTaskResult(
            task_status=status,
            video_url=video_url,
            error_code=str(output.get("code")) if output.get("code") is not None else None,
            error_message=str(output.get("message")) if output.get("message") is not None else None,
            request_id=str(data.get("request_id")) if data.get("request_id") is not None else None,
            raw=data,
        )


# 创建全局客户端实例（单例模式）
aliyun_emoji_client = AliyunEmojiClient()

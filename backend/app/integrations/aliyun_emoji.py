from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.api.errors import AppError
from app.core.config import settings

_FACE_DETECT_PATH = "/api/v1/services/aigc/image2video/face-detect"
_VIDEO_SYNTHESIS_PATH = "/api/v1/services/aigc/image2video/video-synthesis"
_TASK_PATH = "/api/v1/tasks/{task_id}"


@dataclass(frozen=True)
class EmojiDetectResult:
    passed: bool
    face_bbox: list[int] | None = None
    ext_bbox: list[int] | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class EmojiCreateResult:
    task_id: str
    task_status: str
    request_id: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class EmojiTaskResult:
    task_status: str
    video_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    request_id: str | None = None
    raw: dict[str, Any] | None = None


class AliyunEmojiClient:
    """
    Aliyun DashScope Emoji API wrapper.

    Docs:
    - face-detect: POST /services/aigc/image2video/face-detect (model emoji-detect-v1)
    - video-synthesis: POST /services/aigc/image2video/video-synthesis (model emoji-v1, async header)
    - task: GET /tasks/{task_id}
    """

    def __init__(self) -> None:
        self._mock = settings.ALIYUN_EMOJI_MOCK
        self._base_url = settings.DASHSCOPE_BASE_URL.rstrip("/")
        self._api_key = settings.DASHSCOPE_API_KEY

    def _headers(self, *, async_enable: bool = False) -> dict[str, str]:
        if not self._api_key:
            raise AppError(code=500101, message="DASHSCOPE_API_KEY not configured", status_code=500)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if async_enable:
            headers["X-DashScope-Async"] = "enable"
        return headers

    def detect(self, *, image_url: str, ratio: str = "1:1") -> EmojiDetectResult:
        if self._mock:
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
        if self._mock:
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
        if self._mock:
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
        # Docs show `output.video_url`; keep a fallback for legacy `output.results[0].video_url`.
        video_url = output.get("video_url")
        if not video_url:
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


aliyun_emoji_client = AliyunEmojiClient()

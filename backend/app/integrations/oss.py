"""
阿里云 OSS（对象存储）集成模块

提供阿里云 OSS 的相关功能，包括：
- 上传文件到 OSS
- 构建对象 URL
- 从 URL 下载并上传到 OSS
"""
from __future__ import annotations

import tempfile
from typing import BinaryIO

import httpx
import oss2

from app.api.errors import AppError
from app.core.config import settings


def _build_host(bucket: str, endpoint: str) -> str:
    """构建 OSS 主机地址（虚拟主机风格）"""
    endpoint = endpoint.strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        base = endpoint
    else:
        base = f"https://{endpoint}"
    scheme, rest = base.split("://", 1)
    return f"{scheme}://{bucket}.{rest}"


def _endpoint_for_sdk(endpoint: str) -> str:
    """格式化端点地址供 SDK 使用"""
    endpoint = endpoint.strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"https://{endpoint}"


def _get_bucket() -> oss2.Bucket:
    """获取 OSS Bucket 实例"""
    if not (
        settings.OSS_ENDPOINT
        and settings.OSS_BUCKET
        and settings.OSS_ACCESS_KEY_ID
        and settings.OSS_ACCESS_KEY_SECRET
    ):
        raise AppError(code=500001, message="OSS not configured", status_code=500)
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, _endpoint_for_sdk(settings.OSS_ENDPOINT), settings.OSS_BUCKET)


def build_object_url(*, key: str) -> str:
    """构建 OSS 对象的公开访问 URL"""
    if settings.OSS_PUBLIC_BASE_URL:
        return f"{settings.OSS_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    if not (settings.OSS_ENDPOINT and settings.OSS_BUCKET):
        raise AppError(code=500001, message="OSS not configured", status_code=500)
    host = _build_host(settings.OSS_BUCKET, settings.OSS_ENDPOINT)
    return f"{host}/{key}"


def upload_file(*, file: BinaryIO, key: str, content_type: str | None = None) -> str:
    """
    上传文件到 OSS

    Args:
        file: 文件对象（二进制流）
        key: OSS 对象键名（存储路径）
        content_type: 文件 MIME 类型

    Returns:
        上传后的对象公开访问 URL
    """
    bucket = _get_bucket()
    headers = {}
    if settings.OSS_OBJECT_ACL:
        headers["x-oss-object-acl"] = settings.OSS_OBJECT_ACL
    if content_type:
        headers["Content-Type"] = content_type

    bucket.put_object(key, file, headers=headers or None)
    return build_object_url(key=key)


def upload_from_url(*, url: str, key: str) -> str:
    """从远程 URL 下载文件并上传到 OSS"""
    bucket = _get_bucket()
    headers = {}
    if settings.OSS_OBJECT_ACL:
        headers["x-oss-object-acl"] = settings.OSS_OBJECT_ACL

    with tempfile.NamedTemporaryFile(suffix=".bin") as tmp:
        with httpx.stream("GET", url, timeout=60) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes():
                tmp.write(chunk)
        tmp.flush()
        bucket.put_object_from_file(key, tmp.name, headers=headers or None)

    return build_object_url(key=key)

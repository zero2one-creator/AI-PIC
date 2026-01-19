from __future__ import annotations

import base64
import hashlib
import hmac
import json
import tempfile
import time
from dataclasses import dataclass

import httpx
import oss2

from app.api.errors import AppError
from app.core.config import settings


@dataclass(frozen=True)
class OssPostPolicy:
    host: str
    dir: str
    key: str
    policy: str
    signature: str
    access_key_id: str
    expire_at: int
    image_url: str


def _build_host(bucket: str, endpoint: str) -> str:
    endpoint = endpoint.strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        # If a scheme is already provided, assume endpoint does NOT include bucket.
        base = endpoint
    else:
        base = f"https://{endpoint}"
    scheme, rest = base.split("://", 1)
    # Use virtual-hosted-style: https://bucket.endpoint
    return f"{scheme}://{bucket}.{rest}"


def generate_post_policy(*, key: str, expire_seconds: int, max_size: int = 10 * 1024 * 1024) -> OssPostPolicy:
    if not (
        settings.OSS_ENDPOINT
        and settings.OSS_BUCKET
        and settings.OSS_ACCESS_KEY_ID
        and settings.OSS_ACCESS_KEY_SECRET
    ):
        raise AppError(code=500001, message="OSS not configured", status_code=500)

    host = _build_host(settings.OSS_BUCKET, settings.OSS_ENDPOINT)
    expire_at = int(time.time()) + max(10, int(expire_seconds))

    expiration = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expire_at))
    dir_prefix = key.rsplit("/", 1)[0] + "/" if "/" in key else ""

    policy_dict = {
        "expiration": expiration,
        "conditions": [
            ["content-length-range", 0, max_size],
            ["starts-with", "$key", dir_prefix],
        ],
    }

    policy_json = json.dumps(policy_dict, separators=(",", ":")).encode("utf-8")
    policy_b64 = base64.b64encode(policy_json).decode("utf-8")

    signature = base64.b64encode(
        hmac.new(
            settings.OSS_ACCESS_KEY_SECRET.encode("utf-8"),
            policy_b64.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")

    return OssPostPolicy(
        host=host,
        dir=dir_prefix,
        key=key,
        policy=policy_b64,
        signature=signature,
        access_key_id=settings.OSS_ACCESS_KEY_ID,
        expire_at=expire_at,
        image_url=f"{host}/{key}",
    )


def build_object_url(*, key: str) -> str:
    if settings.OSS_PUBLIC_BASE_URL:
        return f"{settings.OSS_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    if not (settings.OSS_ENDPOINT and settings.OSS_BUCKET):
        raise AppError(code=500001, message="OSS not configured", status_code=500)
    host = _build_host(settings.OSS_BUCKET, settings.OSS_ENDPOINT)
    return f"{host}/{key}"


def _endpoint_for_sdk(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"https://{endpoint}"


def _get_bucket() -> oss2.Bucket:
    if not (
        settings.OSS_ENDPOINT
        and settings.OSS_BUCKET
        and settings.OSS_ACCESS_KEY_ID
        and settings.OSS_ACCESS_KEY_SECRET
    ):
        raise AppError(code=500001, message="OSS not configured", status_code=500)
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, _endpoint_for_sdk(settings.OSS_ENDPOINT), settings.OSS_BUCKET)


def upload_from_url(*, url: str, key: str) -> str:
    """
    Download a remote URL and upload it to OSS.

    Returns the final object URL (public base or virtual-hosted style).
    """
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

"""
阿里云 OSS 客户端

提供图片上传、下载、删除等功能
"""

import logging
from typing import BinaryIO

import oss2

from app.core.config import settings

logger = logging.getLogger(__name__)


class OSSClient:
    """阿里云 OSS 客户端封装"""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        bucket_name: str,
    ):
        """
        初始化 OSS 客户端

        Args:
            access_key_id: AccessKey ID
            access_key_secret: AccessKey Secret
            endpoint: OSS endpoint
            bucket_name: Bucket 名称
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint
        self.bucket_name = bucket_name

        # 创建认证对象
        auth = oss2.Auth(access_key_id, access_key_secret)

        # 创建 Bucket 对象
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)

        logger.info(f"OSS client initialized: bucket={bucket_name}, endpoint={endpoint}")

    def upload_file(
        self,
        object_name: str,
        file_data: bytes | BinaryIO,
        content_type: str | None = None,
    ) -> str:
        """
        上传文件

        Args:
            object_name: OSS 对象名称(路径)
            file_data: 文件数据
            content_type: 内容类型

        Returns:
            文件 URL
        """
        try:
            headers = {}
            if content_type:
                headers["Content-Type"] = content_type

            result = self.bucket.put_object(object_name, file_data, headers=headers)

            if result.status == 200:
                # 返回文件 URL
                scheme = "https"
                endpoint = self.endpoint
                if endpoint.startswith(("http://", "https://")):
                    scheme, endpoint = endpoint.split("://", 1)
                url = f"{scheme}://{self.bucket_name}.{endpoint}/{object_name}"
                logger.info(f"File uploaded: {object_name}")
                return url
            else:
                raise Exception(f"Upload failed with status {result.status}")
        except Exception as e:
            logger.error(f"Failed to upload file {object_name}: {e}")
            raise

    def download_file(self, object_name: str) -> bytes:
        """
        下载文件

        Args:
            object_name: OSS 对象名称

        Returns:
            文件数据
        """
        try:
            result = self.bucket.get_object(object_name)
            return result.read()
        except Exception as e:
            logger.error(f"Failed to download file {object_name}: {e}")
            raise

    def delete_file(self, object_name: str) -> bool:
        """
        删除文件

        Args:
            object_name: OSS 对象名称

        Returns:
            是否成功
        """
        try:
            result = self.bucket.delete_object(object_name)
            logger.info(f"File deleted: {object_name}")
            return result.status == 204
        except Exception as e:
            logger.error(f"Failed to delete file {object_name}: {e}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_name: OSS 对象名称

        Returns:
            是否存在
        """
        try:
            return self.bucket.object_exists(object_name)
        except Exception as e:
            logger.error(f"Failed to check file existence {object_name}: {e}")
            return False

    def generate_presigned_url(
        self,
        object_name: str,
        expires: int = 3600,
    ) -> str:
        """
        生成预签名 URL

        Args:
            object_name: OSS 对象名称
            expires: 过期时间(秒)

        Returns:
            预签名 URL
        """
        try:
            url = self.bucket.sign_url("GET", object_name, expires)
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            raise


# 全局 OSS 客户端实例
_oss_client: OSSClient | None = None


def init_oss_client(
    access_key_id: str,
    access_key_secret: str,
    endpoint: str,
    bucket_name: str,
) -> OSSClient:
    """
    初始化全局 OSS 客户端

    Args:
        access_key_id: AccessKey ID
        access_key_secret: AccessKey Secret
        endpoint: OSS endpoint
        bucket_name: Bucket 名称

    Returns:
        OSS 客户端实例
    """
    global _oss_client
    _oss_client = OSSClient(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint=endpoint,
        bucket_name=bucket_name,
    )
    return _oss_client


def get_oss_client() -> OSSClient:
    """
    获取全局 OSS 客户端实例

    Returns:
        OSS 客户端实例

    Raises:
        RuntimeError: 如果客户端未初始化
    """
    if _oss_client is None:
        # 尝试从配置初始化
        if all(
            [
                settings.OSS_ACCESS_KEY_ID,
                settings.OSS_ACCESS_KEY_SECRET,
                settings.OSS_ENDPOINT,
                settings.OSS_BUCKET_NAME,
            ]
        ):
            return init_oss_client(
                access_key_id=settings.OSS_ACCESS_KEY_ID,
                access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
                endpoint=settings.OSS_ENDPOINT,
                bucket_name=settings.OSS_BUCKET_NAME,
            )
        raise RuntimeError("OSS client not initialized and config not available.")
    return _oss_client

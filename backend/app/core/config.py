"""
应用配置模块

使用 Pydantic Settings 管理所有环境变量和配置。
配置从项目根目录的 .env 文件读取，支持类型验证和默认值。

关键概念：
- BaseSettings: Pydantic 的配置基类，自动从环境变量读取
- computed_field: 计算字段，根据其他字段动态生成
- model_validator: 模型验证器，用于自定义验证逻辑
"""
import secrets  # 用于生成安全的随机字符串
import warnings  # 用于发出警告
from typing import Annotated, Any, Literal  # 类型注解工具

from pydantic import (
    AnyUrl,  # URL 类型验证
    BeforeValidator,  # 字段验证前的转换器
    HttpUrl,  # HTTP URL 类型验证
    PostgresDsn,  # PostgreSQL 连接字符串验证
    computed_field,  # 计算字段装饰器
    model_validator,  # 模型验证器装饰器
)
from pydantic_settings import BaseSettings, SettingsConfigDict  # 配置管理
from typing_extensions import Self  # 用于类型注解中引用自身类型


def parse_cors(v: Any) -> list[str] | str:
    """
    解析 CORS 配置值

    支持两种格式：
    1. 逗号分隔的字符串："http://localhost:3000,http://localhost:3001"
    2. 列表格式：["http://localhost:3000", "http://localhost:3001"]

    Args:
        v: 输入的配置值（字符串或列表）

    Returns:
        解析后的列表或字符串

    Raises:
        ValueError: 当输入格式不正确时
    """
    if isinstance(v, str) and not v.startswith("["):
        # 如果是字符串且不是列表格式，按逗号分割
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """
    应用配置类

    继承自 BaseSettings，自动从环境变量和 .env 文件读取配置。
    所有配置项都有类型验证和默认值。

    配置来源优先级：
    1. 环境变量（最高优先级）
    2. .env 文件
    3. 代码中的默认值（最低优先级）
    """
    model_config = SettingsConfigDict(
        # 使用项目根目录的 .env 文件（backend/ 目录的上一级）
        env_file="../.env",
        env_ignore_empty=True,  # 忽略空的环境变量
        extra="ignore",  # 忽略未定义的额外字段
    )
    API_V1_STR: str = "/api/v1"  # API 版本前缀
    SECRET_KEY: str = secrets.token_urlsafe(32)  # JWT 签名密钥（默认随机生成）
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7  # JWT token 过期天数
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    # Literal: 限制只能取这几个值之一

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []
    # Annotated: 类型注解，BeforeValidator 在验证前先调用 parse_cors 函数转换格式

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """
        计算字段：获取所有 CORS 允许的源（去除尾部斜杠）

        这是一个计算属性，根据 BACKEND_CORS_ORIGINS 动态生成。
        去除 URL 尾部的斜杠，确保格式统一。

        Returns:
            CORS 允许的源列表（字符串格式）
        """
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None

    # Snowflake
    SNOWFLAKE_NODE_ID: int = 0

    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # SMTP 邮件服务器配置（用于发送邮件）
    SMTP_TLS: bool = True  # 是否使用 TLS
    SMTP_SSL: bool = False  # 是否使用 SSL
    SMTP_PORT: int = 587  # SMTP 端口
    SMTP_HOST: str | None = None  # SMTP 服务器地址
    SMTP_USER: str | None = None  # SMTP 用户名
    SMTP_PASSWORD: str | None = None  # SMTP 密码
    EMAILS_FROM_EMAIL: str | None = None  # 发件人邮箱
    EMAILS_FROM_NAME: str | None = None  # 发件人名称

    # Redis 缓存配置
    REDIS_HOST: str = "localhost"  # Redis 服务器地址
    REDIS_PORT: int = 6379  # Redis 端口
    REDIS_DB: int = 0  # Redis 数据库编号（0-15）
    REDIS_PASSWORD: str | None = None  # Redis 密码（可选）

    # 阿里云 OSS（对象存储）配置
    OSS_ENDPOINT: str | None = None  # OSS 端点地址
    OSS_BUCKET: str | None = None  # OSS 存储桶名称
    OSS_ACCESS_KEY_ID: str | None = None  # OSS Access Key ID
    OSS_ACCESS_KEY_SECRET: str | None = None  # OSS Access Key Secret
    OSS_DIR_PREFIX: str = "uploads"  # 上传文件目录前缀
    OSS_RESULT_PREFIX: str = "results"  # 结果文件目录前缀
    OSS_UPLOAD_EXPIRE_SECONDS: int = 60  # 上传 URL 过期时间（秒）
    OSS_OBJECT_ACL: str = "public-read"  # 对象访问权限（公开读）
    OSS_PUBLIC_BASE_URL: str | None = None  # OSS 公开访问的基础 URL

    # 阿里云 DashScope（表情生成 API）配置
    ALIYUN_EMOJI_MOCK: bool = True  # 是否使用模拟模式（本地开发时）
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com"  # API 基础 URL
    DASHSCOPE_API_KEY: str | None = None  # DashScope API 密钥

    # 表情生成任务轮询配置
    EMOJI_POLL_INTERVAL_SECONDS: int = 15  # 轮询间隔（秒）
    EMOJI_POLL_TIMEOUT_SECONDS: int = 10 * 60  # 轮询超时时间（10 分钟）

    # RevenueCat 配置（iOS/Android 订阅管理）
    REVENUECAT_WEBHOOK_SECRET: str | None = None  # Webhook 验证密钥

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """
        检查敏感配置是否使用了默认值

        如果配置项使用了默认值 "changethis"，在本地环境会发出警告，
        在生产环境会抛出错误，强制修改。

        Args:
            var_name: 配置项名称
            value: 配置项的值

        Raises:
            ValueError: 在生产环境使用默认值时
        """
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                # 本地环境只警告，不阻止运行
                warnings.warn(message, stacklevel=1)
            else:
                # 生产环境直接报错，强制修改
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        """
        模型验证器：确保敏感配置不使用默认值

        在配置加载完成后自动调用，检查关键安全配置。
        这是 Pydantic 的验证机制，确保配置安全。

        Returns:
            self: 返回配置实例本身
        """
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)

        return self


# 创建全局配置实例，整个应用共享
settings = Settings()  # type: ignore

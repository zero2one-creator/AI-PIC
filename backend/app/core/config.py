import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
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

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # OSS (Aliyun)
    OSS_ENDPOINT: str | None = None
    OSS_BUCKET: str | None = None
    OSS_ACCESS_KEY_ID: str | None = None
    OSS_ACCESS_KEY_SECRET: str | None = None
    OSS_DIR_PREFIX: str = "uploads"
    OSS_RESULT_PREFIX: str = "results"
    OSS_UPLOAD_EXPIRE_SECONDS: int = 60
    OSS_OBJECT_ACL: str = "public-read"
    OSS_PUBLIC_BASE_URL: str | None = None

    # Aliyun DashScope (Emoji) (mockable)
    ALIYUN_EMOJI_MOCK: bool = True
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com"
    DASHSCOPE_API_KEY: str | None = None

    EMOJI_POLL_INTERVAL_SECONDS: int = 15
    EMOJI_POLL_TIMEOUT_SECONDS: int = 10 * 60

    # RevenueCat
    REVENUECAT_WEBHOOK_SECRET: str | None = None

    # Nacos (optional)
    NACOS_ENABLED: bool = False
    NACOS_SERVER_ADDR: str | None = None
    NACOS_NAMESPACE: str | None = None
    NACOS_USERNAME: str | None = None
    NACOS_PASSWORD: str | None = None
    NACOS_GROUP_DEFAULT: str = "DEFAULT_GROUP"
    NACOS_GROUP_BUSINESS: str = "BUSINESS"

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)

        return self


settings = Settings()  # type: ignore

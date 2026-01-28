# Docker 方案概览

本文介绍当前项目使用的 Docker 方案，包括 Compose 文件划分、服务角色、网络与路由、数据持久化，以及本地与生产的运行方式。

## 文件划分

- `docker-compose.yml`：核心服务栈，适用于生产/测试环境。
- `docker-compose.override.yml`：本地开发的覆盖配置（端口暴露、热更新、MailCatcher、本地 Traefik 代理）。
- `docker-compose.traefik.yml`：公共 Traefik 实例，用于 HTTPS 证书与子域名路由。
- `backend/Dockerfile`：后端镜像构建定义（Python 3.10 + uv）。

## 服务组成（docker-compose.yml）

- `adminer`：数据库管理工具，通过 Traefik 暴露为 `adminer.${DOMAIN}`。
- `prestart`：启动前置任务，执行数据库连通检查、迁移和初始化数据（`backend/scripts/prestart.sh`）。
- `backend`：FastAPI 服务，暴露为 `api.${DOMAIN}`，依赖 `prestart` 成功后启动。
- `worker`：后台任务进程，复用后端镜像，执行 `python worker/emoji_worker.py`。

## 网络与路由

- 使用 `traefik-public` 网络连接对外服务。
- 生产环境下 `traefik-public` 为外部共享网络（由公共 Traefik 创建）。
- 本地开发通过 `docker-compose.override.yml` 增加 `proxy`（Traefik）并将 `traefik-public` 设为内部网络。
- 通过 Traefik label 按子域名路由：`api.${DOMAIN}`、`adminer.${DOMAIN}`、`traefik.${DOMAIN}`。

## 启动流程与依赖顺序

1. `prestart` 负责等待外部 PostgreSQL 就绪并执行迁移/初始化。
2. `backend`、`worker` 在 `prestart` 成功后启动。

## 本地开发模式

- 使用 `docker-compose.override.yml` 自动开启端口映射与热更新。
- 启动方式：`docker compose watch`（或 `docker compose up -d`）。
- 本地额外服务：`proxy`（Traefik 本地代理）、`mailcatcher`（本地邮件捕获）。
- 详细步骤与访问地址见：`docs/development/docker.zh-CN.md`。

## 生产部署模式

- 先部署公共 Traefik（`docker-compose.traefik.yml`），再启动项目栈。
- 启动命令通常为：`docker compose -f docker-compose.yml up -d`。
- 生产部署注意事项见：`docs/deployment/docker.zh-CN.md`。

## 关键环境变量

- 运行环境：`ENVIRONMENT`、`DOMAIN`、`STACK_NAME`。
- 数据库：`POSTGRES_SERVER`、`POSTGRES_PORT`、`POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`。
- Redis：`REDIS_HOST`、`REDIS_PORT`、`REDIS_DB`。
- 安全相关：`SECRET_KEY`、`FIRST_SUPERUSER`、`FIRST_SUPERUSER_PASSWORD`。
- 邮件：`SMTP_HOST`、`SMTP_USER`、`SMTP_PASSWORD`、`EMAILS_FROM_EMAIL`。
- 其他：`SENTRY_DSN`、`SNOWFLAKE_NODE_ID`、`DOCKER_IMAGE_BACKEND`、`TAG`。

## 外部 PostgreSQL/Redis（必需）

PostgreSQL 与 Redis 由外部服务提供，本仓库不再启动相关容器。
请在 `.env` 中将 `POSTGRES_SERVER` 与 `REDIS_HOST` 指向可用的外部服务。

## 数据与持久化

- 数据持久化由外部 PostgreSQL/Redis 负责。
- 本地开发会额外挂载 `./backend/htmlcov` 以保存覆盖率输出（见 override）。

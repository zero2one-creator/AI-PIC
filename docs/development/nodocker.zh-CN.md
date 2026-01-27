# FastAPI 项目 - 开发（非 Docker）

面向新同学的本地开发指南，本版本在 macOS 上直接运行 Python。
Docker 方式请见 [Docker 开发](docker.zh-CN.md)。

## 环境文件

后端会从仓库根目录 `.env` 读取环境变量（相对于 `backend/` 目录）。
本地开发请保持 `ENVIRONMENT=local`，并按需调整 `POSTGRES_*`、`DOMAIN`、
`STACK_NAME` 等配置。不要提交真实密钥。仓库里提供了本地用的 `.env` 基线，
非 Docker 运行时请确保 `POSTGRES_*` 和 `REDIS_*` 指向本机服务。

## 前置条件（macOS）

- Python 3.10+ 与 [uv](https://docs.astral.sh/uv/)
- PostgreSQL（必需）
- Redis（可选；Emoji 队列 Worker 需要）

## 安装依赖

```bash
cd backend
uv sync
source .venv/bin/activate
```

## 配置并启动本地服务

在 `.env` 中配置本地服务，例如：

```dotenv
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
```

确保数据库已创建且可访问，然后执行迁移与初始化数据：

```bash
cd backend
bash scripts/prestart.sh
```

## 启动 API

```bash
cd backend
fastapi dev app/main.py
```

## 可选：后台 Worker

需要时在不同终端启动：

```bash
cd backend
python worker/emoji_worker.py
python worker/weekly_points_reward.py
```

如果未启动 Redis，Emoji 队列接口会返回 “Queue unavailable”，但 API 仍可启动。

## 测试

```bash
cd backend
bash scripts/test.sh
```

## Pre-commit 与代码检查

本项目使用 [prek](https://prek.j178.dev/)（一个现代化的 pre-commit 替代方案）。

安装 git hook（在 `backend/` 目录下执行）：

```bash
uv run prek install -f
```

手动运行所有检查：

```bash
uv run prek run --all-files
```

## 部署脚本与 GitHub Actions

本地脚本位于 `./scripts/`：

- `scripts/build.sh`：构建镜像（需要 `TAG`）
- `scripts/build-push.sh`：构建并推送镜像（需要 `TAG`）
- `scripts/deploy.sh`：渲染 Swarm 栈并部署（需要 `DOMAIN`、`STACK_NAME`、`TAG`）

本仓库实际部署通过 GitHub Actions 在阿里云 ECS 的自建 Runner 上执行：

- 预发：push 到 `master`（`.github/workflows/deploy-staging.yml`）
- 生产：发布 release（`.github/workflows/deploy-production.yml`）
- 均使用 `docker compose -f docker-compose.yml build` + `up -d`
- 需要的 secrets：`DOMAIN_*`、`STACK_NAME_*`、`SECRET_KEY`、
  `FIRST_SUPERUSER`、`FIRST_SUPERUSER_PASSWORD`、`POSTGRES_PASSWORD`、
  SMTP 配置与 `SENTRY_DSN`（可选）

更多工作流说明见 `docs/github-actions-concepts.zh-CN.md`。

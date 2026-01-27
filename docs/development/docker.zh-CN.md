# FastAPI 项目 - 开发（Docker）

面向新同学的本地开发指南，本版本使用 Docker Compose。

## 环境文件

后端会从仓库根目录 `.env` 读取环境变量（相对于 `backend/` 目录）。
本地开发请保持 `ENVIRONMENT=local`，并按需调整 `POSTGRES_*`、`DOMAIN`、
`STACK_NAME` 等配置。不要提交真实密钥。

## 启动本地环境

```bash
docker compose watch
```

如果 `watch` 不可用，使用：

```bash
docker compose up -d
```

## 本地访问地址

- 后端 API：http://localhost:8000
- API 文档（Swagger UI）：http://localhost:8000/docs
- Adminer（数据库管理）：http://localhost:8080
- Traefik UI（本地开发代理）：http://localhost:8090
- MailCatcher：http://localhost:1080

## 日志与状态

```bash
docker compose ps
docker compose logs
docker compose logs backend
```

## 依赖服务端口

`docker-compose.override.yml` 将 PostgreSQL 映射到 `localhost:5433`，
Redis 映射到 `localhost:6379`。从宿主机连接时请使用这些端口。

## 重置本地数据（危险操作）

```bash
docker compose down -v
```

## Mailcatcher

Mailcatcher 是一个本地 SMTP 服务器：它会捕获应用发出的邮件，并在 Web UI 中展示。
在本地使用 Docker Compose 运行时，后端会被配置为把邮件发送到 Mailcatcher
（SMTP 端口 1025）。

- MailCatcher UI：http://localhost:1080

## 可选：本地域名（`localhost.tiangolo.com`）

如果你想在本地测试基于子域名的路由，可以编辑 `.env`：

```dotenv
DOMAIN=localhost.tiangolo.com
```

然后重启：

```bash
docker compose watch
```

使用该配置后：

- 后端 API：http://api.localhost.tiangolo.com
- API 文档：http://api.localhost.tiangolo.com/docs
- Adminer：http://adminer.localhost.tiangolo.com
- Traefik UI：http://localhost.tiangolo.com:8090
- MailCatcher：http://localhost.tiangolo.com:1080

## 测试

```bash
docker compose exec backend bash scripts/tests-start.sh
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

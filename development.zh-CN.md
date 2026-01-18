# FastAPI 项目 - 开发

## Docker Compose

使用 Docker Compose 启动本地环境：

```bash
docker compose watch
```

本地访问地址：

- 后端 API：http://localhost:8000
- API 文档（Swagger UI）：http://localhost:8000/docs
- Adminer（数据库管理）：http://localhost:8080
- Traefik UI（本地开发代理）：http://localhost:8090
- MailCatcher：http://localhost:1080

如果服务仍在启动中，可以查看日志：

```bash
docker compose logs
docker compose logs backend
```

## Mailcatcher

Mailcatcher 是一个本地 SMTP 服务器：它会捕获应用发出的邮件，并在 Web UI 中展示。

在本地使用 Docker Compose 运行时，后端会被配置为把邮件发送到 Mailcatcher（SMTP 端口 1025）。

- MailCatcher UI：http://localhost:1080

## 本地开发（不使用 Docker）

Docker Compose 文件会将后端暴露在与本地开发一致的端口（`8000`）。因此你可以停止容器，直接在本机运行开发服务器：

```bash
docker compose stop backend

cd backend
fastapi dev app/main.py
```

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


# FastAPI 项目 - 部署

你可以使用 Docker Compose 将该项目部署到远程服务器。该栈为纯后端（API + 数据库 + 管理工具）。

此模板可以与一个共享的 Traefik 实例集成：由它负责 HTTPS 证书，并通过子域名进行路由转发。

## 准备工作

- 一台已安装 Docker Engine 的远程服务器（不是 Docker Desktop）。
- DNS 解析指向你的服务器 IP（常见配置如下）：
  - `api.<your-domain>` -> 后端 API
  - `adminer.<your-domain>` -> Adminer（可选）
  - `traefik.<your-domain>` -> Traefik 仪表盘（可选）

## 公共 Traefik（可选，但推荐用于 HTTPS）

每台服务器只需要做一次。

1) 将 `docker-compose.traefik.yml` 复制到服务器（示例路径）：

```bash
mkdir -p /root/code/traefik-public/
rsync -a docker-compose.traefik.yml root@your-server:/root/code/traefik-public/
```

2) 创建共享 Docker 网络：

```bash
docker network create traefik-public
```

3) 设置必须的环境变量并启动 Traefik：

```bash
export USERNAME=admin
export PASSWORD=changethis
export HASHED_PASSWORD=$(openssl passwd -apr1 "$PASSWORD")
export DOMAIN=example.com
export EMAIL=admin@example.com

cd /root/code/traefik-public/
docker compose -f docker-compose.traefik.yml up -d
```

## 部署后端栈

在服务器上（或通过 CI/CD）至少需要设置：

- `ENVIRONMENT=staging|production`
- `DOMAIN=<your-domain>`
- 密钥/密码：`SECRET_KEY`、`POSTGRES_PASSWORD`、`FIRST_SUPERUSER_PASSWORD`

然后部署：

```bash
docker compose -f docker-compose.yml up -d
```

在生产环境中通常不使用 `docker-compose.override.yml`，因此这里显式指定 `-f docker-compose.yml`。

## 环境变量

核心变量位于 `.env`。常见变量包括：

- `PROJECT_NAME`、`STACK_NAME`
- `BACKEND_CORS_ORIGINS`
- `SECRET_KEY`
- `FIRST_SUPERUSER`、`FIRST_SUPERUSER_PASSWORD`
- `SMTP_*`、`EMAILS_FROM_EMAIL`（如果需要发送真实邮件）
- `POSTGRES_*`
- `SENTRY_DSN`（可选）


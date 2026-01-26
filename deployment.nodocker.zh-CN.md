# FastAPI 项目 - 非 Docker 部署

本文档介绍在 Linux 服务器上使用 systemd + Nginx + PostgreSQL 的非 Docker 部署方案。请根据你的实际环境调整路径与版本。

## 1) 前置条件

- Linux 服务器，Python 3.10+。
- PostgreSQL（必须）。
- Redis（可选，用于 emoji 队列）。
- Nginx 或 Caddy（推荐作为反向代理）。

## 2) 准备数据库

创建数据库与用户，并与顶层 `.env` 保持一致（该文件与本文档同级）：

```bash
sudo -u postgres psql
```

```sql
CREATE USER app_user WITH PASSWORD 'strong_password';
CREATE DATABASE app OWNER app_user;
```

更新 `.env`：

```dotenv
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=app_user
POSTGRES_PASSWORD=strong_password
```

## 3) 安装依赖

```bash
cd /opt/ai-pic__ai-emoji-revcat-gpt/backend
uv sync
```

## 4) 迁移与初始化数据

```bash
cd /opt/ai-pic__ai-emoji-revcat-gpt/backend
source .venv/bin/activate
bash scripts/prestart.sh
```

## 5) 创建 systemd 服务

创建 `/etc/systemd/system/ai-emoji-backend.service`：

```ini
[Unit]
Description=AI Emoji FastAPI Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-pic__ai-emoji-revcat-gpt/backend
EnvironmentFile=/opt/ai-pic__ai-emoji-revcat-gpt/.env
ExecStart=/opt/ai-pic__ai-emoji-revcat-gpt/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

重载并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-emoji-backend
sudo systemctl status ai-emoji-backend
```

## 6) Nginx 反向代理（示例）

创建 `/etc/nginx/sites-available/ai-emoji.conf`：

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用并重载：

```bash
sudo ln -s /etc/nginx/sites-available/ai-emoji.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 7) 说明

- Adminer 为 Docker 组件，非 Docker 部署可使用任意 DB 客户端替代。
- Redis 为可选项，未运行时 emoji 队列会提示 “Queue unavailable”，服务仍可启动。
- 若需要 HTTPS，可在 Nginx/Caddy 中配置 TLS。

# FastAPI 项目 - 部署（非 Docker）

本文描述在 Linux 服务器上的非 Docker 部署方式
（systemd + Nginx + PostgreSQL）。请按实际环境调整路径与版本。
Docker 方案请见 [Docker 部署](docker.zh-CN.md)。

## 前置条件

- Linux 服务器（Python 3.10+）
- PostgreSQL（必需）
- Redis（可选，Emoji 队列会用到）
- Nginx 或 Caddy 作为反向代理（推荐）

## 1) 准备数据库

创建与 `.env` 匹配的数据库与用户（与本文同级的根目录 `.env`）。
示例（PostgreSQL）：

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

## 2) 安装依赖

```bash
cd /opt/ai-pic__ai-emoji-revcat-gpt/backend
uv sync
```

## 3) 运行迁移与初始化数据

```bash
cd /opt/ai-pic__ai-emoji-revcat-gpt/backend
source .venv/bin/activate
bash scripts/prestart.sh
```

## 4) 创建 systemd 服务

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

## 5) Nginx 反向代理（示例）

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

## 备注

- Adminer 是 Docker 方案专用组件；请使用你习惯的数据库客户端。
- Redis 可选；如果未运行 Redis，Emoji 队列会返回 “Queue unavailable”，但 API 仍可启动。
- HTTPS 可通过 Nginx 配置证书，或使用 Caddy 自动签发。

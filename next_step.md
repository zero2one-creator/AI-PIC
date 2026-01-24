# Next Steps: 非 Docker 部署所需的剩余工作

下面按“必须完成 → 建议完成”的顺序列出步骤，并给出具体怎么做的操作指引。
目标：让后端 API、数据库、Redis、Emoji Worker 都能稳定跑起来，并且订阅/OSS/阿里云 AI 等功能可用。

---

## 1) 准备基础设施与账号（必须）

1. **服务器**
   - 一台可公网访问的服务器（Ubuntu 22.04 LTS 推荐）。
   - 已安装 Python 3.11+，并准备好构建工具（`build-essential`、`libpq-dev` 等）。

2. **外部依赖服务**
   - **PostgreSQL**：本机安装或远端托管均可。
   - **Redis**：本机安装或远端托管均可。
   - **OSS**：准备阿里云 OSS Bucket + AccessKey。
   - **阿里云 AI**：准备 Emoji AI 的 API Key + Endpoint。
   - **RevenueCat**：准备 API Key + Webhook Secret。
   - **Nacos（可选）**：若想动态配置可部署，否则可不启用（API 会返回本地默认配置）。

---

## 2) 配置 `.env`（必须）

编辑项目根目录 `.env`，至少设置：

```env
ENVIRONMENT=production
DOMAIN=your-domain.com
STACK_NAME=pickitchen
PROJECT_NAME=PicKitchen

SECRET_KEY=please-change
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=please-change
POSTGRES_USER=postgres
POSTGRES_PASSWORD=please-change
POSTGRES_DB=pickitchen
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432

BACKEND_CORS_ORIGINS=https://your-frontend-domain.com

# Redis（必须）
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# OSS（必须用于上传/结果保存）
OSS_ACCESS_KEY_ID=xxx
OSS_ACCESS_KEY_SECRET=xxx
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=your-bucket

# 阿里云 AI（必须用于 emoji 生成）
ALIYUN_AI_API_KEY=xxx
ALIYUN_AI_ENDPOINT=https://xxx.aliyuncs.com

# RevenueCat（订阅系统）
REVENUECAT_API_KEY=xxx
REVENUECAT_WEBHOOK_SECRET=xxx

# Snowflake（多实例时建议不同）
DATACENTER_ID=0
WORKER_ID=0
```

> 如果你不使用 Nacos，可以先不填 NACOS_*。
> 若要启用 Nacos，在 `.env` 中加入 `NACOS_SERVER_ADDRESSES` 等配置即可。

---

## 3) 创建数据库与用户（必须）

本机 Postgres 示例（远端托管请跳过）：

```bash
sudo -u postgres psql
```

```sql
CREATE USER pickitchen WITH PASSWORD 'please-change';
CREATE DATABASE pickitchen OWNER pickitchen;
```

确保 `.env` 中 `POSTGRES_*` 与数据库配置一致。

---

## 4) 安装后端依赖（必须）

```bash
cd backend
uv sync
```

---

## 5) 迁移与初始化（必须）

```bash
cd backend
uv run bash scripts/prestart.sh
```

> `prestart` 会自动执行：
> - 等数据库就绪
> - 运行 Alembic 迁移
> - 创建初始用户

---

## 6) 启动后端 API（必须）

开发模式：

```bash
cd backend
uv run fastapi dev app/main.py
```

生产模式（示例）：

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 7) 启动 Emoji Worker（必须，否则任务不处理）

```bash
cd backend
uv run python app/worker/emoji_worker.py
```

---

## 8) 定时积分发放（已内置）

```bash
cd backend
uv run python app/worker/scheduler.py
```

---

## 9) 反向代理与 HTTPS（可选但建议）

可使用 Nginx/Apache 做反向代理，并通过证书实现 HTTPS。以下为 Nginx 方向的最小思路：

- 反向代理到 `127.0.0.1:8000`
- 配置 `client_max_body_size` 以支持图片上传
- 使用 Certbot 或你现有证书配置 HTTPS

---

## 10) 验证部署（必须）

1. 健康检查：
   ```
   https://api.<your-domain>/api/v1/utils/health-check/
   ```
2. 登录获取 token：
   ```
   POST /api/v1/login/access-token
   ```
3. 上传图片、创建 emoji 任务，确认 worker 会更新状态。

---

## 11) 订阅与 Webhook（必须）

在 RevenueCat 控制台配置 Webhook：

```
POST https://api.<your-domain>/api/v1/subscription/webhook
```

并填入 `REVENUECAT_WEBHOOK_SECRET` 用于签名校验。

---

## 12) 上线前建议检查（可选但强烈建议）

- 确保 `.env` 中默认密码已更换
- 生产环境开启 HTTPS
- 配置日志收集/监控（Sentry 已支持）
- 限制管理端点的访问范围

---

## 如需我继续

你可以告诉我：
- 是否需要我帮你生成 systemd service 文件
- 是否需要我根据你的云厂商做定制化部署步骤
- 是否需要我补充运行监控/告警方案

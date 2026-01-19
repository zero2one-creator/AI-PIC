# Next Steps: 完成部署所需的剩余工作

下面按“必须完成 → 建议完成”的顺序列出步骤，并给出具体怎么做的操作指引。  
目标：让后端 API、数据库、Redis、Emoji Worker 都能稳定跑起来，并且订阅/OSS/阿里云 AI 等功能可用。

---

## 1) 准备基础设施与账号（必须）

1. **服务器与 DNS**
   - 一台可公网访问的服务器（Docker Engine 已安装）。
   - DNS 解析指向服务器 IP：
     - `api.<your-domain>` → 后端 API
     - `adminer.<your-domain>` → Adminer（可选）
     - `traefik.<your-domain>` → Traefik 控制台（可选）

2. **外部依赖服务**
   - **PostgreSQL**：已包含在 `docker-compose.yml`。
   - **Redis**：已包含在 `docker-compose.yml`。
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
POSTGRES_SERVER=db
POSTGRES_PORT=5432

BACKEND_CORS_ORIGINS=https://your-frontend-domain.com

# Redis（必须）
REDIS_HOST=redis
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

## 3) 启动 Traefik（可选但建议用于 HTTPS）

按 `deployment.md` 的“Public Traefik”部分操作，确保：

- 已创建 `traefik-public` 网络：
  ```bash
  docker network create traefik-public
  ```
- 服务器上已启动 Traefik：
  ```bash
  docker compose -f docker-compose.traefik.yml up -d
  ```

---

## 4) 启动 Redis（必须）

`docker-compose.yml` 已内置 Redis 服务。请确认 `.env` 中：
```
REDIS_HOST=redis
```
然后直接执行 `docker compose up -d` 即可。

---

## 5) 部署后端（必须）

在服务器上执行（生产建议不带 override）：
```bash
docker compose -f docker-compose.yml up -d
```

> `prestart` 会自动执行：
> - 等数据库就绪
> - 运行 Alembic 迁移
> - 创建初始用户

---

## 6) 启动 Emoji Worker（必须，否则任务不处理）

`docker-compose.yml` 已内置 `worker` 服务，会自动启动。

---

## 7) 定时积分发放（已内置）

`docker-compose.yml` 已内置 `scheduler` 服务，每周一 00:00 UTC 发放积分。

---

## 8) 验证部署（必须）

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

## 9) 订阅与 Webhook（必须）

在 RevenueCat 控制台配置 Webhook：

```
POST https://api.<your-domain>/api/v1/subscription/webhook
```

并填入 `REVENUECAT_WEBHOOK_SECRET` 用于签名校验。

---

## 10) 仍未完成的功能（可选）

当前无阻塞项。

---

## 11) 上线前建议检查（可选但强烈建议）

- 确保 `.env` 中默认密码已更换
- 生产环境开启 HTTPS（Traefik）
- 配置日志收集/监控（Sentry 已支持）
- 限制 Adminer 暴露或关闭

---

## 如需我继续

你可以告诉我：
- 是否需要我帮你生成更精简的部署脚本
- 是否需要我根据你的云厂商做定制化部署步骤
- 是否需要我补充运行监控/告警方案

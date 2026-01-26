# 🚀 PicKitchen AI Backend 部署指南

本文档指导你完成项目的完整部署流程。

---

## ✅ 已完成的工作

- ✅ 代码审查和 Bug 修复（4个关键 Bug 已修复）
- ✅ 所有测试通过（31/31）
- ✅ 代码质量达到生产标准
- ✅ 文档更新完成

---

## 📋 待完成任务清单

### 阶段 1: 数据库迁移 🗄️

#### 1.1 启动本地数据库
```bash
# 在项目根目录
docker compose up -d db redis
```

#### 1.2 生成并应用迁移文件
```bash
cd backend

# 生成迁移文件（包含周奖励唯一约束）
uv run alembic revision --autogenerate -m "Add unique constraint for weekly rewards and bug fixes"

# 检查生成的迁移文件
ls -la app/alembic/versions/

# 应用迁移
uv run alembic upgrade head
```

#### 1.3 验证迁移结果
```bash
# 连接数据库检查索引是否创建成功
docker compose exec db psql -U postgres -d app -c "\d point_transactions"

# 应该看到 idx_user_reward_week 索引
```

**预期结果**:
- `point_transactions` 表有唯一部分索引 `idx_user_reward_week`
- 所有表使用 Snowflake ID (bigint 类型)

---

### 阶段 2: 环境配置 ⚙️

#### 2.1 生产环境配置文件

创建 `.env.production` 文件（**不要提交到 Git**）:

```bash
# 复制模板
cp .env .env.production
```

编辑 `.env.production`，**必须修改**以下配置:

```bash
# ========== 安全配置（必改！）==========
SECRET_KEY="your-super-secret-key-min-32-chars-$(openssl rand -hex 16)"
POSTGRES_PASSWORD="your-strong-db-password-$(openssl rand -hex 12)"
REVENUECAT_WEBHOOK_SECRET="your-revenuecat-webhook-secret"

# ========== 数据库配置 ==========
POSTGRES_SERVER=your-db-host.com
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_DB=pickitchen_prod

# ========== Redis 配置 ==========
REDIS_HOST=your-redis-host.com
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# ========== Snowflake ID 配置 ==========
# 每个实例必须唯一！范围 0-1023
# 实例1: SNOWFLAKE_NODE_ID=0
# 实例2: SNOWFLAKE_NODE_ID=1
SNOWFLAKE_NODE_ID=0

# ========== 阿里云 OSS 配置 ==========
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=pickitchen-prod
OSS_ACCESS_KEY_ID=your-oss-access-key-id
OSS_ACCESS_KEY_SECRET=your-oss-access-key-secret
OSS_DIR_PREFIX=uploads
OSS_RESULT_PREFIX=results
OSS_UPLOAD_EXPIRE_SECONDS=300
OSS_OBJECT_ACL=public-read

# ========== 阿里云 DashScope API ==========
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DASHSCOPE_API_KEY=your-dashscope-api-key
ALIYUN_EMOJI_MOCK=false  # 生产环境必须为 false
EMOJI_POLL_INTERVAL_SECONDS=2
EMOJI_POLL_TIMEOUT_SECONDS=300

# ========== 其他配置 ==========
ENVIRONMENT=production
PROJECT_NAME="PicKitchen AI"
BACKEND_CORS_ORIGINS=["https://your-frontend-domain.com"]
```

#### 2.2 配置文件准备

编辑 `backend/app/config/default_config.json`:

```json
{
  "points_rules": {
    "emoji": 200
  },
  "vip_products": {
    "com.pickitchen.weekly": "weekly",
    "com.pickitchen.lifetime": "lifetime"
  },
  "points_packs": {
    "com.pickitchen.points_500": 500,
    "com.pickitchen.points_1000": 1000,
    "com.pickitchen.points_5000": 5000
  },
  "weekly_reward": {
    "weekly": 2000,
    "lifetime": 3000
  }
}
```

---

### 阶段 3: 本地测试 🧪

#### 3.1 完整本地测试
```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f backend

# 运行测试
docker compose exec backend bash scripts/tests-start.sh

# 测试 API
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/docs
```

#### 3.2 测试关键流程

**测试 1: 用户注册和登录**
```bash
# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test-device-123"}'

# 保存返回的 access_token
TOKEN="your-access-token"

# 获取用户信息
curl http://localhost:8000/api/v1/user/profile \
  -H "Authorization: Bearer $TOKEN"
```

**测试 2: 积分系统**
```bash
# 查看积分余额
curl http://localhost:8000/api/v1/points/balance \
  -H "Authorization: Bearer $TOKEN"
```

**测试 3: Emoji 上传**
```bash
# 获取上传凭证
curl -X POST "http://localhost:8000/api/v1/emoji/upload?ext=jpg" \
  -H "Authorization: Bearer $TOKEN"
```

**测试 4: RevenueCat Webhook**
```bash
# 测试 webhook（使用你的 webhook secret）
curl -X POST http://localhost:8000/api/v1/subscription/webhook \
  -H "Authorization: Bearer your-webhook-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "id": "test-event-123",
      "type": "TEST",
      "app_user_id": "123456789",
      "product_id": "com.pickitchen.weekly"
    }
  }'
```

---

### 阶段 4: Worker 部署 🔧

#### 4.1 Emoji Worker（长期运行）

**Docker Compose 方式**（推荐）:

编辑 `docker-compose.yml`，确保包含:
```yaml
services:
  emoji-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python -m worker.emoji_worker
    environment:
      - EMOJI_WORKER_CONSUMER=worker-1
    depends_on:
      - db
      - redis
    restart: unless-stopped
```

启动:
```bash
docker compose up -d emoji-worker
docker compose logs -f emoji-worker
```

**手动运行方式**:
```bash
cd backend
source .venv/bin/activate
EMOJI_WORKER_CONSUMER=worker-1 python -m worker.emoji_worker
```

#### 4.2 Weekly Points Reward（定时任务）

**使用 Cron**:
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周日凌晨 0:00 UTC 运行）
0 0 * * 0 cd /path/to/spokane/backend && /path/to/.venv/bin/python -m worker.weekly_points_reward >> /var/log/weekly_reward.log 2>&1
```

**使用 Docker + Cron**:

创建 `docker-compose.cron.yml`:
```yaml
services:
  weekly-reward:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python -m worker.weekly_points_reward
    depends_on:
      - db
    restart: "no"
```

添加到系统 cron:
```bash
0 0 * * 0 cd /path/to/spokane && docker compose -f docker-compose.cron.yml up weekly-reward
```

---

### 阶段 5: 生产部署 🚀

#### 5.1 部署前检查清单

- [ ] `.env.production` 所有敏感配置已修改
- [ ] 数据库迁移已在生产环境执行
- [ ] OSS bucket 已创建并配置 CORS
- [ ] DashScope API Key 已申请并测试
- [ ] RevenueCat webhook 已配置指向你的服务器
- [ ] Redis 已部署并可访问
- [ ] 防火墙规则已配置（开放必要端口）
- [ ] SSL 证书已配置（推荐使用 Let's Encrypt）
- [ ] 监控和日志系统已就绪

#### 5.2 部署方式选择

**方式 A: Docker Compose（适合单机部署）**

```bash
# 在生产服务器上
git clone <your-repo>
cd spokane

# 复制生产配置
cp .env.production .env

# 构建并启动
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看状态
docker compose ps
docker compose logs -f
```

**方式 B: Kubernetes（适合集群部署）**

需要准备:
1. Kubernetes 集群
2. Helm charts（需要创建）
3. ConfigMap 和 Secret 配置
4. Ingress 配置

**方式 C: 云服务（AWS/阿里云/腾讯云）**

推荐使用:
- 阿里云 ECS + RDS + Redis + OSS
- AWS EC2 + RDS + ElastiCache + S3
- 容器服务（阿里云 ACK / AWS ECS）

#### 5.3 生产环境数据库迁移

```bash
# SSH 到生产服务器
ssh user@your-production-server

# 进入项目目录
cd /path/to/spokane/backend

# 备份数据库（重要！）
docker compose exec db pg_dump -U postgres app > backup_$(date +%Y%m%d_%H%M%S).sql

# 应用迁移
uv run alembic upgrade head

# 验证
uv run alembic current
```

---

### 阶段 6: 监控和告警 📊

#### 6.1 必须监控的指标

**应用指标**:
- API 响应时间和错误率
- Snowflake ID 生成失败（时钟回拨）
- Redis 连接失败
- 积分余额不足错误
- Emoji 生成任务失败率

**系统指标**:
- CPU 和内存使用率
- 数据库连接池状态
- Redis 队列长度
- 磁盘空间

#### 6.2 推荐的监控工具

**日志收集**:
```bash
# 使用 Sentry（已集成）
# 在 .env 中配置
SENTRY_DSN=your-sentry-dsn
```

**指标监控**:
- Prometheus + Grafana
- 阿里云云监控
- AWS CloudWatch

**告警配置示例**:
```yaml
# Prometheus Alert Rules
groups:
  - name: pickitchen_alerts
    rules:
      - alert: SnowflakeClockDrift
        expr: rate(snowflake_clock_drift_errors[5m]) > 0
        annotations:
          summary: "Snowflake ID generator detected clock drift"

      - alert: RedisConnectionFailed
        expr: rate(redis_connection_errors[5m]) > 0.1
        annotations:
          summary: "Redis connection failures detected"

      - alert: EmojiTaskFailureRate
        expr: rate(emoji_task_failures[5m]) / rate(emoji_task_total[5m]) > 0.1
        annotations:
          summary: "High emoji task failure rate"
```

---

### 阶段 7: RevenueCat 配置 💳

#### 7.1 在 RevenueCat 控制台配置

1. 登录 [RevenueCat Dashboard](https://app.revenuecat.com)
2. 进入 Project Settings → Integrations → Webhooks
3. 添加 Webhook URL: `https://your-domain.com/api/v1/subscription/webhook`
4. 设置 Authorization Header: `Bearer your-webhook-secret`
5. 选择要接收的事件类型:
   - ✅ Initial Purchase
   - ✅ Renewal
   - ✅ Cancellation
   - ✅ Expiration
   - ✅ Billing Issue

#### 7.2 测试 Webhook

在 RevenueCat 控制台发送测试事件，检查:
- 服务器日志中是否收到请求
- 数据库中是否创建了 `revenuecat_events` 记录
- 用户 VIP 状态是否正确更新

---

### 阶段 8: 性能优化（可选）🔥

#### 8.1 数据库优化

```sql
-- 添加常用查询索引
CREATE INDEX CONCURRENTLY idx_emoji_tasks_user_status
ON emoji_tasks(user_id, status);

CREATE INDEX CONCURRENTLY idx_point_transactions_user_created
ON point_transactions(user_id, created_at DESC);

-- 分析表统计信息
ANALYZE users;
ANALYZE emoji_tasks;
ANALYZE point_transactions;
```

#### 8.2 Redis 优化

```bash
# 配置 Redis 持久化
# 编辑 redis.conf
appendonly yes
appendfsync everysec
```

#### 8.3 应用优化

- 启用 FastAPI 的 Gzip 压缩
- 配置 CDN 加速静态资源
- 使用连接池优化数据库连接
- 考虑添加 API 限流

---

## 🆘 常见问题排查

### 问题 1: 数据库连接失败
```bash
# 检查数据库是否运行
docker compose ps db

# 检查连接配置
docker compose exec backend env | grep POSTGRES

# 测试连接
docker compose exec backend python -c "from app.core.db import engine; print(engine.url)"
```

### 问题 2: Redis 连接失败
```bash
# 检查 Redis 是否运行
docker compose ps redis

# 测试连接
docker compose exec backend python -c "from app.core.redis import get_redis; print(get_redis().ping())"
```

### 问题 3: Snowflake ID 时钟回拨错误
```bash
# 检查系统时间
date
timedatectl status

# 启用 NTP 时间同步
sudo timedatectl set-ntp true
```

### 问题 4: Emoji Worker 不处理任务
```bash
# 检查 Redis Stream
docker compose exec redis redis-cli XINFO STREAM emoji_tasks

# 检查 Consumer Group
docker compose exec redis redis-cli XINFO GROUPS emoji_tasks

# 查看 Worker 日志
docker compose logs -f emoji-worker
```

### 问题 5: 迁移文件冲突
```bash
# 查看当前版本
uv run alembic current

# 查看迁移历史
uv run alembic history

# 如果需要回滚
uv run alembic downgrade -1
```

---

## 📚 相关文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLModel 文档](https://sqlmodel.tiangolo.com/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [Redis Streams 文档](https://redis.io/docs/data-types/streams/)
- [RevenueCat Webhooks](https://www.revenuecat.com/docs/webhooks)
- [阿里云 OSS 文档](https://help.aliyun.com/product/31815.html)
- [DashScope API 文档](https://help.aliyun.com/zh/dashscope/)

---

## ✅ 部署完成检查

部署完成后，确认以下所有项目:

- [ ] 所有服务正常运行（backend, db, redis, workers）
- [ ] API 健康检查通过 (`/api/v1/health`)
- [ ] Swagger 文档可访问 (`/docs`)
- [ ] 用户可以注册和登录
- [ ] 积分系统正常工作
- [ ] Emoji 上传和生成流程完整
- [ ] RevenueCat webhook 接收正常
- [ ] 周奖励定时任务配置完成
- [ ] 监控和告警已配置
- [ ] 日志正常输出
- [ ] 数据库备份策略已制定

---

## 🎉 恭喜！

如果所有检查项都通过，你的 PicKitchen AI Backend 已经成功部署！

**下一步建议**:
1. 进行压力测试，评估系统容量
2. 制定灾难恢复计划
3. 编写运维文档
4. 培训运维团队
5. 准备上线发布

**需要帮助？**
- 查看 `CLAUDE.md` 了解项目架构
- 查看代码注释了解实现细节
- 运行测试了解预期行为

祝你部署顺利！🚀

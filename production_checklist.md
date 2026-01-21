# Production Deployment Checklist

## 基础准备
- [ ] 服务器已安装 Docker Engine（非 Docker Desktop）
- [ ] DNS 已指向服务器 IP：`api.<domain>` / `adminer.<domain>`（可选）/ `traefik.<domain>`（可选）
- [ ] 防火墙放行 80/443（如使用 HTTPS）

## 环境变量与密钥
- [ ] `.env` 已设置 `ENVIRONMENT=production`
- [ ] `SECRET_KEY` / `FIRST_SUPERUSER_PASSWORD` / `POSTGRES_PASSWORD` 已替换为强密码
- [ ] `BACKEND_CORS_ORIGINS` 已配置前端域名
- [ ] OSS 配置已填写（上传与结果保存）
- [ ] 阿里云 AI 配置已填写（Emoji 生成）
- [ ] RevenueCat 配置已填写（订阅 + Webhook）
- [ ] Redis 配置已填写（任务队列 + 锁）

## Traefik / HTTPS（建议）
- [ ] 已创建 `traefik-public` 网络
- [ ] Traefik 已运行并可签发证书

## 服务启动
- [ ] `docker compose -f docker-compose.yml up -d` 已执行
- [ ] `backend` / `worker` / `scheduler` / `redis` / `db` 均处于 `healthy` 或 `running`

## 数据库
- [ ] Alembic migrations 已自动执行（`prestart`）
- [ ] 初始超级管理员已创建
- [ ] 已配置数据库备份策略（快照或定期导出）

## Webhook
- [ ] RevenueCat Webhook 指向：`https://api.<domain>/api/v1/subscription/webhook`
- [ ] Webhook Secret 与 `.env` 一致

## 功能验证
- [ ] `GET /api/v1/utils/health-check/` 返回 `true`
- [ ] 登录成功并可获取 token
- [ ] 图片上传成功，任务进入队列
- [ ] Worker 能更新任务状态并生成结果 URL

## 监控与日志
- [ ] Sentry 已配置（如需）
- [ ] 日志采集可用（Docker logs 或集中日志）
- [ ] Adminer 暴露已限制或关闭（生产建议）


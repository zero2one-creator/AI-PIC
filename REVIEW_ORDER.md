# 代码审查顺序

1) 阅读 `README.md` 和 `development.md`，了解项目目标、运行方式与环境结构。
2) 查看 `.env` 与 `backend/app/core/config.py`，确认必须配置项、默认值与安全项。
3) 阅读 `backend/app/main.py`，理解应用入口、路由注册、中间件与异常处理。
4) 审核 `backend/app/core/`：认证、安全、数据库、Redis 等基础能力。
5) 审核 `backend/app/models.py`，理解领域模型与约束。
6) 审核 `backend/app/api/schemas.py`，核对请求/响应结构与校验规则。
7) 审核 `backend/app/api/deps.py`，检查认证与依赖注入、权限控制。
8) 按顺序审查 `backend/app/api/routes/`：`utils.py`、`users.py`、`auth.py`、`emoji.py`、`orders.py`、`subscription.py`。
9) 审核 `backend/app/services/`，关注业务流程编排与边界处理。
10) 审核 `backend/app/integrations/`（OSS、Aliyun、RevenueCat、Nacos），关注外部 IO 与错误处理。
11) 审核 `backend/app/alembic/` 迁移，检查 schema 演进与数据安全。
12) 审核 `backend/scripts/`，了解启动与测试流程。
13) 扫描 `backend/tests/`，评估覆盖范围与关键路径测试。

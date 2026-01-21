# CLAUDE.md

本文件用于在 Claude Code（claude.ai/code）处理此仓库代码时提供指导信息。

## 项目概览

Backend FastAPI Template：一个可用于生产环境的后端 API 模板，基于 FastAPI、PostgreSQL 和 Docker Compose。

## 常用命令

### 开发

```bash
# 启动服务（推荐用于本地开发）
docker compose watch

# 查看日志
docker compose logs backend
docker compose logs db
docker compose logs adminer
```

### Backend（在 backend/ 目录下执行）

```bash
# 安装依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate

# 运行本地开发服务（不使用 Docker）
fastapi dev app/main.py

# 在 Docker 中运行测试（在项目根目录执行）
docker compose exec backend bash scripts/tests-start.sh

# 运行单个测试
docker compose exec backend bash scripts/tests-start.sh -x tests/path/to/test.py::test_name

# 创建数据库迁移
alembic revision --autogenerate -m "Description"

# 应用迁移
alembic upgrade head
```

### 代码质量

```bash
# 安装 pre-commit hooks（在 backend/ 下执行）
uv run prek install -f

# 手动运行全部 pre-commit 检查
uv run prek run --all-files

# Lint 与格式化
uv run ruff check --fix
uv run ruff format
```

## 架构

### 后端结构（backend/app/）

- `main.py` - FastAPI 应用初始化、CORS、Sentry 配置
- `models.py` - SQLModel 数据库模型与 Pydantic schema（User、Item、Token）
- `crud.py` - 数据库 CRUD 操作
- `core/config.py` - 通过 pydantic-settings 管理配置（从 ../.env 读取）
- `core/db.py` - 数据库会话管理
- `core/security.py` - 密码哈希、JWT token 处理
- `api/main.py` - API 路由聚合
- `api/routes/` - 各端点模块（login、users、items、utils、private）
- `api/deps.py` - FastAPI 依赖项（认证、DB session）
- `alembic/` - 数据库迁移

### 关键模式

- **API 版本管理**：所有端点位于 `/api/v1` 下
- **认证**：通过 `/api/v1/login/access-token` 获取 JWT token
- **数据库模型**：SQLModel 类对 DB 表使用 `table=True`；不带 `table=True` 的类用于 Pydantic schema

### 开发环境地址

- 后端 API：http://localhost:8000
- API 文档（Swagger）：http://localhost:8000/docs
- Adminer（数据库管理）：http://localhost:8080
- MailCatcher：http://localhost:1080

## 配置

环境变量位于项目根目录的 `.env`。关键配置包括：

- `SECRET_KEY`、`POSTGRES_PASSWORD`、`FIRST_SUPERUSER_PASSWORD` - 在非本地环境必须从默认值 "changethis" 修改
- 后端通过 `backend/app/core/config.py` 使用 `pydantic-settings` 读取配置


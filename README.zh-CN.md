# FastAPI 后端模板

这是一个可用于生产环境的后端 API 模板，基于 FastAPI、PostgreSQL 和 Docker Compose。

## 包含内容

- ⚡ FastAPI 后端 API
- 🧰 SQLModel（ORM）+ Pydantic 配置（settings）
- 💾 PostgreSQL 数据库
- 🔑 JWT 身份认证
- 📫 基于邮箱的密码找回（基于 token，纯 API）
- 📬 Mailcatcher（本地邮件测试）
- 🗄️ Adminer（数据库管理）
- 🐋 Docker Compose（本地开发与部署）
- 📞 通过 Docker labels 集成 Traefik（可选）

## 快速开始（Docker）

```bash
docker compose up -d --build
```

- API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- Adminer: http://localhost:8080
- Mailcatcher: http://localhost:1080

## 文档

- 后端文档：`backend/README.md`
- 开发（Docker）：`docs/development/docker.zh-CN.md`
- 部署（Docker）：`docs/deployment/docker.zh-CN.md`

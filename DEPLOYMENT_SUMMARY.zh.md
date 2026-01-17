# 项目部署方案总结

## 📋 部署架构概览

这个项目采用 **Docker Compose + Traefik + GitHub Actions** 的部署方案，支持多环境（Staging/Production）自动部署。

```
┌─────────────────────────────────────────────────────────┐
│                    外部访问 (HTTPS)                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Traefik 反向代理 (端口 80/443)              │
│  - 自动 HTTPS 证书 (Let's Encrypt)                        │
│  - 路由分发到不同服务                                     │
│  - 统一入口管理                                           │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
    ┌──────────────────┐      ┌──────────────────┐
    │   FastAPI 后端    │      │   React 前端      │
    │  api.domain.com   │      │dashboard.domain.com│
    └────────┬──────────┘      └──────────────────┘
             │
             ▼
    ┌──────────────────┐
    │  PostgreSQL 数据库│
    │   (容器内)        │
    └──────────────────┘
```

## 🏗️ 核心组件

### 1. **Traefik 反向代理** (公共层)
- **作用**: 统一入口，处理 HTTPS 证书，路由分发
- **位置**: 独立部署 (`docker-compose.traefik.yml`)
- **功能**:
  - 自动申请和续期 Let's Encrypt SSL 证书
  - HTTP 自动重定向到 HTTPS
  - 基于域名的路由分发
  - 提供 Traefik Dashboard 管理界面

### 2. **应用服务栈** (业务层)
- **后端**: FastAPI (Python)
- **前端**: React (Nginx 静态文件)
- **数据库**: PostgreSQL
- **数据库管理**: Adminer

## 🌐 域名结构

### 生产环境 (Production)
```
https://traefik.fastapi-project.example.com    # Traefik 管理界面
https://api.fastapi-project.example.com        # 后端 API
https://dashboard.fastapi-project.example.com  # 前端界面
https://adminer.fastapi-project.example.com   # 数据库管理
```

###  staging 环境 (Staging)
```
https://api.staging.fastapi-project.example.com        # 后端 API
https://dashboard.staging.fastapi-project.example.com  # 前端界面
https://adminer.staging.fastapi-project.example.com   # 数据库管理
```

## 📦 部署方式

### 方式一：手动部署 (Docker Compose)

#### 步骤 1: 准备服务器
```bash
# 1. 准备远程服务器
# 2. 配置 DNS 记录指向服务器 IP
# 3. 配置通配符子域 (*.example.com)
# 4. 安装 Docker Engine
```

#### 步骤 2: 部署 Traefik (只需一次)
```bash
# 在服务器上创建目录
mkdir -p /root/code/traefik-public/

# 复制 Traefik 配置文件
rsync -a docker-compose.traefik.yml root@your-server:/root/code/traefik-public/

# 创建公共网络
docker network create traefik-public

# 设置环境变量
export USERNAME=admin
export PASSWORD=your-password
export HASHED_PASSWORD=$(openssl passwd -apr1 $PASSWORD)
export DOMAIN=fastapi-project.example.com
export EMAIL=admin@example.com

# 启动 Traefik
cd /root/code/traefik-public/
docker compose -f docker-compose.traefik.yml up -d
```

#### 步骤 3: 部署应用
```bash
# 设置环境变量
export ENVIRONMENT=production
export DOMAIN=fastapi-project.example.com
export STACK_NAME=fastapi-project-example-com
export SECRET_KEY=your-secret-key
export FIRST_SUPERUSER=admin@example.com
export FIRST_SUPERUSER_PASSWORD=your-password
export POSTGRES_PASSWORD=your-db-password
# ... 其他环境变量

# 部署应用
docker compose -f docker-compose.yml up -d
```

### 方式二：自动部署 (GitHub Actions CI/CD) ⭐推荐

#### 前置条件
1. **在服务器上安装 GitHub Actions Runner**
   ```bash
   # 创建 github 用户
   sudo adduser github
   sudo usermod -aG docker github
   
   # 切换到 github 用户并安装 runner
   sudo su - github
   # 按照 GitHub 官方指南安装 self-hosted runner
   # 添加标签: staging 或 production
   
   # 安装为系统服务
   cd /home/github/actions-runner
   ./svc.sh install github
   ./svc.sh start
   ```

2. **在 GitHub 仓库配置 Secrets**
   - `DOMAIN_PRODUCTION` - 生产环境域名
   - `DOMAIN_STAGING` - 测试环境域名
   - `STACK_NAME_PRODUCTION` - 生产环境堆栈名
   - `STACK_NAME_STAGING` - 测试环境堆栈名
   - `SECRET_KEY` - 应用密钥
   - `FIRST_SUPERUSER` - 超级用户邮箱
   - `FIRST_SUPERUSER_PASSWORD` - 超级用户密码
   - `POSTGRES_PASSWORD` - 数据库密码
   - `EMAILS_FROM_EMAIL` - 发件邮箱
   - `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` - SMTP 配置
   - `SENTRY_DSN` - (可选) Sentry 错误追踪

#### 自动部署流程

**Staging 环境**:
- **触发条件**: 推送到 `master` 分支
- **工作流文件**: `.github/workflows/deploy-staging.yml`
- **Runner 标签**: `staging`

**Production 环境**:
- **触发条件**: 发布 Release
- **工作流文件**: `.github/workflows/deploy-production.yml`
- **Runner 标签**: `production`

## 🔧 关键配置说明

### Docker Compose 网络架构
```
traefik-public (外部网络)
    ├── Traefik
    ├── Backend
    ├── Frontend
    └── Adminer

default (内部网络)
    ├── Backend
    ├── Frontend
    ├── Database
    └── Prestart (迁移任务)
```

### 服务启动顺序
1. **Database** - PostgreSQL 数据库
2. **Prestart** - 数据库迁移和初始化
3. **Backend** - FastAPI 后端服务
4. **Frontend** - React 前端服务
5. **Adminer** - 数据库管理工具

### 环境变量管理

**必需的环境变量**:
- `ENVIRONMENT`: `production` 或 `staging`
- `DOMAIN`: 主域名
- `STACK_NAME`: Docker Compose 项目名称
- `SECRET_KEY`: JWT 签名密钥
- `POSTGRES_PASSWORD`: 数据库密码
- `FIRST_SUPERUSER`: 初始管理员邮箱
- `FIRST_SUPERUSER_PASSWORD`: 初始管理员密码

**生成安全密钥**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🚀 部署流程总结

### 首次部署
1. ✅ 准备服务器和域名
2. ✅ 部署 Traefik (一次性)
3. ✅ 配置 GitHub Secrets
4. ✅ 安装 GitHub Actions Runner
5. ✅ 推送代码触发自动部署

### 日常更新
- **Staging**: 直接推送到 `master` 分支自动部署
- **Production**: 创建 Release 自动部署

## 📝 注意事项

1. **Traefik 只需部署一次**: 一个 Traefik 可以管理多个应用栈
2. **环境隔离**: Staging 和 Production 使用不同的 `STACK_NAME` 和域名
3. **安全密钥**: 生产环境必须更改所有默认的 `changethis` 值
4. **数据库持久化**: 使用 Docker volumes 保存数据
5. **HTTPS 证书**: Traefik 自动管理，无需手动配置

## 🔍 监控和调试

- **Traefik Dashboard**: `https://traefik.your-domain.com`
- **查看日志**: `docker compose logs [service-name]`
- **健康检查**: 后端提供 `/api/v1/utils/health-check/` 端点
- **数据库管理**: `https://adminer.your-domain.com`

## 📚 相关文档

- 详细部署指南: [deployment.md](./deployment.md) / [deployment.zh.md](./deployment.zh.md)
- 开发环境配置: [development.md](./development.md) / [development.zh.md](./development.zh.md)
- 后端文档: [backend/README.md](./backend/README.md)
- 前端文档: [frontend/README.md](./frontend/README.md)

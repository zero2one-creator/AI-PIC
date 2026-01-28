# Docker 入门（本项目版 · 深入）

本教程面向 **从未用过 Docker 的 macOS 同学**，但会讲到比入门更深入的概念，并紧贴本项目的实际用法。

你会学到：
- Docker/Compose 的核心概念（镜像、层、容器、网络、卷、缓存、Registry、健康检查等）
- 本项目的服务结构与启动顺序
- 外部 PostgreSQL/Redis 的连接方式（macOS）
- 常见问题与排查方法

---

## 1. 本项目的 Docker 方案“全景图”

### 1.1 关键文件

- `docker-compose.yml`：核心服务（后端、worker、adminer、prestart）
- `docker-compose.override.yml`：本地开发增强（proxy、mailcatcher、热更新）
- `docker-compose.traefik.yml`：公共 Traefik（线上 HTTPS 入口）
- `backend/Dockerfile`：后端镜像构建定义
- `.env`：运行时配置（数据库/Redis/密钥等）

### 1.2 服务关系

```
外部 PostgreSQL / Redis
          ↑
       prestart  →  backend
          ↓           ↓
        worker      (API)

adminer  （可选 UI）
proxy    （仅本地）
mailcatcher（仅本地）
```

核心点：**数据库和 Redis 不在 Docker 中启动**，Docker 只负责后端服务本身。

---

## 2. Docker 概念深入（结合本项目）

### 2.1 镜像（Image）= 可运行的软件快照

镜像是“打包好的软件环境 + 可执行程序”。
本项目的后端镜像由 `backend/Dockerfile` 构建：

- 基础镜像：`public.ecr.aws/docker/library/python:3.10`
- 依赖安装：使用 `uv`（会利用缓存加速）
- 最终镜像名：`backend:latest`

**镜像标签（tag）**
- `backend:latest` 是一个标签，不是固定版本
- 生产环境会用明确版本号（如 `backend:2025.01.28`）

**镜像来自哪里（Registry）**
- `public.ecr.aws`：AWS 的公共镜像仓库
- `docker.io`：Docker Hub（默认）

---

### 2.2 层（Layer）与构建缓存

镜像是由多层组成的，每一层对应 Dockerfile 的一条指令。

好处：
- 当某层没有变化时，Docker 会复用缓存，不重新构建
- 依赖安装和代码复制分开，构建更快

本项目里：
- 改 `pyproject.toml` 会触发依赖层重建
- 只改代码（`./app`）会复用依赖层

常用命令：

```bash
# 使用缓存构建（默认）
docker compose build backend

# 不使用缓存
docker compose build --no-cache backend
```

---

### 2.3 容器（Container）= 镜像的运行实例

容器是“正在运行的镜像”。
比如：

- `ai-pic-backend-1`：后端 API
- `ai-pic-worker-1`：后台任务

容器与镜像的关系：
- 镜像像安装包
- 容器像运行中的程序

**容器生命周期**
- `docker compose up -d` 启动容器
- `docker compose stop` 停止但不删除
- `docker compose down` 停止并删除容器/网络

---

### 2.4 网络（Network）与容器 DNS

Docker 会给每个 Compose 项目建一个默认网络（`default`）。
容器之间可以用 **服务名当作 DNS**。

本项目：
- `default` 网络用于容器之间通信
- `traefik-public` 用于 Traefik 路由（线上是 external，本地 override 设置为 internal）
- 如果数据库/redis 在容器里，`POSTGRES_SERVER=db` 就能访问
- 但现在 **数据库是外部的**，所以要改成 `host.docker.internal`

macOS 下连接宿主机服务：

```dotenv
POSTGRES_SERVER=host.docker.internal
REDIS_HOST=host.docker.internal
```

如果你在 Linux 上，用宿主机 IP。

---

### 2.5 端口映射（Ports）

容器内的服务默认不能被宿主机访问，需要映射端口。
本项目常用端口：

- 后端 API → `http://localhost:8000`
- Adminer → `http://localhost:8080`
- Traefik UI（本地）→ `http://localhost:8090`
- MailCatcher → `http://localhost:1080`

若端口冲突，可改 `docker-compose.override.yml`。

---

### 2.6 环境变量（.env）加载规则

Compose 会读取 `.env`，并注入到容器中：

- `env_file: .env`：整体注入
- `environment:`：追加或覆盖

本项目 **数据库/Redis 必须来自外部**：

```dotenv
POSTGRES_SERVER=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=ai_pic_admin
POSTGRES_PASSWORD=***

REDIS_HOST=host.docker.internal
REDIS_PORT=6379
REDIS_DB=0
```

---

### 2.7 健康检查（healthcheck）与依赖

Compose 支持健康检查 + 依赖关系。
本项目：
- `backend` 有 HTTP 健康检查
- `prestart` 负责 DB 可用性检测 + 迁移
- `backend`、`worker` 依赖 `prestart` 成功

注意：
- `depends_on` 只能保证“启动顺序”，**不能保证外部服务一定可用**
- 所以 `prestart` 脚本内部实现重试

---

### 2.8 卷（Volume）与挂载（Bind Mount）

#### Volume（由 Docker 管理的持久化数据）
通常用于数据库数据（现在我们不用 DB 容器）

#### Bind Mount（宿主机目录挂载）
本项目本地开发会挂载覆盖率目录：

```
./backend/htmlcov:/app/htmlcov
```

这样容器里生成的报告会写到宿主机。

---

### 2.9 Dockerfile 与构建过程（关键指令）

后端镜像由 `backend/Dockerfile` 构建，常见指令含义如下：

- `FROM`：指定基础镜像（Python 3.10）
- `WORKDIR`：容器内默认工作目录
- `COPY`：把宿主机文件复制进镜像
- `RUN`：构建时执行命令（安装依赖）
- `CMD`：容器启动时默认命令

本项目中：
- 依赖安装分两次，最大化缓存命中
- `CMD ["fastapi", "run", "--workers", "4", "app/main.py"]` 是默认启动命令

---

### 2.10 启动命令与 command/entrypoint

容器“启动时运行什么”由 Dockerfile 的 `CMD` 和 Compose 的 `command` 共同决定：

- `prestart` 显式指定 `command: bash scripts/prestart.sh`
- `worker` 指定 `command: ["python", "worker/emoji_worker.py"]`
- `backend` 没有覆写 command，所以使用 Dockerfile 的 `CMD`

这意味着同一个镜像可以用不同命令启动多个服务（backend / worker）。

---

### 2.11 Compose 文件合并规则

Compose 会自动合并：

- `docker-compose.yml`（基础）
- `docker-compose.override.yml`（本地覆盖）

本项目在 macOS 本地运行时默认会带上 override：
- 增加 `proxy` / `mailcatcher`
- 启用 `docker compose watch` 热更新

如果只想运行基础配置：

```bash
docker compose -f docker-compose.yml up -d
```

---

### 2.12 Compose 项目名与容器命名

Compose 会用“目录名”作为项目名。当前目录名为 `AI-PIC`，实际容器名会变成：

- `ai-pic-backend-1`
- `ai-pic-worker-1`

如果想自定义项目名，可以使用：

```bash
COMPOSE_PROJECT_NAME=myproject docker compose up -d
```

---

### 2.13 查看最终配置（排查时很有用）

Compose 会把多个文件合并成最终配置，你可以用下面的命令查看：

```bash
docker compose config
```

这能快速看出：哪些环境变量被覆盖、哪些服务最终存在。

---

## 3. 本项目启动流程（一步步）

### 3.1 前置条件

- PostgreSQL 已启动（宿主机或远程）
- Redis 已启动（宿主机或远程）
- `.env` 指向正确地址

### 3.2 启动命令

```bash
docker compose up -d
```

### 3.3 启动顺序

1. `prestart` 连接数据库 → 迁移 → 初始化
2. `backend` 启动服务
3. `worker` 启动后台任务

### 3.4 验证

```bash
curl http://localhost:8000/api/v1/utils/health-check/
```

返回 `true` 表示后端正常。

---

## 4. 本地开发（macOS）特别说明

### 4.1 文件同步

`docker compose watch` 会把 `./backend` 同步到容器 `/app`：

- 改代码自动同步
- 改依赖（pyproject）会触发重建

如果你 Compose 版本没有 `watch`，使用：

```bash
docker compose up -d
```

### 4.2 macOS 网络访问

容器访问宿主机服务必须用：

```
host.docker.internal
```

不要用 `localhost`，否则会指向容器自身。

---

## 5. 常用命令速查

```bash
# 启动全部服务
docker compose up -d

# 停止并删除容器
docker compose down

# 查看状态
docker compose ps

# 看日志
docker compose logs

# 只看后端日志
docker compose logs backend

# 进入容器
docker compose exec backend bash

# 重新构建镜像
docker compose build backend
```

---

## 6. 常见问题排查

### 6.1 数据库连接失败

现象：日志出现 `connection refused` / `could not connect`。

排查：
- `.env` 中是否写成了 `localhost`？
- 宿主机数据库是否监听了 TCP（不是只监听 127.0.0.1）？
- 端口是否正确？

### 6.2 端口冲突

现象：`port is already allocated`。

排查：
- `lsof -i :8000` 查看占用
- 修改 `docker-compose.override.yml` 的端口映射

### 6.3 watch 不生效

- 确认 Docker Compose 版本支持 `watch`
- 或退回到 `docker compose up -d` 手动重启

### 6.4 后端健康检查失败

- `docker compose logs backend` 查看具体错误
- 常见原因是数据库/Redis 配置错误

---

## 7. 进一步阅读

- `docs/development/docker.zh-CN.md`：本地开发流程
- `docs/deployment/docker.zh-CN.md`：部署流程
- `docs/deployment/docker-overview.zh-CN.md`：方案整体说明

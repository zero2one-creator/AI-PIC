# Docker 入门（本项目版 · 深入）

本教程面向 **从未用过 Docker 的 macOS 同学**，但会讲到比入门更深入的概念，并紧贴本项目的实际用法。

你会学到：
- Docker/Compose 的核心概念（镜像、层、容器、网络、卷、缓存、Registry、健康检查等）
- 本项目的服务结构与启动顺序
- 外部 PostgreSQL/Redis 的连接方式（macOS）
- 常见问题与排查方法

阅读提示：
- 文中命令默认使用 **Docker Compose v2**（也就是 `docker compose ...`）。如果你的机器上只有老版本 `docker-compose`（带短横线），建议升级 Docker Desktop。
- 本文会反复提到“构建（build）”和“运行（run）”是两件事：**构建产物是镜像，运行产物是容器**。

---

## 1. 本项目的 Docker 方案“全景图”

### 1.0 先把 3 个最容易混淆的名词分清楚

很多新同学卡在“我明明装了 Docker，为什么还要 Compose？”——建议用下面这张小图先建立心智模型：

- **Docker Desktop（macOS/Windows）**：一个“全家桶”，里面包含 Docker Engine、GUI、以及一些兼容层。你平时点开 Docker 图标、开关设置，指的就是它。
- **Docker Engine / Docker Daemon**：真正负责“拉镜像、建容器、建网络”的后台服务。你运行 `docker ps` 时，其实是在和它通信。
- **Docker Compose**：用一份 `docker-compose*.yml` 把“多个服务怎么一起跑”描述清楚，然后一条命令起一整套（backend/worker/proxy...）。

在本项目里：
- “build”阶段主要看 `backend/Dockerfile`（怎么做出后端镜像）
- “up”阶段主要看 `docker-compose.yml` 和 `docker-compose.override.yml`（怎么把镜像跑成多个容器并连起来）

### 1.1 关键文件

- `docker-compose.yml`：核心服务（后端、worker、adminer、prestart）
- `docker-compose.override.yml`：本地开发增强（proxy、mailcatcher、热更新）
- `docker-compose.traefik.yml`：公共 Traefik（线上 HTTPS 入口）
- `backend/Dockerfile`：后端镜像构建定义
- `.env`：运行时配置（数据库/Redis/密钥等）

补充说明（新手非常常见的疑问）：
- `docker-compose.yml` 是“基础版”，更贴近线上/部署形态：不直接暴露端口，更多通过 Traefik 的 label 来路由。
- `docker-compose.override.yml` 是“本地开发增强”：默认会自动合并进来（如果你在项目根目录直接运行 `docker compose up`）。
  - 它会额外加一个本地 Traefik（服务名 `proxy`），并把常用端口映射到宿主机（比如 `8000:8000`）。
  - 它还启用 `docker compose watch` 的文件同步规则，让你改代码不用手动重建镜像。
- `docker-compose.traefik.yml` 一般用于“单独起一个公共 Traefik”（常见于生产/服务器上），让多个项目共享同一个 HTTPS 入口。

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

补充解释（把服务当作“进程角色”理解）：
- `backend`：FastAPI API 服务（对外提供 HTTP 接口）。
- `worker`：后台任务进程（复用同一份后端镜像，但运行的是另一个命令）。
- `prestart`：一次性的“前置任务容器”（很像 Kubernetes 的 init container）：
  - 等外部 PostgreSQL 可用（带重试）
  - 跑 Alembic 迁移
  - 初始化一些数据
- `adminer`：数据库管理 UI（可选）。
- `proxy`：仅本地启用的 Traefik（反向代理 + 子域名路由 + 本地 dashboard）。
- `mailcatcher`：仅本地启用的“邮件捕获器”（开发环境发出的邮件会被它接住，你在 Web UI 里看）。

---

## 2. Docker 概念深入（结合本项目）

### 2.1 镜像（Image）= 可运行的软件快照

镜像是“打包好的软件环境 + 可执行程序”。
更准确一点：镜像本质上是一组 **只读的文件系统层（layers）** + 一些元数据（默认工作目录、默认启动命令、环境变量等）。
你可以把它理解成“一个可复制、可分发、可复现的运行环境模板”。

几个非常关键的直觉：
- 镜像是 **不可变（immutable）** 的：你在运行中的容器里 `apt install ...`、`pip install ...`，并不会“改回镜像”；容器删了就没了（除非你把变更做成新镜像）。
- 镜像通常来自仓库（Registry）：例如 `public.ecr.aws/...`、`docker.io/...`。第一次构建/运行时如果本地没有，会自动拉取。

本项目的后端镜像由 `backend/Dockerfile` 构建：

- 基础镜像：`public.ecr.aws/docker/library/python:3.10`
- 依赖安装：使用 `uv`（会利用缓存加速）
- 最终镜像名由 Compose 决定：在 `docker-compose.yml` 里是：

```yaml
image: '${DOCKER_IMAGE_BACKEND?Variable not set}:${TAG-latest}'
```

也就是说：
- `.env` 里 `DOCKER_IMAGE_BACKEND=backend` 时，镜像仓库名就是 `backend`
- `TAG` 没设置时默认 `latest`，所以最终就是 `backend:latest`
- 部署时通常会设置 `TAG=某个版本号`，让镜像版本可追溯、可回滚

**镜像标签（tag）**
- `backend:latest` 是一个标签，不是固定版本
- 生产环境会用明确版本号（如 `backend:2025.01.28`）

**镜像来自哪里（Registry）**
- `public.ecr.aws`：AWS 的公共镜像仓库
- `docker.io`：Docker Hub（默认）

常用查看命令（不用记全，知道有这些就行）：

```bash
# 查看本机有哪些镜像
docker images

# 只看某个镜像的详细信息（包括 ENV / CMD 等元数据）
docker image inspect backend:latest

# 看镜像每一层是怎么来的（有助于理解 Dockerfile 缓存）
docker history backend:latest
```

---

### 2.2 层（Layer）与构建缓存

镜像是由多层组成的，每一层对应 Dockerfile 的一条指令。

好处：
- 当某层没有变化时，Docker 会复用缓存，不重新构建
- 依赖安装和代码复制分开，构建更快

本项目里：
- 改 `pyproject.toml` 会触发依赖层重建
- 只改代码（`./app`）会复用依赖层

再补 3 个新手常见“为什么这么写”的点：

1) **构建上下文（build context）会影响构建速度**  
`docker compose build` 会把 `build.context` 指定目录（本项目是 `./backend`）里的文件发给构建器。
因此 `backend/.dockerignore` 非常重要：它会把 `.venv/`、`__pycache__/`、`htmlcov/` 等排除掉，否则每次构建都要“打包上传一大坨文件”。

2) **BuildKit 才支持 `RUN --mount=...` 的高级缓存**  
本项目的 `backend/Dockerfile` 里有：
- `--mount=type=cache,target=/root/.cache/uv`：让 `uv` 的下载/编译缓存跨构建复用（缓存不进入最终镜像）
- `--mount=type=bind,source=uv.lock,...`：把 lockfile 当作“构建输入”，配合缓存机制让依赖层只在 lockfile 变化时失效

3) **Dockerfile 的指令顺序就是“缓存命中策略”**  
你会看到它先只“喂”构建器 `pyproject.toml/uv.lock` 去装依赖，再 COPY 源码。
这样做的效果是：你只改业务代码时，不会每次都重新装一遍依赖。

常用命令：

```bash
# 使用缓存构建（默认）
docker compose build backend

# 不使用缓存
docker compose build --no-cache backend
```

想看更详细的构建过程（排查缓存是否命中时很有用）：

```bash
docker compose build --progress=plain backend
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

更贴近真实的理解：
- 容器≈“一个进程 + 一层可写的临时文件系统（copy-on-write）+ 独立的网络/hostname”
- 容器里一般有一个“主进程”（PID 1）。主进程退出，容器就结束。
  - 这就是为什么 `prestart` 会“跑完就退出”：它就是设计成一次性任务容器。

**容器生命周期**
- `docker compose up -d` 启动容器
- `docker compose stop` 停止但不删除
- `docker compose down` 停止并删除容器/网络

补充：`restart` 重启策略  
在 `docker-compose.yml`（基础版）里，`backend/worker/adminer` 都是 `restart: always`，意思是：
- 容器进程退出时会自动重启（提高可用性）
- Docker 守护进程重启后，也会把这些容器拉起来

而在 `docker-compose.override.yml`（本地开发）里，把 `backend/adminer` 的 restart 改成了 `"no"`，避免你本地开发时“死循环重启”把日志刷爆、也更方便你观察报错原因。

你会经常用到的 3 个动作：

```bash
# 看当前服务状态（有没有起来、端口有没有暴露、健不健康）
docker compose ps

# 看某个服务日志（排查 80% 问题都靠它）
docker compose logs backend

# 进到容器里执行命令（排查“容器里实际看到的环境”）
docker compose exec backend bash
```

---

### 2.4 网络（Network）与容器 DNS

Docker 会给每个 Compose 项目建一个默认网络（`default`）。
容器之间可以用 **服务名当作 DNS**。

本项目：
- `default` 网络用于容器之间通信
- `traefik-public` 用于 Traefik 路由（线上是 external，本地 override 设置为 internal）
- 如果数据库/redis 在容器里，`POSTGRES_SERVER=db` 就能访问
- 但现在 **数据库是外部的**，所以要改成 `host.docker.internal`

把访问方向分开想，会清晰很多：

- **容器 → 容器**：走 Docker 网络，用“服务名 + 容器端口”访问（不需要 `ports:`）。
  - 例：如果另一个容器要访问后端，一般是 `http://backend:8000`（不是 `localhost:8000`）。
- **宿主机 → 容器**：必须靠 `ports:` 把容器端口映射出来（本项目在 override 里做了）。
- **容器 → 宿主机**：macOS/Windows 通常用 `host.docker.internal`（本项目就是这种情况）。

macOS 下连接宿主机服务：

```dotenv
POSTGRES_SERVER=host.docker.internal
REDIS_HOST=host.docker.internal
```

如果你在 Linux 上，用宿主机 IP。

常用排查命令：

```bash
# 看有哪些网络
docker network ls

# 查看某个网络里有哪些容器、它们的 IP/别名
docker network inspect <network-name>
```

---

### 2.5 端口映射（Ports）

容器内的服务默认不能被宿主机访问，需要映射端口。
本项目常用端口：

- 后端 API → `http://localhost:8000`
- Adminer → `http://localhost:8080`
- Traefik UI（本地）→ `http://localhost:8090`
- MailCatcher → `http://localhost:1080`

若端口冲突，可改 `docker-compose.override.yml`。

补充解释：`ports:` 做的事情是把“容器端口”发布到“宿主机端口”。

```yaml
ports:
  - "8000:8000" # 宿主机 8000 -> 容器 8000
```

几个要点：
- 只在本地开发/调试时才需要大量 `ports:`。生产环境很多时候通过反向代理（这里是 Traefik）对外暴露，不一定直接映射端口。
- `docker-compose.yml`（基础版）里 **backend/adminer 没有 ports**，所以如果你只跑基础版，`http://localhost:8000` 可能访问不到（需要走 Traefik 或加 override）。

---

### 2.6 环境变量（.env）加载规则

Compose 会读取 `.env`，并注入到容器中：

- `env_file: .env`：整体注入
- `environment:`：追加或覆盖

这里新手最容易混淆的是：**同一个 `.env` 在 Compose 里常常扮演两种角色**：

1) **给 Compose 做变量替换（interpolation）**  
比如 `docker-compose.yml` 里写了 `${DOMAIN?Variable not set}`，Compose 会从“当前 shell 环境变量 + 项目根目录 `.env`”里找 `DOMAIN`，找不到就报错。

2) **作为容器运行时环境变量（env_file）**  
本项目很多服务都有：

```yaml
env_file:
  - .env
```

它的效果是：把 `.env` 的键值对塞进容器里（容器里的应用通过 `os.environ` 读到）。

常见优先级（够用版）：
- 对容器来说：`environment:`（显式写在 compose 里的） > `env_file:` > 镜像里 `ENV ...` 的默认值
- 对 Compose 替换来说：shell 环境变量 > `.env` > `${VAR-default}` 的默认值

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

建议你用下面命令“把最终结果打印出来”来排障（尤其是变量覆盖/合并问题）：

```bash
docker compose config
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

把它和项目文件对上会更好理解：
- `prestart` 实际跑的是 `backend/scripts/prestart.sh`：先等 DB 可用，再迁移，再初始化数据
- 等 DB 的重试逻辑在 `backend/app/backend_pre_start.py`（用了 tenacity，每秒重试，最长 5 分钟）

关于 healthcheck 的一个常见误区：
- healthcheck 只是“状态探针”，不会自动帮你重启容器（除非你的主进程自己退出触发 restart policy）
- 看到 `unhealthy` 时，第一反应还是去看日志：`docker compose logs backend`

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

再补一个你在部署时会遇到的 Volume：  
`docker-compose.traefik.yml` 里有 `traefik-public-certificates`，用来持久化 Let's Encrypt 的证书文件（否则 Traefik 重建一次证书就没了）。

清理提示：
- `docker compose down` 默认**不会删除**命名 volume
- `docker compose down -v` 才会把命名 volume 一起删掉（注意这通常是“危险操作”）

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

建议你用“从上到下读一遍”的方式理解本项目 Dockerfile（它其实在做这些事）：

1) 选一份 Python 基础镜像：`FROM public.ecr.aws/docker/library/python:3.10`
2) 把 `uv` 这个可执行文件从另一个镜像里拷进来：`COPY --from=ghcr.io/astral-sh/uv:...`  
   这叫 **多阶段构建（multi-stage build）**：可以只拿到你需要的产物（uv 二进制），而不是把整套构建环境带进最终镜像。
3) 利用 BuildKit 的缓存 mount 加速依赖安装：`RUN --mount=type=cache,... uv sync ...`
4) 先 COPY 锁文件/配置，再 COPY 源码：这是为了“只改代码不重装依赖”的缓存策略
5) 最后用 `CMD` 声明默认启动命令（真正运行时依然可以被 Compose 覆写）

如果你发现“明明只改了代码却一直在重装依赖”，优先检查两件事：
- 你改动的文件是否影响到了 `pyproject.toml/uv.lock` 这类“依赖输入”
- `backend/.dockerignore` 是否把本地虚拟环境/缓存排除干净（否则 build context 一变就可能触发缓存失效）

---

### 2.10 启动命令与 command/entrypoint

容器“启动时运行什么”由 Dockerfile 的 `CMD` 和 Compose 的 `command` 共同决定：

- `prestart` 显式指定 `command: bash scripts/prestart.sh`
- `worker` 指定 `command: ["python", "worker/emoji_worker.py"]`
- `backend` 没有覆写 command，所以使用 Dockerfile 的 `CMD`

这意味着同一个镜像可以用不同命令启动多个服务（backend / worker）。

再补一层（新手够用版）：
- `CMD`：默认参数/命令（最常被 override）
- `ENTRYPOINT`：把镜像“固定成某个程序入口”（本项目没用到，但很多镜像会用）
- 在 Compose 里：
  - `command:` 会覆盖 Dockerfile 的 `CMD`
  - `entrypoint:` 会覆盖 Dockerfile 的 `ENTRYPOINT`

调试技巧：想临时“进容器看看”但又不想改 compose 文件时，可以：

```bash
docker compose run --rm --entrypoint bash backend
```

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

合并规则里最重要的一个点：**后面的文件会覆盖前面的同名字段**，但“覆盖方式”取决于字段类型。
举例（来自本项目的真实效果）：
- `backend.command`：在 override 里会完全替换基础版的启动命令（本地用 `--reload`，生产用 `--workers 4`）。
- `backend.ports`：基础版没有，override 里新增（本地才能 `localhost:8000` 访问）。
- `backend.environment`：会按 key 合并/覆盖（同名变量以 override 为准）。

---

### 2.12 Compose 项目名与容器命名

Compose 会用“目录名”作为项目名。当前目录名为 `AI-PIC`，实际容器名会变成：

- `ai-pic-backend-1`
- `ai-pic-worker-1`

如果想自定义项目名，可以使用：

```bash
COMPOSE_PROJECT_NAME=myproject docker compose up -d
```

项目名还会影响：
- 默认网络名：通常是 `<project>_default`
- Compose 创建的其他资源名（network/volume 等）也通常会带上 `<project>_` 前缀

如果你同时跑两套同样的服务（比如你开了两个终端在不同目录），项目名不同就不会互相抢容器名/网络名。

---

### 2.13 查看最终配置（排查时很有用）

Compose 会把多个文件合并成最终配置，你可以用下面的命令查看：

```bash
docker compose config
```

这能快速看出：哪些环境变量被覆盖、哪些服务最终存在。

另外两个经常用到的小技巧：

```bash
# 列出最终有哪些服务
docker compose config --services

# 只看最终有哪些 volume（如果你想确认 down -v 会删哪些）
docker compose config --volumes
```

---

### 2.14 Traefik 与 Docker Labels（本项目的反向代理是怎么工作的）

你会在 `docker-compose.yml` 里看到大量类似下面的 label：
- `traefik.enable=true`
- `traefik.http.routers....rule=Host(\`api.${DOMAIN}\`)`
- `traefik.http.services....loadbalancer.server.port=8000`

这背后的概念是：
- **Traefik 是反向代理**：它监听宿主机的 80/443 端口，把请求按规则转发到后端容器（`backend`）或其他服务（`adminer`）。
- **Traefik “读 Docker”**：本项目把 `/var/run/docker.sock` 挂到 Traefik 容器里，让 Traefik 能通过 Docker API 看到有哪些容器、以及它们的 labels（也就是“动态配置”）。
- **labels 就是“把路由规则写在容器上”**：Compose 启动容器时会把 labels 写进 Docker 元数据，Traefik 读取后就知道：
  - 哪些容器要对外暴露（`traefik.enable=true`）
  - 用什么域名匹配（`rule=Host(...)`）
  - 转发到容器的哪个端口（`loadbalancer.server.port=8000`）
  - http/https 入口、TLS、跳转等（routers / entrypoints / middlewares）

本项目把 Traefik 拆成两种运行方式：
- **本地开发**：`docker-compose.override.yml` 里额外起一个 `proxy`（Traefik），暴露端口 `80:80` 和本地面板 `8090:8080`。你既可以用端口直连（`localhost:8000`），也可以用子域名方式（需要把 `.env` 里的 `DOMAIN` 改成 `localhost.tiangolo.com`，详见 `docs/development/docker.zh-CN.md`）。
- **生产/服务器**：通常单独跑 `docker-compose.traefik.yml` 作为“公共 Traefik”，并创建共享网络 `traefik-public`。项目栈（`docker-compose.yml`）里的服务加入同一个外部网络，Traefik 才能把请求转发过去。

排查 Traefik 路由问题时常用：

```bash
docker compose logs proxy
```

以及打开本地 Traefik 面板（override 默认映射到）：`http://localhost:8090`。

## 3. 本项目启动流程（一步步）

### 3.1 前置条件

- Docker Desktop 已启动（macOS 菜单栏小鲸鱼是运行状态）
- PostgreSQL 已启动（宿主机或远程）
- Redis 已启动（宿主机或远程）
- `.env` 指向正确地址

### 3.2 启动命令

```bash
docker compose up -d
```

第一次运行（或你刚改了依赖/想确保镜像是最新）建议：

```bash
docker compose up -d --build
```

### 3.3 启动顺序

1. `prestart` 连接数据库 → 迁移 → 初始化
2. `backend` 启动服务
3. `worker` 启动后台任务

如何判断卡在哪一步：

```bash
docker compose ps
docker compose logs prestart
```

你通常会看到 `prestart` 这个容器 **Exited (0)** ——这在本项目里是“正常现象”，表示它成功完成了前置任务。
如果它是 **Exited (非 0)**，后端/worker 就不会启动，应该优先看 `prestart` 的日志错误。

### 3.4 验证

```bash
curl http://localhost:8000/api/v1/utils/health-check/
```

返回 `true` 表示后端正常。

也可以顺手打开：
- Swagger UI：`http://localhost:8000/docs`
- 看健康状态：`docker compose ps`（backend 一般会显示 `healthy`）

---

## 4. 本地开发（macOS）特别说明

### 4.1 文件同步

`docker compose watch` 会把 `./backend` 同步到容器 `/app`：

- 改代码自动同步
- 改依赖（pyproject）会触发重建

结合 `docker-compose.override.yml` 里的：

```yaml
develop:
  watch:
    - path: ./backend
      action: sync
      target: /app
    - path: ./backend/pyproject.toml
      action: rebuild
```

解释一下它在本项目里的“工作方式”：
- 你运行 `docker compose watch` 后，Compose 会在后台起容器，并持续监听文件变化（一般需要你把这个命令挂在一个终端里）。
- 当你改 `./backend/app/...` 代码时：变更会被同步进容器 `/app/...`，配合 `fastapi run --reload` 自动重载。
- 当你改 `pyproject.toml` 时：Compose 会触发“重建镜像 + 重新创建容器”，因为依赖变了只同步代码不够。

如果你 Compose 版本没有 `watch`，使用：

```bash
docker compose up -d
```

这时你需要自己意识到一件事：**没有 watch（也没有 bind mount）就不会自动把你本机改的代码同步到容器里**。  
所以你可能需要手动：

```bash
docker compose restart backend
```

或者在改依赖后重建：

```bash
docker compose up -d --build
```

### 4.2 macOS 网络访问

容器访问宿主机服务必须用：

```
host.docker.internal
```

不要用 `localhost`，否则会指向容器自身。

一个更“形象”的记法：
- 你在浏览器里访问 `http://localhost:8000`：这是 **宿主机 → 容器**（靠 `ports:`）
- 你在容器里访问数据库时写 `localhost:5432`：这是 **容器 → 容器自己**（通常会错）
- 所以本项目 `.env` 才会用 `host.docker.internal`：这是 **容器 → 宿主机**

---

## 5. 常用命令速查

```bash
# 启动全部服务
docker compose up -d

# 构建 + 启动（常用）
docker compose up -d --build

# 停止并删除容器
docker compose down

# 停止并删除容器 + volume（危险，可能丢数据）
docker compose down -v

# 查看状态
docker compose ps

# 看日志
docker compose logs

# 跟随日志（实时滚动）
docker compose logs -f

# 只看后端日志
docker compose logs backend

# 进入容器
docker compose exec backend bash

# 临时跑一次命令（用完即删容器）
docker compose run --rm backend python -V

# 重新构建镜像
docker compose build backend

# 查看合并后的最终配置（变量/覆盖/服务是否存在）
docker compose config
```

---

## 6. 常见问题排查

### 6.1 数据库连接失败

现象：日志出现 `connection refused` / `could not connect`。

排查：
- `.env` 中是否写成了 `localhost`？
- 宿主机数据库是否监听了 TCP（不是只监听 127.0.0.1）？
- 端口是否正确？

补充：本项目的第一道“守门员”是 `prestart`，所以数据库连不上时最先失败的往往是 `prestart`：

```bash
docker compose logs prestart
```

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

### 6.5 启动时报 `Variable not set`

现象：`docker compose up` 直接报错，类似：
- `${STACK_NAME?Variable not set}`
- `${SECRET_KEY?Variable not set}`

原因：`docker-compose.yml` 用了 `${VAR?Variable not set}` 这种写法来强制要求变量存在。  
排查顺序：
- 先确认项目根目录 `.env` 存在且变量齐全
- 再确认你不是在“错误的目录”执行 `docker compose ...`（必须在仓库根目录）

### 6.6 `traefik-public` 网络找不到（多见于只跑基础版）

现象：你用 `docker compose -f docker-compose.yml up -d` 启动时报错 network not found。  
原因：基础版把 `traefik-public` 声明为 `external: true`，意思是“这个网络由外部（通常是公共 Traefik 栈）创建并维护”。  
解决方式（任选一种）：

```bash
# 方式 1：手动创建一次共享网络
docker network create traefik-public

# 方式 2：先把公共 Traefik 跑起来（见 docker-compose.traefik.yml）
```

本地开发一般不会遇到这个问题，因为 `docker-compose.override.yml` 把它改成了 `external: false`（由当前项目自行创建）。

### 6.7 磁盘占用越来越大/构建越来越慢

Docker 的镜像层和构建缓存会吃磁盘（尤其是你经常 `--build`、经常换分支）。可以用：

```bash
docker system df
```

如果确认要清理（会删除未使用的镜像/缓存/容器），再考虑：

```bash
docker system prune
```

---

## 7. 进一步阅读

- `docs/development/docker.zh-CN.md`：本地开发流程
- `docs/development/docker-buildkit.zh-CN.md`：BuildKit 与构建缓存（为什么 `RUN --mount` 能加速）
- `docs/deployment/docker.zh-CN.md`：部署流程
- `docs/deployment/docker-overview.zh-CN.md`：方案整体说明

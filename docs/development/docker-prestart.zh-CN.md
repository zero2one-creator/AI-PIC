# prestart 详解（本项目版）

本文专门解释本项目里的 `prestart`：它是什么、启动时做了哪些事、为什么要单独拆成一个服务，以及常见失败场景怎么排查。

先说结论：**`prestart` 是一个“一次性前置任务容器”**（类似 Kubernetes 的 init container）。它在后端服务启动前完成“外部依赖就绪检查 + 数据库迁移 + 初始化数据”，成功后退出；失败时阻止 `backend/worker` 启动。

---

## 1. `prestart` 在哪里定义？和 `backend` 是什么关系？

`prestart` 是一个 Compose service，定义在仓库根目录 `docker-compose.yml`。

关键点：
- **它复用和 `backend/worker` 一样的镜像**（同一个 `backend/Dockerfile` 构建出来的镜像）
- 但 **运行的命令不一样**：`prestart` 跑的是 `bash scripts/prestart.sh`
- `backend`/`worker` 通过 `depends_on` 等待它成功

你可以把它理解成：同一个“安装包（镜像）”，分别跑成三个“进程角色（容器）”：
- `prestart`：前置任务（一次性）
- `backend`：API 服务（常驻）
- `worker`：后台任务（常驻）

### 1.1 Compose 里的关键配置点（够用版）

在 `docker-compose.yml` 里：
- `prestart.command: bash scripts/prestart.sh`
- `backend.depends_on.prestart.condition: service_completed_successfully`
- `worker.depends_on.prestart.condition: service_completed_successfully`

这意味着：
- `prestart` 必须 **以退出码 0 成功退出**
- 否则 `backend/worker` 会被 Compose 阻止启动（或者启动后马上失败，取决于你怎么操作）

---

## 2. `prestart` 具体做了什么？（按执行顺序）

`prestart` 实际执行的脚本是：`backend/scripts/prestart.sh`。

内容很短，但每一行都很关键：

1) `set -e`：任意一步报错（返回非 0）就立刻退出整个脚本  
2) `set -x`：把执行的命令打印到日志里（方便排查）
3) `python app/backend_pre_start.py`：等待数据库就绪（带重试）
4) `alembic upgrade head`：把数据库结构迁移到最新版本（真正改表结构）
5) `python app/initial_data.py`：初始化数据（seed data，当前版本基本是占位）

你看到的现象通常是：
- `prestart` 容器运行一小会儿，然后变成 `Exited (0)`
- 这是“正常现象”，表示前置任务完成

---

## 3. 第一步：等待数据库就绪（`backend_pre_start.py`）

对应文件：`backend/app/backend_pre_start.py`

它的目标不是“做迁移”，而是解决一个很现实的问题：
- 在容器启动时，外部 PostgreSQL 可能还没准备好（或你本机刚启动数据库）
- 如果应用/迁移一上来就连数据库，容易直接失败
- 所以要做“带重试的探活”

### 3.1 它怎么判断“数据库好了”？

代码核心逻辑是：
- 从 `app.core.db` 导入 `engine`（SQLAlchemy/SQLModel 的引擎）
- 每次重试创建一个 Session
- 执行一个最简单的查询：`select(1)`
  - 如果能成功执行，基本可以认为数据库已经可连接、可响应查询

### 3.2 重试策略（为什么说“最多等 5 分钟”）

它使用了 `tenacity` 重试库：
- `wait_fixed(1)`：每次失败等 1 秒
- `stop_after_attempt(60 * 5)`：最多尝试 300 次（约 5 分钟）
- 会在重试前/后打日志，方便你看到“还在等 DB”

所以当你看到 `prestart` 一直没退出时，很多时候不是“卡住”，而是在等数据库可用。

### 3.3 依赖什么配置才能连上 DB？

数据库地址来自 `.env`，最终在容器里会变成应用的运行时环境变量（通过 Compose 的 `env_file: .env` 注入）。

本项目本地开发常见写法是：
- `POSTGRES_SERVER=host.docker.internal`（容器访问宿主机 PostgreSQL）
- 以及 `POSTGRES_PORT/POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD`

如果你把 `POSTGRES_SERVER` 写成 `localhost`，在容器里通常会连到“容器自己”，导致连接失败。

---

## 4. 第二步：数据库迁移（`alembic upgrade head`）

对应命令：`alembic upgrade head`（在 `backend/scripts/prestart.sh` 里）

它做的事是：
- 扫描项目里的 Alembic migration（迁移脚本）
- 把数据库 schema 从当前版本升级到最新（`head`）

常见误区：
- 迁移不是“生成迁移文件”，而是“应用迁移”
  - 生成迁移通常是你开发时手动跑：`alembic revision --autogenerate ...`
- 迁移是会“真的改数据库”的：加表、改列、建索引等

为什么放在 `prestart` 里？
- 保证 `backend/worker` 启动时数据库结构已经是“符合当前代码预期”的
- 否则很容易出现：代码已经用到新字段，但 DB 还没迁移，启动/运行就报错

---

## 5. 第三步：初始化数据（`initial_data.py` / `init_db`）

对应文件：
- `backend/app/initial_data.py`
- `backend/app/core/db.py` 里的 `init_db(session)`

当前版本的实现特点：
- `initial_data.py` 会创建一个 DB Session 并调用 `init_db(session)`
- `init_db` 目前基本是占位（V1.0 不需要 seed data）

也就是说：
- 这个步骤目前大概率什么都不做，但它预留了一个“未来要加初始化逻辑”的入口

如果你未来要加“默认管理员账号/默认配置”等 seed data，通常会放在这里做，并且要注意：
- 尽量写成**幂等**（重复执行不会重复插数据/不会破坏已有数据）
  - 因为 `prestart` 在某些场景下可能会被你手动重跑

---

## 6. 什么时候 `prestart` 会执行？会不会每次都执行？

`prestart` 是一个独立的 service：
- 当你执行 `docker compose up` 时，如果 Compose 需要创建/启动它，它就会跑一遍脚本
- 跑完成功后容器退出（`Exited (0)`）

几个常见情况（理解行为很重要）：
- 你第一次 `docker compose up -d`：会创建并运行 `prestart`，成功后再启动 `backend/worker`
- 你只 `docker compose restart backend`：通常不会重新跑 `prestart`（你只是重启了 backend）
- 你 `docker compose down` 再 `up`：会重新创建容器，因此 `prestart` 会再跑一遍

所以：把 `prestart` 当作“初始化/迁移的入口”是合理的，但不要指望它在你“只重启 backend”时自动再跑一次。

---

## 7. 排查与常用操作（非常实用）

### 7.1 最常用：看 `prestart` 日志

```bash
docker compose logs prestart
```

你要找的通常是三类信息：
- “正在重试连接 DB” → 多半是 DB 没起来或地址写错
- Alembic 报错 → 多半是迁移脚本问题或权限问题
- Python 初始化报错 → 多半是配置缺失（环境变量/密钥等）

### 7.2 看启动顺序是否卡在 `prestart`

```bash
docker compose ps
```

典型现象：
- `prestart` 一直 `running`：多半在等 DB
- `prestart` `Exited (非 0)`：后端/worker 起不来，优先查 `docker compose logs prestart`

### 7.3 手动重跑一次 `prestart`（用于“迁移/初始化想再来一遍”）

```bash
docker compose run --rm prestart
```

说明：
- `--rm` 会在命令结束后删除这个临时容器，避免一堆一次性容器堆着
- 这会再次执行 `scripts/prestart.sh`（等待 DB、迁移、初始化）

### 7.4 进到 `prestart` 的环境里调试（不自动跑脚本）

```bash
docker compose run --rm --entrypoint bash prestart
```

然后你可以在里面手动执行：
- `python app/backend_pre_start.py`
- `alembic upgrade head`
- `python app/initial_data.py`

---

## 8. 常见失败场景（对号入座）

### 8.1 一直在重试 DB / `connection refused`

优先检查：
- `.env` 里 `POSTGRES_SERVER` 是否是 `host.docker.internal`（macOS）
- 宿主机 Postgres 是否真的在监听 `5432`（不是只监听 `127.0.0.1`）
- 账号密码是否正确（权限不足也会表现为“连不上/认证失败”）

### 8.2 Alembic 迁移报错

常见原因：
- 迁移脚本本身有 bug（语法、依赖、执行顺序）
- 数据库权限不足（无法建表/改表/建索引）
- 数据库里已经有不一致的状态（例如手工改过表结构）

排查步骤：
1) `docker compose logs prestart` 看具体报错栈
2) 进容器手动跑 `alembic upgrade head` 看更直观的输出

### 8.3 `initial_data` 重复执行导致重复数据（未来可能会遇到）

如果你未来在 `init_db` 里加了 seed data，强烈建议：
- 按唯一键/业务键查询后再插入（“有则跳过”）
- 或使用 upsert（需要你选定策略）

这样你才能放心重跑 `prestart`，也不会破坏已有数据。


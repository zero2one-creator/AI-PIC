# BuildKit 入门（本项目版 · 够用就好）

本文面向 Docker 初学者，目标是让你看懂本项目 `backend/Dockerfile` 里那些“像魔法一样”的构建写法（尤其是 `RUN --mount=...`），并知道遇到构建慢/缓存失效/报错时怎么排查。

你会学到：
- BuildKit 是什么、解决了什么问题
- 为什么 `RUN --mount=type=cache|bind` 能明显加速构建
- 本项目 `backend/Dockerfile` 的 BuildKit 用法逐点解释
- 常用命令与常见报错排查

---

## 1. BuildKit 是什么？

一句话：**BuildKit 是 Docker 的镜像构建引擎（builder backend）**。

更具体一点：
- 你写的 `Dockerfile` 只是“构建配方”
- 执行 `docker build` / `docker compose build` 时，真正负责“解析 Dockerfile、安排构建步骤、算缓存、执行命令、产出镜像”的，就是构建引擎
- BuildKit 是新一代构建引擎，相比旧的 legacy builder，通常有更好的：
  - 缓存能力（可复用、粒度更细）
  - 并行与性能（构建更快）
  - 进度输出（更清楚每一步在干什么）
  - Dockerfile 新特性（例如 `RUN --mount=...`）

你在本项目里“感知到 BuildKit”的最直接信号就是：`backend/Dockerfile` 用到了 `RUN --mount=...`，这是 BuildKit 才支持的能力。

---

## 2. BuildKit 和“层缓存”是什么关系？

很多新手只知道“Docker 会缓存 layer”，但 BuildKit 让缓存更强/更可控。

先复习一个基础：
- `Dockerfile` 每条指令（如 `COPY`/`RUN`）通常会生成一层（layer）
- 当某一层的“输入”没变时，Docker 会复用这层，不重新执行

BuildKit 在此基础上额外提供了“构建时挂载（mount）”：
- `type=cache`：给某个构建步骤一块**可复用的缓存目录**（不进最终镜像）
- `type=bind`：把某些文件**临时绑定**进构建步骤（不 COPY 进镜像层），让“依赖层”的缓存更稳定
- `type=secret` / `type=ssh`：在构建时临时提供敏感信息或 SSH（本项目目前没用到）

这类 mount 的关键点是：**它们是“构建过程的辅助输入”，不是镜像内容**。所以它们能加速、能让缓存更聪明，但不会把缓存垃圾带到最终镜像里。

---

## 3. 本项目里 BuildKit 具体用在哪？

打开 `backend/Dockerfile`，你会看到两段关键的 `RUN --mount`：

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync
```

下面把每个点拆开解释（建议对着 Dockerfile 看）：

### 3.1 `--mount=type=cache,target=/root/.cache/uv`：让依赖下载/编译缓存跨构建复用

`uv` 会在缓存目录里存下载的包、构建产物等。
如果你每次构建都从零开始下载/编译，构建会非常慢。

`type=cache` 做的事情就是：
- 在构建器侧创建一个可复用的缓存目录
- 每次执行到这条 `RUN` 时，把它挂到容器的 `/root/.cache/uv`
- 下次构建遇到同样的步骤，缓存还在，速度就会快很多

注意：这个缓存**不在镜像里**，所以不会让最终镜像变大，但会占用本机 Docker 的构建缓存空间（见第 5 节清理）。

### 3.2 `--mount=type=bind,source=uv.lock/...`：把“依赖输入”绑定进构建步骤，稳定缓存命中

这两行：

```dockerfile
--mount=type=bind,source=uv.lock,target=uv.lock
--mount=type=bind,source=pyproject.toml,target=pyproject.toml
```

含义是：在执行 `uv sync ...` 这一步时，构建器临时把 `uv.lock` 和 `pyproject.toml` 绑定进来，让这一步“看得到”它们。

为什么不直接 `COPY uv.lock pyproject.toml ...` 再 `RUN uv sync`？
- 可以，但这样会更容易让“依赖安装层”的缓存被无关文件变化影响（尤其当你 COPY 的东西多时）
- `type=bind` 的设计思路是：**把这一步的输入限制得很干净**：只和依赖描述文件相关
- 于是你改业务代码（`./app`）时，依赖层更可能直接命中缓存，不必重装依赖

### 3.3 为什么有两次 `uv sync`？

第一段：

```dockerfile
uv sync --frozen --no-install-project
```

你可以把它理解为“只装依赖，不装项目本身”：
- `--frozen`：严格按 lockfile（`uv.lock`）来，避免“构建时偷偷变了依赖版本”
- `--no-install-project`：不把项目以可编辑/包的方式安装进环境（减少因为源码变化导致的缓存失效）

第二段（在 COPY 代码之后）：

```dockerfile
uv sync
```

这一步才把项目和最终运行所需的环境补齐。

这两步的整体目的就是：**最大化“只改业务代码时的缓存命中”**。

---

## 4. 我怎么知道现在是不是在用 BuildKit？

大多数情况下（尤其是 Docker Desktop 较新的版本），BuildKit 通常是默认启用的；但如果你遇到 `RUN --mount` 报错，就需要先确认 BuildKit 是否启用。

你可以用这些方式检查/确认：

```bash
# 查看 buildx（BuildKit 的入口/包装）是否可用
docker buildx version

# 构建时输出更详细的步骤（便于看缓存命中）
docker compose build --progress=plain backend
```

如果你怀疑 BuildKit 没启用，可以临时显式开启（对单次命令生效）：

```bash
DOCKER_BUILDKIT=1 docker compose build backend
```

（如果你用的是 `docker build` 也是一样的写法。）

---

## 5. 缓存在哪里？会不会越用越占磁盘？怎么清？

会的。BuildKit 的缓存是“用磁盘换时间”：
- 构建速度更快
- 但缓存会占用 Docker 的存储空间（尤其是依赖多、分支切换频繁时）

常用查看命令：

```bash
docker system df
```

清理构建缓存（谨慎，会让下次构建变慢）：

```bash
docker builder prune
```

如果你只是想“重来一次”，也可以用：

```bash
docker compose build --no-cache backend
```

区别：
- `--no-cache`：不使用缓存来构建这次镜像（缓存本身不一定会被删）
- `docker builder prune`：直接删构建缓存（影响所有项目的构建速度）

---

## 6. 常见报错与排查

### 6.1 `RUN --mount=...` 报错 / 不认识 `--mount`

常见原因：
- BuildKit 没启用
- Docker/Compose 版本过旧，Dockerfile frontend 不支持该语法

排查/解决（从简单到彻底）：
1) 先试试显式启用 BuildKit：

```bash
DOCKER_BUILDKIT=1 docker compose build backend
```

2) 再用更详细输出看具体失败在哪一步：

```bash
docker compose build --progress=plain backend
```

3) 仍然不行：通常就是升级 Docker Desktop / Docker Engine / Docker Compose。

### 6.2 明明只改了代码，却每次都在重装依赖

通常是缓存失效了，常见触发点：
- 你改了 `backend/pyproject.toml` 或 `backend/uv.lock`（这是“依赖输入”，必然重装）
- build context 发生了变化（例如把 `.venv/` 等大目录带进了构建上下文）

建议检查：
- `backend/.dockerignore` 是否包含 `.venv/`、`__pycache__/` 等本地噪音目录
- 用 `docker compose build --progress=plain backend` 看是哪一层没有命中缓存

### 6.3 构建很慢，但没报错

思路：
- 先确认是不是在“下载依赖/拉镜像”阶段慢（网络问题）
- 再看缓存是否命中（`--progress=plain`）
- 最后再考虑清理缓存/重建（`builder prune` 或 `--no-cache`）

---

## 7. 和本项目相关的“够用结论”

你只要记住这几条，在本项目里就够用了：
- `RUN --mount=type=cache` 是为了缓存依赖下载/编译，让构建变快（缓存不进镜像）
- `RUN --mount=type=bind` 是为了让“依赖安装层”的输入更干净，更容易命中缓存
- 只改业务代码时，一般不该重装依赖；如果重装了，从 `uv.lock/pyproject.toml` 变化和 `.dockerignore` 开始排查
- 排查构建问题最常用的是：`docker compose build --progress=plain backend`


# GitHub Actions / Workflow 概念说明（本仓库）

本文聚焦本仓库 `.github/workflows/*.yml` 中用到的概念与它们在仓库里的具体用途。

## 1. Workflow 基础结构

一个 workflow 文件通常包含以下顶层结构：

- `name`：工作流显示名称。
- `on`：触发条件（事件/分支/类型/定时等）。
- `jobs`：一个或多个 job。每个 job 运行在一个 runner 上。
- `jobs.<job_id>.steps`：job 内的步骤。每步可以执行命令或调用 Action。

常见键说明：

- `runs-on`：指定 runner 环境，如 `ubuntu-latest` 或自建 runner 标签（如 `self-hosted`, `staging`）。
- `steps.uses`：调用 GitHub Action（官方或第三方）。
- `steps.run`：直接执行 shell 命令。
- `env`：环境变量，可在 workflow、job、step 层级设置。
- `if`：条件表达式，决定是否执行（job 或 step 级）。
- `permissions`：限制 `GITHUB_TOKEN` 的权限范围。
- `needs`：声明 job 依赖关系。
- `continue-on-error`：失败后继续执行，常用于“先收集结果再统一失败”。
- `id` 与 `steps.<id>.outcome`：给 step 命名并读取其结果。

## 2. 触发事件（`on`）

本仓库用到的触发类型：

- `push`：代码推送时触发，可限定分支（如 `main`/`master`）。
- `pull_request`：PR 事件触发，不具备仓库 secrets（对 fork PR）。
- `pull_request_target`：在目标仓库上下文中运行，**可读取 secrets**；安全性要求更高。
- `issues`：Issue 事件（如 `opened`、`labeled`）。
- `issue_comment`：Issue/PR 评论事件。
- `release`：发布事件（如 `published`）。
- `workflow_run`：监听其他 workflow 完成后触发。
- `schedule`：定时（cron）触发。
- `workflow_dispatch`：手动触发。

## 3. Runner 与执行环境

- `ubuntu-latest`：GitHub 提供的 Linux runner。
- `self-hosted`：自建 runner。可加标签区分环境：
  - `production`、`staging`（分别用于生产/预发部署）。

## 4. 权限与安全

- `GITHUB_TOKEN`：GitHub 自动提供的 token。
- `permissions`：限制该 token 能做什么（例如 `pull-requests: write`）。
- `secrets.*`：仓库或组织级 secrets，例如 `SECRET_KEY`、`PROJECTS_TOKEN`。
- `pull_request_target`：在 base 仓库上下文运行且可访问 secrets，需要避免执行来自 PR 的不可信代码。
- `if: github.repository_owner != 'fastapi'`：避免在官方模板仓触发部署，仅在 fork/用户仓运行。

## 5. 依赖与工具

- `actions/checkout@v6`：拉取代码。
- `actions/setup-python@v6`：设置 Python 环境。
- `astral-sh/setup-uv@v7`：安装 `uv`（Python 包管理器/运行器）。
- `pre-commit`/`prek`：代码格式化与检查。
- `docker compose`：用 Compose 拉起本地服务或构建镜像。
- `curl`：简单健康检查。
- `smokeshow`：上传测试覆盖率报告并反馈到 GitHub 状态。
- `actions/upload-artifact` / `actions/download-artifact`：保存/读取产物（如 coverage HTML）。

## 6. 本仓库工作流解读

### 6.1 Deploy 部署类

- **Staging**：
  - 推送到 `master` 时部署到预发（自建 runner）。
- **Production**：
  - 发布 `release` 时部署到生产（自建 runner）。
- 均使用 `docker compose` build + up，并注入部署相关 secrets。

### 6.2 测试与质量

- **Test Backend**：
  - 起 DB/Redis/Mailcatcher，执行迁移与测试。
  - 上传 `coverage-html` 产物并检查覆盖率 >= 90%。
- **Test Docker Compose**：
  - 构建镜像并拉起 `backend`/`adminer`，跑健康检查。
- **pre-commit**：
  - 在 PR 触发，自动运行格式化/检查。
  - 有 secrets 时自动提交并回推格式化结果；无 secrets 用 lite action。
  - `alls-green` 汇总状态用于分支保护。
- **Smokeshow**：
  - 在 `Test Backend` 完成后运行，下载 coverage artifact 并上传。

### 6.3 仓库治理

- **Add to Project**：
  - PR/Issue 新开时加入项目看板（需 `PROJECTS_TOKEN`）。
- **Conflict detector**：
  - PR 有冲突时自动打 `conflicts` 标签并评论。
- **Labeler**：
  - 根据 `.github/labeler.yml` 自动打标签。
  - `check-labels` 保障 PR 至少有一个关键标签。
- **Issue Manager**：
  - 定时或触发条件满足时，按规则关闭 `answered/waiting/invalid`。

## 7. 关键配置文件

- `.github/labeler.yml`：定义自动标签匹配规则。
- `.github/dependabot.yml`：定义依赖自动更新范围与频率（Actions/uv/docker/compose）。

## 8. 常见关键字速查

- `types`：事件子类型（如 `opened`、`synchronize`、`published`）。
- `cron`：定时表达式（UTC）。
- `env`：环境变量，优先级：step > job > workflow。
- `if`：条件表达式，失败时跳过。
- `needs`：依赖其他 job 成功或完成。
- `always()`：无论成功失败都执行。
- `continue-on-error`：失败不终止 job。
- `workflow_run`：监听其他 workflow 的完成。

---

如果你希望我把“每个 workflow 对应的 secrets 列表”或“安全注意事项/替代实现”也单独整理，我可以再补一份更偏运维的说明文档。

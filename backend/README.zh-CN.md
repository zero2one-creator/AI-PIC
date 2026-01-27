# FastAPI 项目 - 后端

## 依赖

* [Docker](https://www.docker.com/)。
* 使用 [uv](https://docs.astral.sh/uv/) 管理 Python 包与虚拟环境。

## Docker Compose

按照 [../docs/development/docker.zh-CN.md](../docs/development/docker.zh-CN.md) 的指南，
使用 Docker Compose 启动本地开发环境。非 Docker 方式见
[../docs/development/nodocker.zh-CN.md](../docs/development/nodocker.zh-CN.md)。

## 通用工作流

默认情况下，本项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖，请先安装它。

在 `./backend/` 目录下安装依赖：

```console
$ uv sync
```

然后激活虚拟环境：

```console
$ source .venv/bin/activate
```

请确保你的编辑器使用正确的 Python 虚拟环境，解释器路径应为 `backend/.venv/bin/python`。

数据与 SQL 表对应的 SQLModel 模型位于 `./backend/app/models.py`；API 端点位于 `./backend/app/api/`；CRUD（Create、Read、Update、Delete）工具位于 `./backend/app/crud.py`。

## VS Code

项目已包含通过 VS Code 调试器运行后端的配置，因此你可以使用断点、暂停并查看变量等。

同样也已配置为可通过 VS Code 的 Python 测试面板运行测试。

## Docker Compose Override

在开发阶段，你可以在 `docker-compose.override.yml` 中调整只影响本地开发环境的 Docker Compose 设置。

对该文件的修改只影响本地开发环境，不影响生产环境。因此，你可以添加一些帮助开发流程的“临时”变更。

例如：后端代码目录会被同步到 Docker 容器中，你对代码的修改会实时复制到容器内目录。这样你可以立即验证改动，而无需重新构建 Docker 镜像。该方式仅建议用于开发；在生产环境中，应使用后端代码的最新版本构建镜像。但在开发中，它能让你迭代得非常快。

此外，还存在一个命令覆盖：使用 `fastapi run --reload` 替代默认的 `fastapi run`。它会启动单进程服务器（而不是生产环境那种多进程），并在代码变更时自动重载。如果你保存了带语法错误的 Python 文件，进程会报错退出，容器也会停止。此时你可以修复错误后重新启动容器：

```console
$ docker compose watch
```

还有一个已注释的 `command` 覆盖项：你可以取消注释它并注释掉默认命令。它会让后端容器运行一个“什么都不做”的进程，但保持容器存活。这样你就能进入运行中的容器并执行命令，例如打开 Python 解释器测试依赖是否正确安装，或启动能自动重载的开发服务器。

要进入容器并打开 `bash` 会话，可先启动整套环境：

```console
$ docker compose watch
```

然后在另一个终端中，对运行中的容器执行 `exec`：

```console
$ docker compose exec backend bash
```

你应该会看到类似输出：

```console
root@7f2607af31c3:/app#
```

这表示你已进入容器内的 `bash` 会话，以 `root` 用户身份位于 `/app` 目录。该目录下还有一个名为 "app" 的目录：容器内的代码位于 `/app/app`。

在容器内，你可以使用 `fastapi run --reload` 运行调试用的实时重载服务器：

```console
$ fastapi run --reload app/main.py
```

……看起来会像这样：

```console
root@7f2607af31c3:/app# fastapi run --reload app/main.py
```

然后回车即可启动。该服务会在检测到代码变更时自动重载。

不过，如果没有检测到变更但存在语法错误，它会直接报错停止。此时容器仍然存活且你仍在 Bash 会话中，修复错误后可快速重启：再次运行同一命令（按“上箭头”再回车）。

……这也是“让容器存活但不运行主要进程”这一做法的用途：你可以在 Bash 会话里自行启动并快速重启实时重载服务。

## 后端测试

运行后端测试：

```console
$ bash ./scripts/test.sh
```

测试使用 Pytest；请在 `./backend/tests/` 中修改或新增测试。

如果使用 GitHub Actions，测试会自动运行。

### 测试运行时栈

如果你的栈已经启动，只想运行测试，可以执行：

```bash
docker compose exec backend bash scripts/tests-start.sh
```

`/app/scripts/tests-start.sh` 脚本会在确保其它服务正常运行后调用 `pytest`。如需向 `pytest` 传递额外参数，可以直接附加到命令后面，它们会被转发。

例如：遇到第一个错误就停止：

```bash
docker compose exec backend bash scripts/tests-start.sh -x
```

### 测试覆盖率

测试运行后会生成 `htmlcov/index.html`，你可以在浏览器中打开它查看测试覆盖率。

## 数据库迁移

在本地开发时，应用目录会以 volume 的方式挂载到容器中。因此你可以在容器内执行 `alembic` 迁移命令，生成的迁移代码会出现在你的应用目录（而不仅仅在容器内），从而可以提交到 git 仓库中。

每次修改模型后，请确保为模型创建一个 "revision" 并将数据库 "upgrade" 到该 revision。这会更新数据库表结构；否则应用可能会报错。

* 在后端容器中启动交互式会话：

```console
$ docker compose exec backend bash
```

* Alembic 已配置为从 `./backend/app/models.py` 导入 SQLModel 模型。

* 修改模型后（例如新增一列），在容器内创建一个 revision，例如：

```console
$ alembic revision --autogenerate -m "Add column last_name to User model"
```

* 将 alembic 目录下生成的文件提交到 git 仓库。

* 创建 revision 后，在数据库中应用迁移（这一步会真正修改数据库）：

```console
$ alembic upgrade head
```

如果你完全不想使用迁移，可以取消注释 `./backend/app/core/db.py` 中以如下内容结尾的行：

```python
SQLModel.metadata.create_all(engine)
```

并注释掉 `scripts/prestart.sh` 中包含以下内容的那一行：

```console
$ alembic upgrade head
```

如果你不想使用默认模型并希望从一开始就删除/修改它们，并且没有任何旧的 revision，你可以删除 `./backend/app/alembic/versions/` 下的 revision 文件（Python 的 `.py` 文件），然后按上面描述创建首次迁移。

## 邮件模板

邮件模板位于 `./backend/app/email-templates/`。其中包含两个目录：`build` 与 `src`。`src` 目录包含用于构建最终邮件模板的源文件；`build` 目录包含应用实际使用的最终邮件模板。

继续之前，请确保在 VS Code 中安装 [MJML 扩展](https://marketplace.visualstudio.com/items?itemName=attilabuti.vscode-mjml)。

安装好 MJML 扩展后，你可以在 `src` 目录创建新的邮件模板。创建完成后，打开编辑器中的 `.mjml` 文件，通过 `Ctrl+Shift+P` 打开命令面板并搜索 `MJML: Export to HTML`。该操作会将 `.mjml` 转换为 `.html` 文件，然后你可以将其保存到 build 目录中。

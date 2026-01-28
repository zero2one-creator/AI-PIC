# Docker 镜像加速器配置指南

## 方案一：配置 Docker Daemon 镜像加速器（推荐）

这种方式会自动加速所有镜像拉取，无需修改 docker-compose.yml。

### macOS (Docker Desktop)

1. 打开 Docker Desktop
2. 点击右上角的设置图标（齿轮）
3. 进入 **Settings** > **Docker Engine**
4. 在 JSON 配置中添加以下内容：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://dockerhub.azk8s.cn",
    "https://reg-mirror.qiniu.com"
  ]
}
```

5. 点击 **Apply & Restart** 重启 Docker

### Linux

运行配置脚本：

```bash
bash scripts/setup-docker-mirror.sh
```

或手动配置：

```bash
# 备份原配置
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak

# 创建或更新配置
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://dockerhub.azk8s.cn",
    "https://reg-mirror.qiniu.com"
  ]
}
EOF

# 重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 验证配置

```bash
docker info | grep -A 10 "Registry Mirrors"
```

应该能看到配置的镜像加速器地址。

## 方案二：使用阿里云个人专属加速器

如果需要使用阿里云个人专属加速器（速度更快）：

1. 访问 [阿里云容器镜像服务](https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors)
2. 登录后获取个人专属加速器地址，格式为：`https://xxxxxx.mirror.aliyuncs.com`
3. 将上述地址添加到 `registry-mirrors` 数组中

## 方案三：直接使用阿里云镜像地址

如果不想配置 Docker daemon，可以直接在 Docker Compose 中使用阿里云镜像地址：

```yaml
services:
  adminer:
    image: registry.cn-hangzhou.aliyuncs.com/acs/adminer:latest
  proxy:
    image: registry.cn-hangzhou.aliyuncs.com/acs/traefik:3.0
  mailcatcher:
    image: registry.cn-hangzhou.aliyuncs.com/acs/mailpit:v1.22.3
```

**注意**：这种方式需要确保阿里云镜像仓库中有对应的镜像，某些镜像可能不存在。
PostgreSQL/Redis 已改为外部服务，因此不在 Compose 中配置。

## 推荐的镜像加速器地址

- 中科大镜像：`https://docker.mirrors.ustc.edu.cn`
- 网易镜像：`https://hub-mirror.c.163.com`
- 七牛云镜像：`https://reg-mirror.qiniu.com`
- 阿里云个人专属：`https://xxxxxx.mirror.aliyuncs.com`（需要登录获取）

## 故障排查

如果配置后仍然很慢：

1. 检查配置是否正确：`docker info | grep Registry`
2. 尝试清除 Docker 缓存：`docker system prune -a`
3. 检查网络连接
4. 尝试使用其他镜像加速器地址

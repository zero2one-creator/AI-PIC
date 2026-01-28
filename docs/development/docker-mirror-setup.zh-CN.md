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
3. 将上述地址添加到 `registry-mirrors` 数组中（放在最前面优先使用）

## 推荐的镜像加速器地址

- **中科大镜像**：`https://docker.mirrors.ustc.edu.cn`（推荐，速度快且稳定）
- **网易镜像**：`https://hub-mirror.c.163.com`
- **七牛云镜像**：`https://reg-mirror.qiniu.com`
- **阿里云个人专属**：`https://xxxxxx.mirror.aliyuncs.com`（需要登录获取，速度最快）

## 故障排查

如果配置后仍然很慢：

1. **检查配置是否正确**：
   ```bash
   docker info | grep Registry
   ```

2. **尝试清除 Docker 缓存**：
   ```bash
   docker system prune -a
   ```

3. **检查网络连接**：确保能访问镜像加速器地址

4. **尝试使用其他镜像加速器地址**：如果某个地址不可用，会自动尝试下一个

5. **重启 Docker 服务**：
   - macOS: 在 Docker Desktop 中重启
   - Linux: `sudo systemctl restart docker`

## 注意事项

- 配置镜像加速器后，Docker 会优先从加速器拉取镜像
- 如果加速器中没有某个镜像，会自动回退到 Docker Hub
- 建议配置多个镜像加速器作为备用
- 个人专属加速器通常比公共加速器更快更稳定

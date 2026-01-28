#!/bin/bash
# 配置 Docker 使用阿里云镜像加速器

# 阿里云镜像加速器地址（公共地址，无需登录）
# 如果需要个人专属地址，请访问：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
MIRROR_URL="https://docker.mirrors.ustc.edu.cn"

# 或者使用阿里云公共镜像加速器（如果上面的不可用，可以尝试）
# MIRROR_URL="https://registry.cn-hangzhou.aliyuncs.com"

# macOS Docker Desktop 配置路径
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到 macOS 系统"
    echo "请手动在 Docker Desktop 中配置镜像加速器："
    echo "1. 打开 Docker Desktop"
    echo "2. 进入 Settings > Docker Engine"
    echo "3. 在 JSON 配置中添加以下内容："
    echo ""
    cat <<EOF
{
  "registry-mirrors": [
    "${MIRROR_URL}",
    "https://dockerhub.azk8s.cn",
    "https://reg-mirror.qiniu.com"
  ]
}
EOF
    echo ""
    echo "4. 点击 Apply & Restart"
    echo ""
    echo "或者使用以下命令（需要 Docker Desktop 4.0+）："
    echo "docker context use default"
    
# Linux 系统配置
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到 Linux 系统"
    DAEMON_JSON="/etc/docker/daemon.json"
    
    # 备份原配置
    if [ -f "$DAEMON_JSON" ]; then
        sudo cp "$DAEMON_JSON" "${DAEMON_JSON}.bak"
        echo "已备份原配置到 ${DAEMON_JSON}.bak"
    fi
    
    # 创建或更新配置
    sudo mkdir -p /etc/docker
    sudo tee "$DAEMON_JSON" > /dev/null <<EOF
{
  "registry-mirrors": [
    "${MIRROR_URL}",
    "https://dockerhub.azk8s.cn",
    "https://reg-mirror.qiniu.com"
  ]
}
EOF
    
    echo "配置已更新，正在重启 Docker 服务..."
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    
    echo "配置完成！"
    echo "验证配置："
    docker info | grep -A 10 "Registry Mirrors"
else
    echo "不支持的操作系统: $OSTYPE"
    exit 1
fi

# MengDong Cloud 部署指南

## 快速部署步骤

### 1. 系统要求

#### 硬件要求
- **GPU**: NVIDIA GPU with Compute Capability >= 7.0
  - 推荐: RTX 3060 及以上
  - 最低: GTX 1080 Ti
- **内存**: 至少 16GB RAM
- **存储**: 至少 30GB 可用空间
- **网络**: 稳定的网络连接用于视频流处理

#### 软件要求
- Ubuntu 20.04 / 22.04 或 CentOS 7/8
- Docker >= 20.10
- NVIDIA Driver >= 525.x
- NVIDIA Container Toolkit

### 2. 安装 Docker 和 NVIDIA Container Toolkit

#### Ubuntu
```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### 验证安装
```bash
# 验证 Docker
docker --version

# 验证 GPU 可用性
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 3. 部署服务

#### 方法1: 使用已构建的镜像（推荐）

```bash
# 1. 加载 Docker 镜像
docker load -i mengdong_cloud.tar

# 2. 创建目录结构
mkdir -p mengdong_deployment/models
mkdir -p mengdong_deployment/logs
cd mengdong_deployment

# 3. 放置模型文件
# 将以下模型文件复制到 models 目录：
cp /path/to/model_mengdong_raa_adjusted.pt models/
cp /path/to/model_mengdong_small_SRL.pt models/
cp /path/to/model_mengdong_tower.pt models/
cp /path/to/model_mengdong_scene_album.pt models/

# 4. 启动容器
docker run -d \
  --name mengdong_cloud \
  --gpus all \
  --restart unless-stopped \
  -p 22266:22266 \
  -p 8554:8554 \
  -p 8080:8080 \
  -v $(pwd)/models:/workspace/models \
  -v $(pwd)/logs:/workspace/logs \
  mengdong_cloud:latest

# 5. 查看日志
docker logs -f mengdong_cloud

# 6. 验证服务
curl http://localhost:22266/health
curl http://localhost:22266/status
```

#### 方法2: 使用 Docker Compose

```bash
# 1. 准备配置
cd mengdong_deployment
cp /path/to/docker-compose.yml .

# 2. 放置模型文件（同上）

# 3. 启动服务
docker-compose up -d

# 4. 查看状态
docker-compose ps
docker-compose logs -f
```

### 4. 验证部署

#### 健康检查
```bash
curl http://localhost:22266/health
```

期望输出:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00.000000"
}
```

#### 服务状态
```bash
curl http://localhost:22266/status
```

期望输出:
```json
{
  "status": "running",
  "active_streams": 0,
  "max_streams": 100,
  "loaded_models": 4,
  "timestamp": "2024-01-15T10:00:00.000000"
}
```

#### API测试
```bash
# 获取算法能力
curl -X POST http://localhost:22266/v1/service/abilities \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 5. 模型转换说明

首次启动时，服务会自动将 PT 模型转换为 TensorRT 引擎。这个过程可能需要几分钟时间。

**查看转换进度**:
```bash
docker logs -f mengdong_cloud
```

**手动转换**（如果自动转换失败）:
```bash
docker exec -it mengdong_cloud bash
cd /workspace
python3 scripts/convert_models.py --config configs/models_config.yaml
```

### 6. 常见问题

#### Q1: GPU 不可用
```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 Docker GPU 支持
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 重启 Docker
sudo systemctl restart docker
```

#### Q2: 端口被占用
```bash
# 查看端口占用
sudo netstat -tulpn | grep 22266

# 修改端口映射
docker run -d \
  --name mengdong_cloud \
  --gpus all \
  -p 23000:22266 \
  ...
```

#### Q3: 模型加载失败
```bash
# 检查模型文件是否存在
docker exec -it mengdong_cloud ls -lh /workspace/models/

# 查看详细错误日志
docker logs mengdong_cloud 2>&1 | grep -i error
```

#### Q4: 内存不足
```bash
# 限制容器内存使用
docker run -d \
  --name mengdong_cloud \
  --gpus all \
  --memory="8g" \
  --memory-swap="16g" \
  ...
```

### 7. 性能优化

#### GPU 显存优化
```bash
# 使用环境变量限制 GPU 显存增长
docker run -d \
  --name mengdong_cloud \
  --gpus all \
  -e CUDA_VISIBLE_DEVICES=0 \
  -e TF_FORCE_GPU_ALLOW_GROWTH=true \
  ...
```

#### 并发流数调整
编辑配置文件 `/workspace/configs/models_config.yaml`:
```yaml
server:
  max_video_streams: 50  # 根据 GPU 性能调整
```

### 8. 监控和维护

#### 查看资源使用
```bash
# CPU 和内存使用
docker stats mengdong_cloud

# GPU 使用
nvidia-smi -l 1
```

#### 日志管理
```bash
# 查看实时日志
docker logs -f mengdong_cloud

# 查看最近100行
docker logs --tail 100 mengdong_cloud

# 导出日志
docker logs mengdong_cloud > mengdong_$(date +%Y%m%d).log
```

#### 备份和恢复
```bash
# 备份配置和数据
tar -czf mengdong_backup_$(date +%Y%m%d).tar.gz \
  models/ logs/ docker-compose.yml

# 恢复
tar -xzf mengdong_backup_YYYYMMDD.tar.gz
```

### 9. 服务管理

#### 启动服务
```bash
docker start mengdong_cloud
```

#### 停止服务
```bash
docker stop mengdong_cloud
```

#### 重启服务
```bash
docker restart mengdong_cloud
```

#### 更新服务
```bash
# 停止旧容器
docker stop mengdong_cloud
docker rm mengdong_cloud

# 加载新镜像
docker load -i mengdong_cloud_new.tar

# 启动新容器（使用相同的命令）
docker run -d ...
```

### 10. 安全建议

- 使用防火墙限制访问
- 启用 HTTPS（使用反向代理如 Nginx）
- 定期更新 Docker 镜像
- 监控异常访问
- 备份重要数据

### 11. 生产环境配置

#### 使用 Nginx 反向代理
```nginx
upstream mengdong_backend {
    server 127.0.0.1:22266;
}

server {
    listen 443 ssl;
    server_name api.mengdong.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://mengdong_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 大文件上传支持
        client_max_body_size 100M;
    }
}
```

#### 负载均衡（多实例）
```yaml
# docker-compose-cluster.yml
version: '3.8'

services:
  mengdong_cloud_1:
    image: mengdong_cloud:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]
    ports:
      - "22266:22266"
    volumes:
      - ./models:/workspace/models

  mengdong_cloud_2:
    image: mengdong_cloud:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
              capabilities: [gpu]
    ports:
      - "22267:22266"
    volumes:
      - ./models:/workspace/models

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - mengdong_cloud_1
      - mengdong_cloud_2
```

## 技术支持

如遇到问题，请联系技术支持团队或查看项目文档。

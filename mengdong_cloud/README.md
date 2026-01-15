# MengDong Cloud Analysis Service (蒙东云端分析服务)

基于 TensorRT-YOLO 的云端视频和图片分析服务，支持多模型推理、多路视频流处理和标准化API接口。

> **🔒 安全说明**: 本服务使用 PyTorch 2.6.0+ 版本，已修复 CVE 安全漏洞。所有依赖项均经过安全审查。

## 功能特性

### 核心功能
- ✅ **多模型支持**: 支持4个专用YOLO检测模型
  - 人员及安全装备检测 (安全帽、安全带等)
  - 钩子和差速器检测
  - 铁塔检测
  - 场景检测 (变压器、断路器、电线杆等)

- ✅ **视频流处理**: 支持最多100路视频流并发处理
  - 硬件编解码加速
  - RTSP和FLV流输出
  - H264/H265格式支持

- ✅ **图片分析**: 同步图片分析API
  - Base64图片输入输出
  - 实时推理返回

- ✅ **TensorRT加速**: PT模型自动转换为TensorRT引擎
  - FP16精度优化
  - GPU加速推理
  - 高吞吐量

### API接口

完全实现了规范文档中的接口：

1. **算法能力获取** - `POST /v1/service/abilities`
2. **视频任务管理** - `POST /v1/service/videoTask`
3. **任务控制** - `POST /v1/service/controlTask`
4. **图片分析** - `POST /v1/service/imageTask`
5. **服务保活** - `POST /analysis/api/v1/keepAlive`
6. **更新分析ID** - `POST /analysis/api/v1/updateAnalyseID`

## 模型说明

### 1. model_mengdong_raa_adjusted.pt
**算法编码**: 010101  
**描述**: 人员及安全装备检测  
**标签**:
- 0: person (人)
- 1: safetybelt (安全带)
- 2: mapblu (蓝色安全帽)
- 3: mapor (橘色安全帽)
- 4: mapr (红色安全帽)
- 5: mapwh (白色安全帽)
- 6: mapy (黄色安全帽)

### 2. model_mengdong_small_SRL.pt
**算法编码**: 100102  
**描述**: 钩子和差速器检测  
**标签**:
- 0: hook (钩子)
- 1: SRL (差速器)

### 3. model_mengdong_tower.pt
**算法编码**: 100103  
**描述**: 铁塔检测  
**标签**:
- 0: tower (铁塔)

### 4. model_mengdong_scene_album.pt
**算法编码**: 100104  
**描述**: 场景检测  
**标签**:
- 0: AerialWorkBucketTruck (斗臂车)
- 1: ConductorSpacer (导线间隔棒)
- 2: byq (变压器)
- 3: daozha (刀闸)
- 4: dlq (断路器)
- 5: gk (高空屋顶)
- 6: jsj (脚手架)
- 7: pcs (脚扣)
- 8: pole (电线杆)
- 9: xl (线路)

## 快速开始

### 前置要求

- NVIDIA GPU with CUDA support (Compute Capability >= 7.0)
- Docker with NVIDIA Container Toolkit
- 足够的存储空间 (至少10GB用于Docker镜像)

### 构建Docker镜像

1. 克隆仓库并进入目录：
```bash
git clone https://github.com/yifengzhong-cat/TensorRT-YOLO.git
cd TensorRT-YOLO
```

2. 构建并导出Docker镜像：
```bash
cd mengdong_cloud/docker
./build.sh
```

构建完成后，会在当前目录生成 `mengdong_cloud.tar` 文件。

### 部署到客户环境

1. 将 `mengdong_cloud.tar` 传输到目标机器

2. 加载Docker镜像：
```bash
docker load -i mengdong_cloud.tar
```

3. 准备模型文件：
```bash
mkdir -p models
# 将以下模型文件放入 models 目录：
# - model_mengdong_raa_adjusted.pt
# - model_mengdong_small_SRL.pt
# - model_mengdong_tower.pt
# - model_mengdong_scene_album.pt
```

4. 启动容器：
```bash
docker run -d \
  --name mengdong_cloud \
  --gpus all \
  --restart unless-stopped \
  -p 22266:22266 \
  -p 8554:8554 \
  -p 8080:8080 \
  -v $(pwd)/models:/workspace/models \
  mengdong_cloud:latest
```

5. 验证服务：
```bash
# 健康检查
curl http://localhost:22266/health

# 服务状态
curl http://localhost:22266/status

# 获取算法能力
curl -X POST http://localhost:22266/v1/service/abilities \
  -H "Content-Type: application/json" \
  -d '{}'
```

## API使用示例

### 1. 获取算法能力列表

```bash
curl -X POST http://localhost:22266/v1/service/abilities \
  -H "Content-Type: application/json" \
  -d '{}'
```

响应示例：
```json
{
  "resultCode": "200",
  "resultValue": {
    "abilityInfo": {
      "number": 4,
      "ability": [
        {
          "algCode": "010101",
          "algDesc": "人员及安全装备检测",
          "algParams": [
            {
              "key": "--sensitivity",
              "value": "灵敏度,范围[1,5]"
            }
          ]
        }
      ]
    }
  },
  "resultHint": null
}
```

### 2. 图片分析任务

```python
import base64
import requests
import json

# 读取图片并编码
with open('test.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# 发送分析请求
payload = {
    "analyseId": "test_001",
    "algCode": "010101",
    "imageData": image_data,
    "rule": {
        "algParams": [
            {
                "key": "--sensitivity",
                "value": "3"
            }
        ]
    }
}

response = requests.post(
    'http://localhost:22266/v1/service/imageTask',
    json=payload
)

result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 3. 视频任务管理

```python
import requests

# 启动视频分析任务
payload = {
    "algCode": "010101",
    "startTime": "2024-01-01 00:00:00",
    "endTime": "2024-12-31 23:59:59",
    "interval": 60,
    "command": 1,  # 1: 开始
    "videoInfo": [
        {
            "analyseId": "video_001",
            "devCode": "camera_001",
            "formatType": 0,
            "videoUrl": "rtsp://192.168.1.100:554/stream1"
        }
    ],
    "rule": {
        "algParams": [
            {
                "key": "--sensitivity",
                "value": "3"
            }
        ]
    }
}

response = requests.post(
    'http://localhost:22266/v1/service/videoTask',
    json=payload
)

print(response.json())
```

## 配置说明

### 模型配置文件

配置文件位于 `/workspace/configs/models_config.yaml`，包含：

- 模型路径配置
- 算法编码和描述
- 类别标签映射
- 服务器参数（端口、最大流数等）
- 视频输出格式配置

### 环境变量

可以通过环境变量覆盖默认配置：

```bash
docker run -d \
  --name mengdong_cloud \
  --gpus all \
  -e SERVER_PORT=22266 \
  -e MAX_VIDEO_STREAMS=100 \
  -p 22266:22266 \
  mengdong_cloud:latest
```

## 性能优化

### GPU内存管理
- 服务自动使用TensorRT FP16精度降低显存占用
- 支持批处理推理提高吞吐量
- 动态显存分配优化

### 视频流处理
- 硬件视频编解码加速
- 多线程并发处理
- 帧采样策略减少计算量

### 推理优化
- TensorRT引擎自动优化
- CUDA核函数加速
- 零拷贝内存传输

## 故障排查

### 模型转换失败
```bash
# 进入容器检查
docker exec -it mengdong_cloud bash

# 手动转换模型
python3 /workspace/scripts/convert_models.py \
  --config /workspace/configs/models_config.yaml
```

### 服务无响应
```bash
# 查看日志
docker logs mengdong_cloud

# 检查服务状态
curl http://localhost:22266/health
```

### GPU不可用
```bash
# 检查NVIDIA Docker运行时
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 确保安装了nvidia-container-toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## 技术架构

```
┌─────────────────────────────────────────────┐
│           API Server (Flask)                │
│  - REST API Endpoints                       │
│  - Request/Response Handling                │
└─────────────┬───────────────────────────────┘
              │
┌─────────────┴───────────────────────────────┐
│       Model Manager                         │
│  - Model Loading                            │
│  - Inference Management                     │
│  - Result Formatting                        │
└─────────────┬───────────────────────────────┘
              │
┌─────────────┴───────────────────────────────┐
│    Video Stream Manager                     │
│  - Multi-stream Processing                  │
│  - Hardware Encoding/Decoding               │
│  - Stream Control                           │
└─────────────┬───────────────────────────────┘
              │
┌─────────────┴───────────────────────────────┐
│       TensorRT-YOLO Engine                  │
│  - GPU Accelerated Inference                │
│  - FP16 Optimization                        │
│  - CUDA Acceleration                        │
└─────────────────────────────────────────────┘
```

## 更新日志

### v1.0.0 (2024-01-15)
- ✅ 初始版本发布
- ✅ 支持4个专用检测模型
- ✅ 实现所有API接口
- ✅ 支持100路视频流处理
- ✅ Docker容器化部署
- ✅ TensorRT引擎自动转换

## 许可证

本项目基于 TensorRT-YOLO 项目开发，遵循 GPL-3.0 许可证。

## 技术支持

如有问题或需要技术支持，请联系：
- 邮箱: support@mengdong.com
- 项目仓库: https://github.com/yifengzhong-cat/TensorRT-YOLO

## 致谢

本项目基于以下开源项目：
- [TensorRT-YOLO](https://github.com/laugh12321/TensorRT-YOLO)
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- [NVIDIA TensorRT](https://developer.nvidia.com/tensorrt)

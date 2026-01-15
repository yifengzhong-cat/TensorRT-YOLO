# 蒙东云端分析服务 - 快速开始

## 30秒快速部署

### 前提条件
- ✅ 已安装 Docker 和 NVIDIA Container Toolkit
- ✅ 有可用的 NVIDIA GPU

### 1. 加载镜像 (10秒)
```bash
docker load -i mengdong_cloud.tar
```

### 2. 准备模型 (可选，稍后添加)
```bash
mkdir -p models
# 将 .pt 模型文件放入 models 目录
```

### 3. 启动服务 (10秒)
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

### 4. 验证服务 (5秒)
```bash
# 等待服务启动（约30秒）
sleep 30

# 检查健康状态
curl http://localhost:22266/health

# 查看服务状态
curl http://localhost:22266/status
```

**完成！** 🎉 服务已经运行在 `http://localhost:22266`

---

## 5分钟快速测试

### Python 测试脚本

```python
import requests
import base64

# 1. 检查服务
print("Testing service...")
health = requests.get("http://localhost:22266/health").json()
print(f"✓ Service is {health['status']}")

# 2. 获取算法列表
abilities = requests.post("http://localhost:22266/v1/service/abilities", json={}).json()
print(f"✓ Found {abilities['resultValue']['abilityInfo']['number']} algorithms")

# 3. 分析图片 (需要准备一张测试图片)
# with open('test.jpg', 'rb') as f:
#     image_data = base64.b64encode(f.read()).decode('utf-8')
# 
# result = requests.post(
#     "http://localhost:22266/v1/service/imageTask",
#     json={
#         "analyseId": "test_001",
#         "algCode": "010101",
#         "imageData": image_data
#     }
# ).json()
# print(f"✓ Analysis complete: {result['resultValue']['analyseResults']}")

print("\n✓ All tests passed!")
```

### 使用客户端库

```python
from client import MengDongCloudClient

# 创建客户端
client = MengDongCloudClient("http://localhost:22266")

# 检查服务状态
status = client.get_status()
print(f"Active streams: {status['active_streams']}/{status['max_streams']}")
print(f"Loaded models: {status['loaded_models']}")

# 分析图片
result = client.analyze_image("test.jpg", alg_code="010101", sensitivity=3)
print(f"Found {len(result.detections)} objects")
for det in result.detections:
    print(f"  - {det.class_name}: {det.confidence:.2f}%")

# 保存结果
client.save_result_image(result, "result.jpg")
```

---

## 常见场景

### 场景1: 图片批量分析

```python
from pathlib import Path
from client import MengDongCloudClient

client = MengDongCloudClient()

# 分析目录中的所有图片
image_dir = Path("images")
for image_path in image_dir.glob("*.jpg"):
    result = client.analyze_image(image_path, alg_code="010101")
    print(f"{image_path.name}: {len(result.detections)} detections")
    
    # 保存结果
    output_path = Path("results") / image_path.name
    client.save_result_image(result, output_path)
```

### 场景2: 视频流监控

```python
from client import MengDongCloudClient

client = MengDongCloudClient()

# 启动多路视频流
cameras = [
    {"url": "rtsp://192.168.1.100:554/stream1", "code": "camera_001"},
    {"url": "rtsp://192.168.1.101:554/stream1", "code": "camera_002"},
    {"url": "rtsp://192.168.1.102:554/stream1", "code": "camera_003"},
]

for camera in cameras:
    stream_info = client.start_video_stream(
        video_url=camera["url"],
        dev_code=camera["code"],
        alg_code="010101",  # 人员及安全装备检测
        interval=60  # 每60秒上报一次结果
    )
    print(f"Started {camera['code']}: {stream_info['osdVideoUrl']}")
```

### 场景3: 实时监控面板

```python
import time
from client import MengDongCloudClient

client = MengDongCloudClient()

while True:
    status = client.get_status()
    print(f"\rStreams: {status['active_streams']}/{status['max_streams']}", end="")
    time.sleep(5)
```

---

## 算法选择

根据您的需求选择合适的算法：

| 算法编码 | 算法描述 | 适用场景 |
|---------|---------|---------|
| 010101 | 人员及安全装备检测 | 工地安全监控、人员管理 |
| 100102 | 钩子和差速器检测 | 设备维护、安全检查 |
| 100103 | 铁塔检测 | 电力巡检、基础设施监控 |
| 100104 | 场景检测 | 变电站监控、设备识别 |

---

## 性能优化建议

### 1. 图片大小
```python
# 推荐使用640x640分辨率
from PIL import Image

def optimize_image(input_path, output_path, max_size=640):
    img = Image.open(input_path)
    img.thumbnail((max_size, max_size))
    img.save(output_path, quality=85)
```

### 2. 灵敏度调整
- **灵敏度 1-2**: 要求高置信度，适合正式报警
- **灵敏度 3**: 默认平衡值，推荐使用
- **灵敏度 4-5**: 更多检出，适合初筛

### 3. 批处理
```python
# 批量处理提高效率
images = ["img1.jpg", "img2.jpg", "img3.jpg"]

for i in range(0, len(images), 10):  # 每10张一批
    batch = images[i:i+10]
    for img in batch:
        result = client.analyze_image(img)
        # 处理结果...
```

---

## 故障排查

### 问题1: 服务无法启动
```bash
# 查看日志
docker logs mengdong_cloud

# 常见原因：
# - GPU不可用: 检查 nvidia-smi
# - 端口被占用: 修改端口映射 -p 23000:22266
```

### 问题2: 模型加载失败
```bash
# 进入容器检查
docker exec -it mengdong_cloud bash
ls -lh /workspace/models/

# 手动转换模型
python3 /workspace/scripts/convert_models.py
```

### 问题3: API响应慢
```bash
# 检查GPU使用情况
nvidia-smi

# 检查容器资源
docker stats mengdong_cloud

# 可能需要：
# - 降低并发流数量
# - 调整图片分辨率
# - 使用批处理
```

---

## 下一步

- 📖 阅读完整的 [API使用手册](API_GUIDE.md)
- 🚀 查看详细的 [部署文档](DEPLOYMENT.md)
- 📚 参考 [项目README](README.md)
- 💬 遇到问题？查看 GitHub Issues

---

## 联系支持

如需帮助：
- 📧 邮箱: support@mengdong.com
- 🌐 项目: https://github.com/yifengzhong-cat/TensorRT-YOLO
- 📱 电话: [联系方式]

---

**祝使用愉快！** 🎉

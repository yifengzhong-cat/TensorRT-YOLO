# MengDong Cloud API 使用手册

## 目录
1. [概述](#概述)
2. [API端点](#api端点)
3. [认证](#认证)
4. [使用示例](#使用示例)
5. [错误处理](#错误处理)
6. [最佳实践](#最佳实践)

## 概述

MengDong Cloud Analysis Service 提供了一套完整的RESTful API，用于视频和图片的智能分析。服务支持多种检测模型，可以识别人员、安全装备、设备和场景等。

**Base URL**: `http://<server-ip>:22266`

**Content-Type**: `application/json`

**响应格式**: JSON

## API端点

### 1. 健康检查

检查服务是否正常运行。

**端点**: `GET /health`

**请求示例**:
```bash
curl http://localhost:22266/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00.000000"
}
```

### 2. 服务状态

获取服务的详细状态信息。

**端点**: `GET /status`

**请求示例**:
```bash
curl http://localhost:22266/status
```

**响应示例**:
```json
{
  "status": "running",
  "active_streams": 5,
  "max_streams": 100,
  "loaded_models": 4,
  "timestamp": "2024-01-15T10:00:00.000000"
}
```

### 3. 获取算法能力

获取所有可用的算法模型及其参数。

**端点**: `POST /v1/service/abilities`

**请求体**: `{}`

**请求示例**:
```bash
curl -X POST http://localhost:22266/v1/service/abilities \
  -H "Content-Type: application/json" \
  -d '{}'
```

**响应示例**:
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
        },
        {
          "algCode": "100102",
          "algDesc": "钩子和差速器检测",
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

### 4. 图片分析任务

对单张图片进行分析。

**端点**: `POST /v1/service/imageTask`

**请求参数**:
- `analyseId` (string, 必选): 分析任务ID
- `algCode` (string, 必选): 算法编码
- `imageData` (string, 必选): Base64编码的图片数据
- `rule` (object, 可选): 分析规则

**Python示例**:
```python
import base64
import requests
import json

# 读取并编码图片
with open('test.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# 构建请求
payload = {
    "analyseId": "image_001",
    "algCode": "010101",  # 人员及安全装备检测
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

# 发送请求
response = requests.post(
    'http://localhost:22266/v1/service/imageTask',
    json=payload,
    timeout=30
)

result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))

# 保存结果图片
if result['resultCode'] == '200':
    osd_image_data = result['resultValue']['osdImageData']
    with open('result.jpg', 'wb') as f:
        f.write(base64.b64decode(osd_image_data))
```

**响应示例**:
```json
{
  "resultCode": "200",
  "resultValue": {
    "analyseTime": "2024-01-15 10:30:00",
    "analyseResults": ["person", "mapy"],
    "rawImageName": "image_001_raw.jpg",
    "rawImageData": "base64...",
    "osdImageName": "image_001_osd.jpg",
    "osdImageData": "base64...",
    "resultDetail": [
      {
        "algCode": "010101",
        "resultDesc": "person",
        "num": 2,
        "resultItems": [
          {
            "score": 95.7,
            "leftTopX": 100,
            "leftTopY": 200,
            "rightBottomX": 300,
            "rightBottomY": 500
          }
        ]
      }
    ]
  },
  "resultHint": null
}
```

### 5. 视频任务管理

创建、启动、停止或删除视频分析任务。

**端点**: `POST /v1/service/videoTask`

**请求参数**:
- `algCode` (string, 必选): 算法编码
- `command` (int, 必选): 命令类型 (0:停止, 1:开始, 2:删除)
- `videoInfo` (array, 必选): 视频流信息列表
- `startTime` (string, 必选): 任务开始时间
- `endTime` (string, 必选): 任务结束时间
- `interval` (int, 必选): 结果上传间隔(秒)
- `rule` (object, 可选): 分析规则

**Python示例**:
```python
import requests
import json

# 启动视频分析任务
payload = {
    "algCode": "010101",
    "startTime": "2024-01-01 00:00:00",
    "endTime": "2024-12-31 23:59:59",
    "interval": 60,  # 每60秒上传一次结果
    "command": 1,  # 开始
    "videoInfo": [
        {
            "analyseId": "video_001",
            "devCode": "camera_001",
            "formatType": 0,  # 0: H264, 1: H265
            "videoUrl": "rtsp://192.168.1.100:554/stream1"
        },
        {
            "analyseId": "video_002",
            "devCode": "camera_002",
            "formatType": 0,
            "videoUrl": "rtsp://192.168.1.101:554/stream1"
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
    json=payload,
    timeout=30
)

result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))

# 获取 OSD 视频流 URL
if result['resultCode'] == '200':
    for item in result['resultValue']:
        print(f"Camera: {item['devCode']}")
        print(f"OSD Stream: {item['osdVideoUrl']}")
```

**响应示例**:
```json
{
  "resultCode": "200",
  "resultValue": [
    {
      "analyseId": "video_001",
      "devCode": "camera_001",
      "osdVideoUrl": "rtsp://localhost:8554/video_001"
    },
    {
      "analyseId": "video_002",
      "devCode": "camera_002",
      "osdVideoUrl": "rtsp://localhost:8554/video_002"
    }
  ],
  "resultHint": null
}
```

### 6. 任务控制

控制已创建的视频分析任务。

**端点**: `POST /v1/service/controlTask`

**请求参数**:
- `analyseId` (string, 必选): 分析任务ID
- `command` (int, 必选): 命令类型 (0:停止, 1:开始, 2:删除)

**示例 - 停止任务**:
```python
payload = {
    "analyseId": "video_001",
    "command": 0  # 停止
}

response = requests.post(
    'http://localhost:22266/v1/service/controlTask',
    json=payload
)
```

**示例 - 恢复任务**:
```python
payload = {
    "analyseId": "video_001",
    "command": 1  # 开始
}

response = requests.post(
    'http://localhost:22266/v1/service/controlTask',
    json=payload
)
```

**示例 - 删除任务**:
```python
payload = {
    "analyseId": "video_001",
    "command": 2  # 删除
}

response = requests.post(
    'http://localhost:22266/v1/service/controlTask',
    json=payload
)
```

### 7. 服务保活

维持服务在线状态。

**端点**: `POST /analysis/api/v1/keepAlive`

**请求示例**:
```python
payload = {
    "devIP": "192.168.1.100",
    "devPort": 22266
}

response = requests.post(
    'http://localhost:22266/analysis/api/v1/keepAlive',
    json=payload
)
```

**响应示例**:
```json
{
  "resultCode": "200",
  "resultValue": {
    "devId": "mengdong_cloud_192.168.1.100_22266"
  },
  "resultHint": "keep alive"
}
```

### 8. 更新分析ID

更新正在运行的任务的分析ID。

**端点**: `POST /analysis/api/v1/updateAnalyseID`

**请求示例**:
```python
payload = {
    "oldAnalyseId": "video_001",
    "newAnalyseId": "video_001_new"
}

response = requests.post(
    'http://localhost:22266/analysis/api/v1/updateAnalyseID',
    json=payload
)
```

## 认证

当前版本不需要认证。如果需要在生产环境中启用认证，建议使用反向代理（如Nginx）添加认证层。

## 错误处理

### HTTP状态码

- `200`: 成功
- `400`: 请求参数错误
- `403`: 请求被禁止，无权限
- `404`: 请求的对象不存在
- `500`: 服务器内部错误
- `503`: 服务当前负荷满

### 错误响应格式

```json
{
  "resultCode": "400",
  "resultValue": null,
  "resultHint": "缺少必要参数: algCode"
}
```

### Python错误处理示例

```python
import requests
import json

def call_api(endpoint, payload):
    try:
        response = requests.post(
            f'http://localhost:22266{endpoint}',
            json=payload,
            timeout=30
        )
        
        result = response.json()
        
        if result['resultCode'] == '200':
            return True, result['resultValue']
        else:
            print(f"API Error: {result['resultHint']}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("Request timeout")
        return False, None
    except requests.exceptions.ConnectionError:
        print("Connection error")
        return False, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False, None

# 使用
success, data = call_api('/v1/service/abilities', {})
if success:
    print(f"Found {data['abilityInfo']['number']} algorithms")
```

## 最佳实践

### 1. 图片处理

- **图片大小**: 建议640x640或更小，以获得最佳性能
- **格式**: 支持JPG、PNG等常见格式
- **压缩**: 建议先压缩图片再编码，减少传输时间

```python
from PIL import Image
import io
import base64

def prepare_image(image_path, max_size=640):
    img = Image.open(image_path)
    img.thumbnail((max_size, max_size))
    
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return image_data
```

### 2. 视频流管理

- **并发限制**: 服务最多支持100路视频流
- **URL格式**: 支持RTSP、HTTP等协议
- **重连策略**: 视频流断开时会自动重连

```python
# 批量管理视频流
def manage_streams(streams, command):
    """
    command: 0=停止, 1=开始, 2=删除
    """
    batch_size = 10  # 分批处理
    
    for i in range(0, len(streams), batch_size):
        batch = streams[i:i+batch_size]
        
        payload = {
            "algCode": "010101",
            "command": command,
            "videoInfo": batch,
            "interval": 60
        }
        
        response = requests.post(
            'http://localhost:22266/v1/service/videoTask',
            json=payload
        )
        
        print(f"Batch {i//batch_size + 1} processed")
```

### 3. 灵敏度调整

灵敏度参数影响检测阈值：
- `1`: 低灵敏度（高置信度要求，少误报）
- `3`: 默认（平衡）
- `5`: 高灵敏度（低置信度要求，多检出）

```python
def analyze_with_sensitivity(image_path, sensitivity=3):
    image_data = prepare_image(image_path)
    
    payload = {
        "analyseId": f"task_{int(time.time())}",
        "algCode": "010101",
        "imageData": image_data,
        "rule": {
            "algParams": [
                {
                    "key": "--sensitivity",
                    "value": str(sensitivity)
                }
            ]
        }
    }
    
    response = requests.post(
        'http://localhost:22266/v1/service/imageTask',
        json=payload
    )
    
    return response.json()
```

### 4. 结果处理

```python
def process_detection_results(result):
    """处理检测结果"""
    if result['resultCode'] != '200':
        return []
    
    detections = []
    result_detail = result['resultValue']['resultDetail']
    
    for detail in result_detail:
        class_name = detail['resultDesc']
        
        for item in detail['resultItems']:
            detection = {
                'class': class_name,
                'confidence': item['score'],
                'bbox': [
                    item['leftTopX'],
                    item['leftTopY'],
                    item['rightBottomX'],
                    item['rightBottomY']
                ]
            }
            detections.append(detection)
    
    return detections
```

### 5. 性能监控

```python
import time

def monitor_performance(image_path, runs=100):
    """监控API性能"""
    image_data = prepare_image(image_path)
    
    payload = {
        "analyseId": "perf_test",
        "algCode": "010101",
        "imageData": image_data
    }
    
    times = []
    for i in range(runs):
        start = time.time()
        
        response = requests.post(
            'http://localhost:22266/v1/service/imageTask',
            json=payload
        )
        
        elapsed = time.time() - start
        times.append(elapsed)
        
        if (i + 1) % 10 == 0:
            print(f"Completed {i + 1}/{runs} requests")
    
    print(f"\nPerformance Statistics:")
    print(f"  Average: {sum(times)/len(times):.3f}s")
    print(f"  Min: {min(times):.3f}s")
    print(f"  Max: {max(times):.3f}s")
```

## 完整示例

### 综合应用示例

```python
import requests
import base64
import json
import time
from pathlib import Path

class MengDongClient:
    """MengDong Cloud API Client"""
    
    def __init__(self, base_url="http://localhost:22266"):
        self.base_url = base_url
    
    def get_abilities(self):
        """获取算法能力"""
        response = requests.post(f"{self.base_url}/v1/service/abilities", json={})
        return response.json()
    
    def analyze_image(self, image_path, alg_code="010101", sensitivity=3):
        """分析图片"""
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            "analyseId": f"img_{int(time.time())}",
            "algCode": alg_code,
            "imageData": image_data,
            "rule": {
                "algParams": [{"key": "--sensitivity", "value": str(sensitivity)}]
            }
        }
        
        response = requests.post(
            f"{self.base_url}/v1/service/imageTask",
            json=payload
        )
        return response.json()
    
    def start_video_stream(self, stream_url, alg_code="010101", interval=60):
        """启动视频流分析"""
        payload = {
            "algCode": alg_code,
            "startTime": "2024-01-01 00:00:00",
            "endTime": "2024-12-31 23:59:59",
            "interval": interval,
            "command": 1,
            "videoInfo": [{
                "analyseId": f"video_{int(time.time())}",
                "devCode": "camera_001",
                "formatType": 0,
                "videoUrl": stream_url
            }]
        }
        
        response = requests.post(
            f"{self.base_url}/v1/service/videoTask",
            json=payload
        )
        return response.json()

# 使用示例
client = MengDongClient()

# 1. 获取可用算法
abilities = client.get_abilities()
print("Available algorithms:")
for ability in abilities['resultValue']['abilityInfo']['ability']:
    print(f"  - {ability['algDesc']} ({ability['algCode']})")

# 2. 分析图片
result = client.analyze_image("test.jpg", alg_code="010101", sensitivity=3)
if result['resultCode'] == '200':
    print(f"\nDetected: {result['resultValue']['analyseResults']}")

# 3. 启动视频流
stream_result = client.start_video_stream("rtsp://192.168.1.100:554/stream1")
if stream_result['resultCode'] == '200':
    print(f"\nVideo stream started: {stream_result['resultValue'][0]['osdVideoUrl']}")
```

## 技术支持

如有任何问题或需要技术支持，请参考：
- [部署文档](DEPLOYMENT.md)
- [README](README.md)
- GitHub Issues

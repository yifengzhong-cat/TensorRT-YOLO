"""
MengDong Cloud Analysis Service - Python Client Library
简化的客户端库，便于集成到其他应用中
"""
import base64
import json
import time
from typing import List, Dict, Optional, Union
from pathlib import Path
import requests
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """单个检测结果"""
    class_name: str
    confidence: float
    bbox: List[int]  # [left_top_x, left_top_y, right_bottom_x, right_bottom_y]


@dataclass
class AnalysisResult:
    """完整的分析结果"""
    analyse_id: str
    analyse_time: str
    detections: List[DetectionResult]
    raw_image_data: Optional[str] = None
    osd_image_data: Optional[str] = None


class MengDongCloudClient:
    """
    MengDong Cloud Analysis Service 客户端
    
    Examples:
        >>> client = MengDongCloudClient("http://localhost:22266")
        >>> 
        >>> # 检查服务状态
        >>> status = client.get_status()
        >>> print(f"Active streams: {status['active_streams']}")
        >>> 
        >>> # 图片分析
        >>> result = client.analyze_image("test.jpg", alg_code="010101")
        >>> for det in result.detections:
        >>>     print(f"{det.class_name}: {det.confidence:.2f}%")
        >>> 
        >>> # 视频流分析
        >>> stream_id = client.start_video_stream(
        >>>     "rtsp://192.168.1.100:554/stream1",
        >>>     alg_code="010101"
        >>> )
    """
    
    def __init__(self, base_url: str = "http://localhost:22266", timeout: int = 30):
        """
        初始化客户端
        
        Args:
            base_url: API服务器地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST等)
            endpoint: API端点
            **kwargs: 传递给requests的其他参数
        
        Returns:
            响应JSON数据
        
        Raises:
            requests.exceptions.RequestException: 请求失败
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        
        return response.json()
    
    def health_check(self) -> bool:
        """
        检查服务健康状态
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            result = self._request('GET', '/health')
            return result.get('status') == 'healthy'
        except Exception:
            return False
    
    def get_status(self) -> Dict:
        """
        获取服务状态
        
        Returns:
            服务状态信息
        """
        return self._request('GET', '/status')
    
    def get_abilities(self) -> List[Dict]:
        """
        获取所有可用的算法能力
        
        Returns:
            算法能力列表
        """
        result = self._request('POST', '/v1/service/abilities', json={})
        
        if result['resultCode'] == '200':
            return result['resultValue']['abilityInfo']['ability']
        else:
            raise Exception(f"Failed to get abilities: {result.get('resultHint')}")
    
    def analyze_image(
        self,
        image_path: Union[str, Path],
        alg_code: str = "010101",
        sensitivity: int = 3,
        analyse_id: Optional[str] = None
    ) -> AnalysisResult:
        """
        分析图片
        
        Args:
            image_path: 图片文件路径
            alg_code: 算法编码
            sensitivity: 灵敏度 (1-5)
            analyse_id: 分析ID，如果不提供则自动生成
        
        Returns:
            分析结果
        """
        # 读取并编码图片
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # 生成分析ID
        if analyse_id is None:
            analyse_id = f"img_{int(time.time() * 1000)}"
        
        # 构建请求
        payload = {
            "analyseId": analyse_id,
            "algCode": alg_code,
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
        
        # 发送请求
        result = self._request('POST', '/v1/service/imageTask', json=payload)
        
        if result['resultCode'] != '200':
            raise Exception(f"Analysis failed: {result.get('resultHint')}")
        
        # 解析结果
        return self._parse_analysis_result(analyse_id, result['resultValue'])
    
    def analyze_image_data(
        self,
        image_data: str,
        alg_code: str = "010101",
        sensitivity: int = 3,
        analyse_id: Optional[str] = None
    ) -> AnalysisResult:
        """
        分析Base64编码的图片数据
        
        Args:
            image_data: Base64编码的图片数据
            alg_code: 算法编码
            sensitivity: 灵敏度 (1-5)
            analyse_id: 分析ID
        
        Returns:
            分析结果
        """
        if analyse_id is None:
            analyse_id = f"img_{int(time.time() * 1000)}"
        
        payload = {
            "analyseId": analyse_id,
            "algCode": alg_code,
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
        
        result = self._request('POST', '/v1/service/imageTask', json=payload)
        
        if result['resultCode'] != '200':
            raise Exception(f"Analysis failed: {result.get('resultHint')}")
        
        return self._parse_analysis_result(analyse_id, result['resultValue'])
    
    def start_video_stream(
        self,
        video_url: str,
        dev_code: str,
        alg_code: str = "010101",
        interval: int = 60,
        format_type: int = 0,
        sensitivity: int = 3,
        analyse_id: Optional[str] = None,
        start_time: str = "2024-01-01 00:00:00",
        end_time: str = "2024-12-31 23:59:59"
    ) -> Dict:
        """
        启动视频流分析
        
        Args:
            video_url: 视频流URL
            dev_code: 设备编码
            alg_code: 算法编码
            interval: 结果上传间隔（秒）
            format_type: 视频格式 (0: H264, 1: H265)
            sensitivity: 灵敏度 (1-5)
            analyse_id: 分析ID
            start_time: 任务开始时间
            end_time: 任务结束时间
        
        Returns:
            包含analyse_id和osdVideoUrl的字典
        """
        if analyse_id is None:
            analyse_id = f"video_{int(time.time() * 1000)}"
        
        payload = {
            "algCode": alg_code,
            "startTime": start_time,
            "endTime": end_time,
            "interval": interval,
            "command": 1,  # Start
            "videoInfo": [
                {
                    "analyseId": analyse_id,
                    "devCode": dev_code,
                    "formatType": format_type,
                    "videoUrl": video_url
                }
            ],
            "rule": {
                "algParams": [
                    {
                        "key": "--sensitivity",
                        "value": str(sensitivity)
                    }
                ]
            }
        }
        
        result = self._request('POST', '/v1/service/videoTask', json=payload)
        
        if result['resultCode'] != '200':
            raise Exception(f"Failed to start video stream: {result.get('resultHint')}")
        
        return result['resultValue'][0]
    
    def stop_video_stream(self, analyse_id: str) -> bool:
        """
        停止视频流分析
        
        Args:
            analyse_id: 分析ID
        
        Returns:
            成功返回True
        """
        return self._control_task(analyse_id, 0)
    
    def resume_video_stream(self, analyse_id: str) -> bool:
        """
        恢复视频流分析
        
        Args:
            analyse_id: 分析ID
        
        Returns:
            成功返回True
        """
        return self._control_task(analyse_id, 1)
    
    def delete_video_stream(self, analyse_id: str) -> bool:
        """
        删除视频流分析
        
        Args:
            analyse_id: 分析ID
        
        Returns:
            成功返回True
        """
        return self._control_task(analyse_id, 2)
    
    def _control_task(self, analyse_id: str, command: int) -> bool:
        """
        控制任务
        
        Args:
            analyse_id: 分析ID
            command: 命令 (0: stop, 1: start, 2: delete)
        
        Returns:
            成功返回True
        """
        payload = {
            "analyseId": analyse_id,
            "command": command
        }
        
        result = self._request('POST', '/v1/service/controlTask', json=payload)
        return result['resultCode'] == '200'
    
    def keep_alive(self, dev_ip: str, dev_port: int = 22266) -> str:
        """
        发送保活消息
        
        Args:
            dev_ip: 设备IP
            dev_port: 设备端口
        
        Returns:
            设备ID
        """
        payload = {
            "devIP": dev_ip,
            "devPort": dev_port
        }
        
        result = self._request('POST', '/analysis/api/v1/keepAlive', json=payload)
        
        if result['resultCode'] == '200':
            return result['resultValue']['devId']
        else:
            raise Exception(f"Keep alive failed: {result.get('resultHint')}")
    
    def update_analyse_id(self, old_id: str, new_id: str) -> bool:
        """
        更新分析ID
        
        Args:
            old_id: 旧ID
            new_id: 新ID
        
        Returns:
            成功返回True
        """
        payload = {
            "oldAnalyseId": old_id,
            "newAnalyseId": new_id
        }
        
        result = self._request('POST', '/analysis/api/v1/updateAnalyseID', json=payload)
        return result['resultCode'] == '200'
    
    def _parse_analysis_result(self, analyse_id: str, result_value: Dict) -> AnalysisResult:
        """
        解析分析结果
        
        Args:
            analyse_id: 分析ID
            result_value: API返回的结果值
        
        Returns:
            AnalysisResult对象
        """
        detections = []
        
        result_detail = result_value.get('resultDetail', [])
        for detail in result_detail:
            class_name = detail['resultDesc']
            
            for item in detail.get('resultItems', []):
                detection = DetectionResult(
                    class_name=class_name,
                    confidence=item['score'],
                    bbox=[
                        item['leftTopX'],
                        item['leftTopY'],
                        item['rightBottomX'],
                        item['rightBottomY']
                    ]
                )
                detections.append(detection)
        
        return AnalysisResult(
            analyse_id=analyse_id,
            analyse_time=result_value.get('analyseTime', ''),
            detections=detections,
            raw_image_data=result_value.get('rawImageData'),
            osd_image_data=result_value.get('osdImageData')
        )
    
    def save_result_image(self, result: AnalysisResult, output_path: Union[str, Path], use_osd: bool = True):
        """
        保存结果图片
        
        Args:
            result: 分析结果
            output_path: 输出路径
            use_osd: 是否使用OSD图片（带标注），否则使用原图
        """
        image_data = result.osd_image_data if use_osd else result.raw_image_data
        
        if not image_data:
            raise ValueError("No image data available")
        
        with open(output_path, 'wb') as f:
            f.write(base64.b64decode(image_data))
    
    def close(self):
        """关闭会话"""
        self.session.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 使用示例
if __name__ == "__main__":
    # 使用上下文管理器
    with MengDongCloudClient("http://localhost:22266") as client:
        # 检查服务状态
        if not client.health_check():
            print("Service is not healthy!")
            exit(1)
        
        # 获取服务状态
        status = client.get_status()
        print(f"Service Status:")
        print(f"  Active streams: {status['active_streams']}/{status['max_streams']}")
        print(f"  Loaded models: {status['loaded_models']}")
        
        # 获取算法能力
        abilities = client.get_abilities()
        print(f"\nAvailable Algorithms:")
        for ability in abilities:
            print(f"  - {ability['algDesc']} ({ability['algCode']})")
        
        # 图片分析示例
        # result = client.analyze_image("test.jpg", alg_code="010101", sensitivity=3)
        # print(f"\nImage Analysis Results:")
        # print(f"  Time: {result.analyse_time}")
        # print(f"  Detections: {len(result.detections)}")
        # for det in result.detections:
        #     print(f"    - {det.class_name}: {det.confidence:.2f}%")
        # 
        # # 保存结果图片
        # client.save_result_image(result, "result.jpg")
        
        # 视频流分析示例
        # stream_info = client.start_video_stream(
        #     video_url="rtsp://192.168.1.100:554/stream1",
        #     dev_code="camera_001",
        #     alg_code="010101",
        #     interval=60
        # )
        # print(f"\nVideo Stream Started:")
        # print(f"  Analysis ID: {stream_info['analyseId']}")
        # print(f"  OSD URL: {stream_info['osdVideoUrl']}")
        
        print("\nClient test completed successfully!")

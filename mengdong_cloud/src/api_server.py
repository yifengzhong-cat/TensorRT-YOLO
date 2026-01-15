"""
Cloud Analysis Service API Server
Implements REST API endpoints for video and image analysis
"""
import os
import logging
import base64
import json
from datetime import datetime
from typing import Optional, List
import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

from model_manager import ModelManager
from video_stream_manager import VideoStreamManager, VideoStreamConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global instances
model_manager: Optional[ModelManager] = None
video_manager: Optional[VideoStreamManager] = None
result_callback_url: Optional[str] = None


def init_services(config_path: str = '/workspace/configs/models_config.yaml'):
    """Initialize model manager and video stream manager"""
    global model_manager, video_manager
    
    logger.info("Initializing services...")
    
    # Initialize model manager
    model_manager = ModelManager(config_path)
    model_manager.load_models()
    
    # Initialize video stream manager
    max_streams = model_manager.get_server_config().get('max_video_streams', 100)
    video_manager = VideoStreamManager(max_streams=max_streams)
    
    # Set callbacks
    video_manager.set_inference_callback(inference_callback)
    video_manager.set_result_callback(result_upload_callback)
    
    logger.info("Services initialized successfully")


def inference_callback(frame: np.ndarray, alg_code: str, rule: Optional[dict]) -> dict:
    """Callback for running inference on a frame"""
    try:
        # Extract sensitivity from rule if provided
        sensitivity = 3  # default
        if rule and 'algParams' in rule:
            for param in rule['algParams']:
                if param['key'] == '--sensitivity':
                    sensitivity = int(param['value'])
                    break
        
        # Run inference
        result = model_manager.predict(frame, alg_code, sensitivity)
        
        # Format result
        formatted_result = model_manager.format_detection_result(result, alg_code)
        
        return formatted_result
    except Exception as e:
        logger.error(f"Inference callback error: {e}")
        return {'analyseResults': [], 'resultDetail': []}


def result_upload_callback(analyse_id: str, result: dict, frame: np.ndarray):
    """Callback for uploading results to the platform"""
    try:
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        osd_image_data = base64.b64encode(buffer).decode('utf-8')
        
        # Prepare result payload
        payload = {
            'analyseId': analyse_id,
            'analyseTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analyseResults': result.get('analyseResults', []),
            'osdImageData': osd_image_data,
            'osdImageName': f"{analyse_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
            'resultDetail': result.get('resultDetail', [])
        }
        
        # Send to platform's result endpoint
        # TODO: Configure result_callback_url in config and implement actual HTTP POST
        # For now, just log the result
        if result_callback_url:
            # Future implementation: POST to result_callback_url
            pass
        
        logger.info(f"Result for {analyse_id}: {len(result.get('analyseResults', []))} detections")
        
    except Exception as e:
        logger.error(f"Result upload callback error: {e}")


# ==================== API Endpoints ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/v1/service/abilities', methods=['POST'])
def get_abilities():
    """
    4.1.7.1. 服务平台算法能力获取
    Get algorithm capabilities
    """
    try:
        abilities = model_manager.get_all_abilities()
        
        return jsonify({
            'resultCode': '200',
            'resultValue': {
                'abilityInfo': {
                    'number': len(abilities),
                    'ability': abilities
                }
            },
            'resultHint': None
        })
    except Exception as e:
        logger.error(f"Error getting abilities: {e}")
        return jsonify({
            'resultCode': '500',
            'resultValue': None,
            'resultHint': str(e)
        }), 500


@app.route('/v1/service/videoTask', methods=['POST'])
def video_task():
    """
    4.1.7.2. 视频任务管理
    Video task management
    """
    try:
        data = request.get_json()
        
        alg_code = data.get('algCode')
        command = data.get('command')  # 0: stop, 1: start, 2: delete
        video_info_list = data.get('videoInfo', [])
        start_time = data.get('startTime')
        end_time = data.get('endTime')
        interval = data.get('interval', 60)
        rule = data.get('rule')
        
        if not alg_code or command is None or not video_info_list:
            return jsonify({
                'resultCode': '400',
                'resultValue': None,
                'resultHint': '缺少必要参数'
            }), 400
        
        # Check if model exists
        if not model_manager.get_model(alg_code):
            return jsonify({
                'resultCode': '404',
                'resultValue': None,
                'resultHint': f'算法模型未找到: {alg_code}'
            }), 404
        
        result_value = []
        
        for video_info in video_info_list:
            analyse_id = video_info.get('analyseId')
            dev_code = video_info.get('devCode')
            video_url = video_info.get('videoUrl')
            format_type = video_info.get('formatType', 0)
            
            if command == 1:  # Start
                config = VideoStreamConfig(
                    analyse_id=analyse_id,
                    dev_code=dev_code,
                    video_url=video_url,
                    format_type=format_type,
                    alg_code=alg_code,
                    rule=rule,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if video_manager.add_stream(config):
                    # Generate OSD video URL (placeholder)
                    osd_video_url = f"rtsp://localhost:8554/{analyse_id}"
                    result_value.append({
                        'analyseId': analyse_id,
                        'devCode': dev_code,
                        'osdVideoUrl': osd_video_url
                    })
                else:
                    logger.error(f"Failed to start stream: {analyse_id}")
                    
            elif command == 0:  # Stop
                video_manager.stop_stream(analyse_id)
                result_value.append({
                    'analyseId': analyse_id,
                    'devCode': dev_code
                })
                
            elif command == 2:  # Delete
                video_manager.remove_stream(analyse_id)
                result_value.append({
                    'analyseId': analyse_id,
                    'devCode': dev_code
                })
        
        return jsonify({
            'resultCode': '200',
            'resultValue': result_value,
            'resultHint': None
        })
        
    except Exception as e:
        logger.error(f"Error in video task: {e}")
        return jsonify({
            'resultCode': '500',
            'resultValue': None,
            'resultHint': str(e)
        }), 500


@app.route('/v1/service/controlTask', methods=['POST'])
def control_task():
    """
    4.1.7.3. 分析任务控制
    Analysis task control
    """
    try:
        data = request.get_json()
        
        analyse_id = data.get('analyseId')
        command = data.get('command')  # 0: stop, 1: start, 2: delete
        
        if not analyse_id or command is None:
            return jsonify({
                'resultCode': '400',
                'resultValue': None,
                'resultHint': '缺少必要参数'
            }), 400
        
        success = False
        if command == 1:  # Start
            success = video_manager.start_stream(analyse_id)
        elif command == 0:  # Stop
            success = video_manager.stop_stream(analyse_id)
        elif command == 2:  # Delete
            success = video_manager.remove_stream(analyse_id)
        
        if success:
            return jsonify({
                'resultCode': '200',
                'resultValue': None,
                'resultHint': 'operation success'
            })
        else:
            return jsonify({
                'resultCode': '404',
                'resultValue': None,
                'resultHint': '任务未找到'
            }), 404
            
    except Exception as e:
        logger.error(f"Error in control task: {e}")
        return jsonify({
            'resultCode': '500',
            'resultValue': None,
            'resultHint': str(e)
        }), 500


@app.route('/v1/service/imageTask', methods=['POST'])
def image_task():
    """
    4.1.7.5. 图片分析任务
    Image analysis task
    """
    try:
        data = request.get_json()
        
        analyse_id = data.get('analyseId')
        alg_code = data.get('algCode')
        image_data = data.get('imageData')
        rule = data.get('rule')
        
        if not analyse_id or not alg_code or not image_data:
            return jsonify({
                'resultCode': '400',
                'resultValue': None,
                'resultHint': '缺少必要参数'
            }), 400
        
        # Check if model exists
        if not model_manager.get_model(alg_code):
            return jsonify({
                'resultCode': '404',
                'resultValue': None,
                'resultHint': f'算法模型未找到: {alg_code}'
            }), 404
        
        # Decode image
        try:
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return jsonify({
                    'resultCode': '400',
                    'resultValue': None,
                    'resultHint': '图片解码失败'
                }), 400
        except Exception as e:
            logger.error(f"Image decode error: {e}")
            return jsonify({
                'resultCode': '400',
                'resultValue': None,
                'resultHint': f'图片解码失败: {e}'
            }), 400
        
        # Extract sensitivity from rule
        sensitivity = 3
        if rule and 'algParams' in rule:
            for param in rule['algParams']:
                if param['key'] == '--sensitivity':
                    try:
                        sensitivity = int(param['value'])
                    except:
                        pass
        
        # Run inference
        result = model_manager.predict(image, alg_code, sensitivity)
        formatted_result = model_manager.format_detection_result(result, alg_code)
        
        # Encode result image
        _, buffer = cv2.imencode('.jpg', image)
        raw_image_data = base64.b64encode(buffer).decode('utf-8')
        
        # Draw bounding boxes on image for OSD
        osd_image = image.copy()
        if result and formatted_result.get('resultDetail'):
            # Draw detection boxes
            for detail in formatted_result['resultDetail']:
                for item in detail.get('resultItems', []):
                    x1, y1 = item['leftTopX'], item['leftTopY']
                    x2, y2 = item['rightBottomX'], item['rightBottomY']
                    # Draw rectangle
                    cv2.rectangle(osd_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Draw label
                    label = f"{detail['resultDesc']}: {item['score']:.1f}%"
                    cv2.putText(osd_image, label, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        _, osd_buffer = cv2.imencode('.jpg', osd_image)
        osd_image_data = base64.b64encode(osd_buffer).decode('utf-8')
        
        return jsonify({
            'resultCode': '200',
            'resultValue': {
                'analyseTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'analyseResults': formatted_result.get('analyseResults', []),
                'rawImageName': f"{analyse_id}_raw.jpg",
                'rawImageData': raw_image_data,
                'osdImageName': f"{analyse_id}_osd.jpg",
                'osdImageData': osd_image_data,
                'resultDetail': formatted_result.get('resultDetail', [])
            },
            'resultHint': None
        })
        
    except Exception as e:
        logger.error(f"Error in image task: {e}")
        return jsonify({
            'resultCode': '500',
            'resultValue': None,
            'resultHint': str(e)
        }), 500


@app.route('/analysis/api/v1/keepAlive', methods=['POST'])
def keep_alive():
    """
    4.1.7.7. 服务保活
    Service keep alive
    """
    try:
        data = request.get_json()
        dev_ip = data.get('devIP')
        dev_port = data.get('devPort')
        
        # Generate or retrieve device ID
        dev_id = f"mengdong_cloud_{dev_ip}_{dev_port}"
        
        return jsonify({
            'resultCode': '200',
            'resultValue': {
                'devId': dev_id
            },
            'resultHint': 'keep alive'
        })
        
    except Exception as e:
        logger.error(f"Error in keep alive: {e}")
        return jsonify({
            'resultCode': '500',
            'resultValue': None,
            'resultHint': str(e)
        }), 500


@app.route('/analysis/api/v1/updateAnalyseID', methods=['POST'])
def update_analyse_id():
    """
    4.1.7.8. 更新分析ID
    Update analysis ID
    """
    try:
        data = request.get_json()
        old_analyse_id = data.get('oldAnalyseId')
        new_analyse_id = data.get('newAnalyseId')
        
        if not old_analyse_id or not new_analyse_id:
            return jsonify({
                'resultCode': '400',
                'resultValue': None,
                'resultHint': '缺少必要参数'
            }), 400
        
        if video_manager.update_analyse_id(old_analyse_id, new_analyse_id):
            return jsonify({
                'resultCode': '200',
                'resultValue': {
                    'newAnalyseId': new_analyse_id
                },
                'resultHint': 'update success'
            })
        else:
            return jsonify({
                'resultCode': '404',
                'resultValue': None,
                'resultHint': '任务未找到或新ID已存在'
            }), 404
            
    except Exception as e:
        logger.error(f"Error updating analyse ID: {e}")
        return jsonify({
            'resultCode': '500',
            'resultValue': None,
            'resultHint': str(e)
        }), 500


@app.route('/status', methods=['GET'])
def get_status():
    """Get service status"""
    try:
        return jsonify({
            'status': 'running',
            'active_streams': video_manager.get_stream_count(),
            'max_streams': model_manager.get_server_config().get('max_video_streams', 100),
            'loaded_models': len(model_manager.models),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MengDong Cloud Analysis Service')
    parser.add_argument('--config', type=str, 
                        default='/workspace/configs/models_config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind to')
    parser.add_argument('--port', type=int, default=22266,
                        help='Port to bind to')
    
    args = parser.parse_args()
    
    # Initialize services
    init_services(args.config)
    
    # Start Flask server
    logger.info(f"Starting server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == '__main__':
    main()

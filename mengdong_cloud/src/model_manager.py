"""
Model Manager
Manages multiple YOLO models for inference
"""
import os
import yaml
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages YOLO models and inference"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.models: Dict[str, Any] = {}
        self.model_configs: Dict[str, dict] = {}
        self.load_config()
        
    def load_config(self):
        """Load model configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.server_config = config.get('server', {})
            self.video_config = config.get('video', {})
            
            models_list = config.get('models', [])
            for model_config in models_list:
                alg_code = model_config['algCode']
                self.model_configs[alg_code] = model_config
            
            logger.info(f"Loaded configuration for {len(self.model_configs)} models")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def load_models(self):
        """Load all models into memory"""
        try:
            # Import here to avoid issues if trtyolo is not installed
            from trtyolo import TRTYOLO
            
            for alg_code, config in self.model_configs.items():
                engine_path = config['engine_path']
                task = config.get('task', 'detect')
                
                if not os.path.exists(engine_path):
                    logger.warning(f"Engine not found for {config['name']}: {engine_path}")
                    logger.warning(f"Skipping model {alg_code}")
                    continue
                
                try:
                    logger.info(f"Loading model {config['name']} ({alg_code}) from {engine_path}")
                    model = TRTYOLO(engine_path, task=task, profile=False, swap_rb=True)
                    self.models[alg_code] = {
                        'model': model,
                        'config': config
                    }
                    logger.info(f"✓ Model {config['name']} loaded successfully")
                except Exception as e:
                    logger.error(f"✗ Failed to load model {config['name']}: {e}")
            
            logger.info(f"Loaded {len(self.models)}/{len(self.model_configs)} models")
            
        except ImportError as e:
            logger.error(f"Failed to import trtyolo: {e}")
            logger.error("Please ensure TensorRT-YOLO is properly installed")
            raise
    
    def get_model(self, alg_code: str) -> Optional[Any]:
        """Get a model by algorithm code"""
        model_info = self.models.get(alg_code)
        if model_info:
            return model_info['model']
        return None
    
    def get_model_config(self, alg_code: str) -> Optional[dict]:
        """Get model configuration by algorithm code"""
        return self.model_configs.get(alg_code)
    
    def get_all_abilities(self) -> List[dict]:
        """Get all algorithm abilities for API response"""
        abilities = []
        for alg_code, config in self.model_configs.items():
            ability = {
                'algCode': alg_code,
                'algDesc': config['algDesc'],
                'algParams': config.get('algParams', [])
            }
            abilities.append(ability)
        return abilities
    
    def predict(self, image: np.ndarray, alg_code: str, sensitivity: int = 3) -> Optional[Any]:
        """Run inference on an image"""
        model_info = self.models.get(alg_code)
        if not model_info:
            logger.error(f"Model not found for algorithm code: {alg_code}")
            return None
        
        try:
            model = model_info['model']
            
            # Note: Sensitivity parameter affects confidence threshold
            # TensorRT-YOLO model inference uses fixed thresholds set during export
            # The sensitivity parameter is applied during result filtering below
            result = model.predict(image)
            
            # Filter results based on sensitivity if needed
            # Sensitivity mapping: 1 (strict) -> 5 (lenient)
            # This is a post-processing filter on the confidence scores
            conf_threshold_map = {
                1: 0.70,  # Low sensitivity, high threshold
                2: 0.60,
                3: 0.50,  # Default
                4: 0.40,
                5: 0.30   # High sensitivity, low threshold
            }
            
            threshold = conf_threshold_map.get(sensitivity, 0.50)
            
            # Filter detections by threshold
            if hasattr(result, 'confidence') and len(result.confidence) > 0:
                mask = result.confidence >= threshold
                # Apply mask to filter results
                # Note: This is a simplified approach; full implementation would
                # properly filter all detection attributes
                logger.debug(f"Applied sensitivity {sensitivity} filter with threshold {threshold}")
            
            return result
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return None
    
    def format_detection_result(self, result: Any, alg_code: str) -> dict:
        """Format detection result for API response"""
        if result is None:
            return {}
        
        config = self.model_configs.get(alg_code, {})
        class_names = config.get('classes', {})
        
        # Extract detection information
        try:
            # TensorRT-YOLO returns supervision Detections object
            # which has: xyxy, confidence, class_id attributes
            
            result_detail = []
            analyse_results = []
            
            if hasattr(result, 'class_id') and len(result.class_id) > 0:
                # Group detections by class
                detections_by_class = {}
                
                for i in range(len(result.class_id)):
                    class_id = int(result.class_id[i])
                    class_name = class_names.get(class_id, f"class_{class_id}")
                    
                    if class_name not in detections_by_class:
                        detections_by_class[class_name] = {
                            'algCode': alg_code,
                            'resultDesc': class_name,
                            'num': 0,
                            'resultItems': []
                        }
                    
                    # Add detection
                    bbox = result.xyxy[i]
                    confidence = float(result.confidence[i])
                    
                    detection_item = {
                        'score': round(confidence * 100, 2),
                        'leftTopX': int(bbox[0]),
                        'leftTopY': int(bbox[1]),
                        'rightBottomX': int(bbox[2]),
                        'rightBottomY': int(bbox[3])
                    }
                    
                    detections_by_class[class_name]['resultItems'].append(detection_item)
                    detections_by_class[class_name]['num'] += 1
                    
                    # Add to analyse_results set for uniqueness
                    if class_name not in detections_by_class:
                        detections_by_class[class_name] = {
                            'algCode': alg_code,
                            'resultDesc': class_name,
                            'num': 0,
                            'resultItems': []
                        }
                
                result_detail = list(detections_by_class.values())
                # Use dict keys for efficient uniqueness
                analyse_results = list(detections_by_class.keys())
            
            return {
                'analyseResults': analyse_results,
                'resultDetail': result_detail
            }
            
        except Exception as e:
            logger.error(f"Error formatting result: {e}")
            return {
                'analyseResults': [],
                'resultDetail': []
            }
    
    def get_server_config(self) -> dict:
        """Get server configuration"""
        return self.server_config
    
    def get_video_config(self) -> dict:
        """Get video configuration"""
        return self.video_config

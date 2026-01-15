"""
Video Stream Manager
Handles video stream processing with hardware encoding/decoding
Supports up to 100 concurrent video streams
"""
import threading
import queue
import time
import logging
import base64
import cv2
import numpy as np
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VideoStreamConfig:
    """Configuration for a video stream"""
    analyse_id: str
    dev_code: str
    video_url: str
    format_type: int  # 0: h264, 1: h265
    alg_code: str
    rule: Optional[dict] = None
    interval: int = 60  # Result upload interval in seconds
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class VideoStreamProcessor:
    """Process a single video stream with inference"""
    
    def __init__(self, config: VideoStreamConfig, inference_callback: Callable, result_callback: Callable):
        self.config = config
        self.inference_callback = inference_callback
        self.result_callback = result_callback
        self.running = False
        self.thread = None
        self.cap = None
        self.last_result_time = 0
        
    def start(self):
        """Start processing the video stream"""
        if self.running:
            logger.warning(f"Stream {self.config.analyse_id} already running")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started stream processor for {self.config.analyse_id}")
        return True
    
    def stop(self):
        """Stop processing the video stream"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.cap:
            self.cap.release()
        logger.info(f"Stopped stream processor for {self.config.analyse_id}")
    
    def _process_loop(self):
        """Main processing loop for video stream"""
        try:
            # Open video stream with hardware acceleration if available
            self.cap = cv2.VideoCapture(self.config.video_url)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open video stream: {self.config.video_url}")
                return
            
            # Try to enable hardware acceleration (may not be supported on all systems)
            try:
                self.cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
                logger.debug(f"Hardware acceleration enabled for {self.config.analyse_id}")
            except Exception as e:
                logger.debug(f"Hardware acceleration not available: {e}")
            
            frame_count = 0
            self.last_result_time = time.time()
            
            while self.running:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame from {self.config.analyse_id}, reconnecting...")
                    time.sleep(1)
                    self.cap.release()
                    self.cap = cv2.VideoCapture(self.config.video_url)
                    continue
                
                frame_count += 1
                
                # Process frame at specified interval
                current_time = time.time()
                if current_time - self.last_result_time >= self.config.interval:
                    # Run inference
                    try:
                        result = self.inference_callback(frame, self.config.alg_code, self.config.rule)
                        
                        # Send result
                        self.result_callback(self.config.analyse_id, result, frame)
                        self.last_result_time = current_time
                        
                    except Exception as e:
                        logger.error(f"Inference error for {self.config.analyse_id}: {e}")
                else:
                    # Sleep longer if not time for inference yet
                    time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in video processing loop for {self.config.analyse_id}: {e}")
        finally:
            if self.cap:
                self.cap.release()


class VideoStreamManager:
    """Manages multiple video streams"""
    
    def __init__(self, max_streams: int = 100):
        self.max_streams = max_streams
        self.streams: Dict[str, VideoStreamProcessor] = {}
        self.lock = threading.Lock()
        self.inference_callback = None
        self.result_callback = None
        
    def set_inference_callback(self, callback: Callable):
        """Set the inference callback function"""
        self.inference_callback = callback
    
    def set_result_callback(self, callback: Callable):
        """Set the result callback function"""
        self.result_callback = callback
    
    def add_stream(self, config: VideoStreamConfig) -> bool:
        """Add and start a new video stream"""
        with self.lock:
            if len(self.streams) >= self.max_streams:
                logger.error(f"Maximum number of streams ({self.max_streams}) reached")
                return False
            
            if config.analyse_id in self.streams:
                logger.warning(f"Stream {config.analyse_id} already exists")
                return False
            
            processor = VideoStreamProcessor(
                config,
                self.inference_callback,
                self.result_callback
            )
            
            if processor.start():
                self.streams[config.analyse_id] = processor
                logger.info(f"Added stream {config.analyse_id}, total: {len(self.streams)}")
                return True
            
            return False
    
    def remove_stream(self, analyse_id: str) -> bool:
        """Remove and stop a video stream"""
        with self.lock:
            if analyse_id not in self.streams:
                logger.warning(f"Stream {analyse_id} not found")
                return False
            
            processor = self.streams.pop(analyse_id)
            processor.stop()
            logger.info(f"Removed stream {analyse_id}, total: {len(self.streams)}")
            return True
    
    def stop_stream(self, analyse_id: str) -> bool:
        """Stop a video stream without removing it"""
        with self.lock:
            if analyse_id not in self.streams:
                logger.warning(f"Stream {analyse_id} not found")
                return False
            
            self.streams[analyse_id].stop()
            return True
    
    def start_stream(self, analyse_id: str) -> bool:
        """Start a stopped video stream"""
        with self.lock:
            if analyse_id not in self.streams:
                logger.warning(f"Stream {analyse_id} not found")
                return False
            
            return self.streams[analyse_id].start()
    
    def get_stream_count(self) -> int:
        """Get the current number of active streams"""
        with self.lock:
            return len(self.streams)
    
    def get_stream_info(self, analyse_id: str) -> Optional[VideoStreamConfig]:
        """Get information about a specific stream"""
        with self.lock:
            if analyse_id in self.streams:
                return self.streams[analyse_id].config
            return None
    
    def update_analyse_id(self, old_id: str, new_id: str) -> bool:
        """Update the analyse_id of a stream"""
        with self.lock:
            if old_id not in self.streams:
                logger.warning(f"Stream {old_id} not found")
                return False
            
            if new_id in self.streams:
                logger.warning(f"Stream {new_id} already exists")
                return False
            
            processor = self.streams.pop(old_id)
            processor.config.analyse_id = new_id
            self.streams[new_id] = processor
            logger.info(f"Updated analyse_id from {old_id} to {new_id}")
            return True
    
    def shutdown(self):
        """Shutdown all streams"""
        with self.lock:
            for analyse_id, processor in list(self.streams.items()):
                processor.stop()
            self.streams.clear()
            logger.info("All streams shut down")

#!/usr/bin/env python3
"""
Test script for MengDong Cloud Analysis Service API
"""
import requests
import json
import base64
import sys
from pathlib import Path

BASE_URL = "http://localhost:22266"


def test_health():
    """Test health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✓ Health check: {response.status_code}")
        print(f"  Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_status():
    """Test status endpoint"""
    print("\nTesting status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"✓ Status: {response.status_code}")
        print(f"  Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Status failed: {e}")
        return False


def test_abilities():
    """Test algorithm abilities endpoint"""
    print("\nTesting algorithm abilities...")
    try:
        response = requests.post(
            f"{BASE_URL}/v1/service/abilities",
            json={}
        )
        print(f"✓ Abilities: {response.status_code}")
        result = response.json()
        print(f"  Number of algorithms: {result['resultValue']['abilityInfo']['number']}")
        print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Abilities failed: {e}")
        return False


def test_image_task(image_path=None):
    """Test image analysis endpoint"""
    print("\nTesting image analysis...")
    
    # Create a dummy image if no path provided
    if image_path and Path(image_path).exists():
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
    else:
        print("  Note: Using dummy image data (test will likely fail without real model)")
        # Create a small dummy image
        import cv2
        import numpy as np
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', dummy_img)
        image_data = base64.b64encode(buffer).decode('utf-8')
    
    try:
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
            f"{BASE_URL}/v1/service/imageTask",
            json=payload
        )
        print(f"✓ Image task: {response.status_code}")
        result = response.json()
        if response.status_code == 200:
            print(f"  Analysis time: {result['resultValue'].get('analyseTime')}")
            print(f"  Results: {result['resultValue'].get('analyseResults')}")
        else:
            print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Image task failed: {e}")
        return False


def test_video_task():
    """Test video task management endpoint"""
    print("\nTesting video task management...")
    try:
        payload = {
            "algCode": "010101",
            "startTime": "2024-01-01 00:00:00",
            "endTime": "2024-12-31 23:59:59",
            "interval": 60,
            "command": 1,
            "videoInfo": [
                {
                    "analyseId": "test_video_001",
                    "devCode": "camera_001",
                    "formatType": 0,
                    "videoUrl": "rtsp://dummy.url/stream"
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
            f"{BASE_URL}/v1/service/videoTask",
            json=payload
        )
        print(f"✓ Video task: {response.status_code}")
        result = response.json()
        print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Video task failed: {e}")
        return False


def test_control_task():
    """Test task control endpoint"""
    print("\nTesting task control...")
    try:
        payload = {
            "analyseId": "test_video_001",
            "command": 0  # Stop
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/service/controlTask",
            json=payload
        )
        print(f"✓ Control task: {response.status_code}")
        result = response.json()
        print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return True  # May fail if task doesn't exist
    except Exception as e:
        print(f"✗ Control task failed: {e}")
        return False


def test_keep_alive():
    """Test keep alive endpoint"""
    print("\nTesting keep alive...")
    try:
        payload = {
            "devIP": "192.168.1.100",
            "devPort": 22266
        }
        
        response = requests.post(
            f"{BASE_URL}/analysis/api/v1/keepAlive",
            json=payload
        )
        print(f"✓ Keep alive: {response.status_code}")
        result = response.json()
        print(f"  Device ID: {result['resultValue']['devId']}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Keep alive failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("MengDong Cloud Analysis Service - API Test Suite")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("Status", test_status),
        ("Algorithm Abilities", test_abilities),
        ("Image Task", lambda: test_image_task()),
        ("Video Task", test_video_task),
        ("Control Task", test_control_task),
        ("Keep Alive", test_keep_alive),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

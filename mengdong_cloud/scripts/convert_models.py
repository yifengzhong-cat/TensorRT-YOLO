#!/usr/bin/env python3
"""
Model Conversion Script: PT -> ONNX -> TensorRT Engine
Converts YOLOv8 models to TensorRT engines for inference
"""
import os
import sys
import yaml
import argparse
from pathlib import Path
import subprocess


def convert_pt_to_onnx(pt_path, onnx_path, imgsz=640, batch_size=1, dynamic=False):
    """Convert PyTorch model to ONNX format"""
    try:
        from ultralytics import YOLO
        
        print(f"Converting {pt_path} to ONNX format...")
        model = YOLO(pt_path)
        
        # Export to ONNX with specific settings
        model.export(
            format='onnx',
            imgsz=imgsz,
            batch=batch_size,
            dynamic=dynamic,
            simplify=True
        )
        
        # The exported file will be in the same directory as pt file
        pt_dir = Path(pt_path).parent
        pt_name = Path(pt_path).stem
        exported_onnx = pt_dir / f"{pt_name}.onnx"
        
        # Move to target location if different
        if exported_onnx != Path(onnx_path):
            os.rename(str(exported_onnx), onnx_path)
            
        print(f"✓ ONNX model saved to {onnx_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to convert {pt_path} to ONNX: {e}")
        return False


def convert_onnx_to_engine(onnx_path, engine_path, fp16=True, batch_size=1, workspace=4096):
    """Convert ONNX model to TensorRT engine"""
    try:
        print(f"Converting {onnx_path} to TensorRT engine...")
        
        cmd = [
            'trtexec',
            f'--onnx={onnx_path}',
            f'--saveEngine={engine_path}',
            f'--workspace={workspace}',
        ]
        
        if fp16:
            cmd.append('--fp16')
        
        # Run trtexec
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ TensorRT engine saved to {engine_path}")
            return True
        else:
            print(f"✗ Failed to convert {onnx_path} to engine:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Failed to convert {onnx_path} to engine: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Convert YOLOv8 models to TensorRT engines')
    parser.add_argument('--config', type=str, default='/workspace/configs/models_config.yaml',
                        help='Path to models configuration file')
    parser.add_argument('--imgsz', type=int, default=640,
                        help='Input image size')
    parser.add_argument('--batch-size', type=int, default=1,
                        help='Batch size for inference')
    parser.add_argument('--fp16', action='store_true', default=True,
                        help='Use FP16 precision')
    parser.add_argument('--workspace', type=int, default=4096,
                        help='TensorRT workspace size in MB')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip conversion if engine already exists')
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    models = config.get('models', [])
    
    print(f"Found {len(models)} models to convert")
    print("=" * 60)
    
    success_count = 0
    for model_config in models:
        model_name = model_config['name']
        pt_path = model_config['pt_path']
        engine_path = model_config['engine_path']
        
        print(f"\nProcessing model: {model_name}")
        print(f"PT path: {pt_path}")
        print(f"Engine path: {engine_path}")
        
        # Check if PT model exists
        if not os.path.exists(pt_path):
            print(f"✗ PT model not found: {pt_path}")
            print(f"  Please place the model file at the specified location")
            continue
        
        # Check if engine already exists
        if args.skip_existing and os.path.exists(engine_path):
            print(f"✓ Engine already exists, skipping: {engine_path}")
            success_count += 1
            continue
        
        # Create intermediate ONNX path
        onnx_path = engine_path.replace('.engine', '.onnx')
        
        # Convert PT to ONNX
        if not convert_pt_to_onnx(pt_path, onnx_path, args.imgsz, args.batch_size):
            continue
        
        # Convert ONNX to TensorRT engine
        if convert_onnx_to_engine(onnx_path, engine_path, args.fp16, args.batch_size, args.workspace):
            success_count += 1
            # Optionally remove ONNX file to save space
            # os.remove(onnx_path)
        
        print("-" * 60)
    
    print(f"\n{'=' * 60}")
    print(f"Conversion complete: {success_count}/{len(models)} models converted successfully")
    print(f"{'=' * 60}")
    
    return success_count == len(models)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

# MengDong Cloud Analysis Service Dockerfile
# Based on NVIDIA TensorRT container with CUDA support

FROM nvcr.io/nvidia/tensorrt:24.12-py3

# Metadata
LABEL maintainer="mengdong_cloud"
LABEL description="MengDong Cloud Analysis Service with TensorRT-YOLO"
LABEL version="1.0.0"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_MODULE_LOADING=LAZY

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    git \
    cmake \
    build-essential \
    libopencv-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    x264 \
    libx264-dev \
    libvpx-dev \
    libssl-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
    torch==2.3.1 \
    torchvision==0.18.1 \
    ultralytics==8.3.0 \
    opencv-python==4.10.0.84 \
    numpy==1.24.3 \
    pyyaml \
    flask \
    flask-cors \
    requests \
    pillow \
    "pybind11[global]"

# Set working directory
WORKDIR /opt/TensorRT-YOLO

# Copy TensorRT-YOLO source code
COPY . /opt/TensorRT-YOLO/

# Build and install TensorRT-YOLO
RUN cmake -S . -B build \
    -D CMAKE_BUILD_TYPE=Release \
    -D BUILD_PYTHON=ON \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build build -j$(nproc) --config Release --target install \
    && python -m build --wheel \
    && pip3 install dist/trtyolo-*.whl \
    && rm -rf build dist

# Create workspace directory structure
WORKDIR /workspace
RUN mkdir -p /workspace/models \
    /workspace/configs \
    /workspace/logs \
    /workspace/scripts

# Copy MengDong Cloud service files
COPY mengdong_cloud/configs/* /workspace/configs/
COPY mengdong_cloud/src/* /workspace/
COPY mengdong_cloud/scripts/* /workspace/scripts/

# Make scripts executable
RUN chmod +x /workspace/scripts/*.py

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "MengDong Cloud Analysis Service"\n\
echo "================================"\n\
echo ""\n\
\n\
# Check if models need to be converted\n\
if [ ! -f "/workspace/models/.converted" ]; then\n\
    echo "Converting models to TensorRT engines..."\n\
    if python3 /workspace/scripts/convert_models.py --config /workspace/configs/models_config.yaml --skip-existing; then\n\
        touch /workspace/models/.converted\n\
        echo "✓ Model conversion complete"\n\
    else\n\
        echo "⚠ Model conversion failed or models not found"\n\
        echo "⚠ Please place .pt model files in /workspace/models/"\n\
        echo "⚠ Service will start but may fail without models"\n\
    fi\n\
    echo ""\n\
fi\n\
\n\
# Start the API server\n\
echo "Starting API server..."\n\
cd /workspace\n\
exec python3 api_server.py --config /workspace/configs/models_config.yaml --host 0.0.0.0 --port 22266\n\
' > /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh

# Expose ports
EXPOSE 22266 8554 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:22266/health || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

#!/bin/bash
# Build script for MengDong Cloud Analysis Service Docker image

set -e

echo "======================================"
echo "MengDong Cloud Docker Build Script"
echo "======================================"
echo ""

# Configuration
IMAGE_NAME="mengdong_cloud"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
DOCKERFILE="mengdong_cloud/docker/Dockerfile"
EXPORT_FILE="mengdong_cloud.tar"

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo "✗ Error: Dockerfile not found at $DOCKERFILE"
    exit 1
fi

# Build Docker image
echo "Building Docker image: $FULL_IMAGE_NAME"
echo "--------------------------------------"
docker build -f "$DOCKERFILE" -t "$FULL_IMAGE_NAME" .

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Docker image built successfully: $FULL_IMAGE_NAME"
    echo ""
else
    echo ""
    echo "✗ Docker build failed"
    exit 1
fi

# Export Docker image to tar file
echo "Exporting Docker image to $EXPORT_FILE"
echo "--------------------------------------"
docker save "$FULL_IMAGE_NAME" -o "$EXPORT_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Docker image exported successfully: $EXPORT_FILE"
    
    # Show file size
    SIZE=$(du -h "$EXPORT_FILE" | cut -f1)
    echo "  File size: $SIZE"
    echo ""
else
    echo ""
    echo "✗ Docker export failed"
    exit 1
fi

# Print deployment instructions
echo "======================================"
echo "Deployment Instructions"
echo "======================================"
echo ""
echo "1. Transfer the $EXPORT_FILE file to the target machine"
echo ""
echo "2. Load the Docker image:"
echo "   docker load -i $EXPORT_FILE"
echo ""
echo "3. Prepare model files:"
echo "   Create a directory for models:"
echo "   mkdir -p models"
echo "   "
echo "   Place your .pt model files in the models directory:"
echo "   - model_mengdong_raa_adjusted.pt"
echo "   - model_mengdong_small_SRL.pt"
echo "   - model_mengdong_tower.pt"
echo "   - model_mengdong_scene_album.pt"
echo ""
echo "4. Run the container:"
echo "   docker run -d \\"
echo "     --name mengdong_cloud \\"
echo "     --gpus all \\"
echo "     -p 22266:22266 \\"
echo "     -p 8554:8554 \\"
echo "     -p 8080:8080 \\"
echo "     -v \$(pwd)/models:/workspace/models \\"
echo "     $FULL_IMAGE_NAME"
echo ""
echo "5. Check service status:"
echo "   curl http://localhost:22266/health"
echo "   curl http://localhost:22266/status"
echo ""
echo "======================================"
echo "Build Complete!"
echo "======================================"

#!/bin/bash
# Start Hidear services with Podman GPU support

set -e

echo "Starting Hidear services..."

# Load environment variables
set -a
source .env
set +a

# Stop and remove existing containers (if any)
echo "Cleaning up existing containers..."
podman rm -f hidear-frontend hidear-celery hidear-backend hidear-redis 2>/dev/null || true

# Create network if it doesn't exist
podman network exists hidear-network || podman network create hidear-network

# Start Redis
echo "Starting Redis..."
podman run -d \
  --name hidear-redis \
  --network hidear-network \
  -p ${REDIS_PORT:-7293}:6379 \
  -v hidear_redis_data:/data \
  --health-cmd "redis-cli ping" \
  --health-interval 5s \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes

# Start Backend
echo "Starting Backend..."
podman run -d \
  --name hidear-backend \
  --network hidear-network \
  --gpus all \
  -e REDIS_URL=redis://hidear-redis:6379/0 \
  -e DATABASE_URL=${DATABASE_URL:-sqlite:///./hidear.db} \
  -e HF_TOKEN=${HF_TOKEN} \
  -e HF_HOME=/app/models \
  -e TRANSFORMERS_CACHE=/app/models \
  -e PORT=${BACKEND_INTERNAL_PORT:-8000} \
  -e MERALION_ENDPOINT_URL=${MERALION_ENDPOINT_URL} \
  -e QWEN_SAGEMAKER_ENDPOINT=${QWEN_SAGEMAKER_ENDPOINT} \
  -e QWENVL_AWS_ACCESS_KEY_ID=${QWENVL_AWS_ACCESS_KEY_ID} \
  -e QWENVL_AWS_SECRET_ACCESS_KEY=${QWENVL_AWS_SECRET_ACCESS_KEY} \
  -e AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-ap-southeast-1} \
  -v ./backend:/app:z \
  -v ./backend/audio_files:/app/audio_files:z \
  -v ./backend/speaker_profiles:/app/speaker_profiles:z \
  -v hidear_huggingface_cache:/app/models:z \
  -p ${BACKEND_PORT:-9427}:${BACKEND_INTERNAL_PORT:-8000} \
  --restart unless-stopped \
  hidear-backend \
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude 'models/*' --reload-exclude '*.pyc' --reload-exclude '__pycache__/*'

# Start Celery Worker
echo "Starting Celery Worker..."
podman run -d \
  --name hidear-celery \
  --network hidear-network \
  --gpus all \
  -e REDIS_URL=redis://hidear-redis:6379/0 \
  -e HF_TOKEN=${HF_TOKEN} \
  -e HF_HOME=/app/models \
  -e TRANSFORMERS_CACHE=/app/models \
  -e MERALION_ENDPOINT_URL=${MERALION_ENDPOINT_URL} \
  -e QWEN_SAGEMAKER_ENDPOINT=${QWEN_SAGEMAKER_ENDPOINT} \
  -e QWENVL_AWS_ACCESS_KEY_ID=${QWENVL_AWS_ACCESS_KEY_ID} \
  -e QWENVL_AWS_SECRET_ACCESS_KEY=${QWENVL_AWS_SECRET_ACCESS_KEY} \
  -e AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-ap-southeast-1} \
  -v ./backend:/app:z \
  -v ./backend/audio_files:/app/audio_files:z \
  -v ./backend/speaker_profiles:/app/speaker_profiles:z \
  -v hidear_huggingface_cache:/app/models:z \
  --restart unless-stopped \
  hidear-celery-worker

# Start Frontend
echo "Starting Frontend..."
podman run -d \
  --name hidear-frontend \
  --network hidear-network \
  -p ${FRONTEND_PORT:-5847}:80 \
  --restart unless-stopped \
  hidear-frontend

echo ""
echo "✅ All services started!"
echo ""
echo "Service URLs:"
echo "  👂 Hidear Frontend: http://localhost:${FRONTEND_PORT:-5847}"
echo "  🔧 Backend API: http://localhost:${BACKEND_PORT:-9427}"
echo ""
echo "Monitor logs:"
echo "  podman logs -f hidear-frontend"
echo "  podman logs -f hidear-backend"
echo "  podman logs -f hidear-celery"
echo ""

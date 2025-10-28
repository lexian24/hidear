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
podman rm -f hidear-frontend hidear-celery hidear-backend hidear-meralion hidear-redis 2>/dev/null || true

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

# Start MERaLiON (with GPU!)
echo "Starting MERaLiON service..."
# Get GPU ID from environment or default to 0
GPU_ID=${GPU_ID:-0}
echo "Using GPU: ${GPU_ID}"

podman run -d \
  --name hidear-meralion \
  --network hidear-network \
  --gpus all \
  -e MERALION_MODEL=${MERALION_MODEL:-MERaLiON/MERaLiON-2-10B} \
  -e MERALION_PORT=${MERALION_INTERNAL_PORT:-8001} \
  -e HF_HOME=/app/models \
  -e TRANSFORMERS_CACHE=/app/models \
  -e HF_TOKEN=${HF_TOKEN} \
  -e CUDA_VISIBLE_DEVICES=${GPU_ID} \
  -e VLLM_GPU_MEMORY_UTILIZATION=${VLLM_GPU_MEMORY_UTILIZATION:-0.90} \
  -e VLLM_MAX_MODEL_LEN=${VLLM_MAX_MODEL_LEN:-8192} \
  -v ./backend/audio_files:/app/audio_files \
  -v hidear_meralion_models:/app/models \
  -p ${MERALION_PORT:-9428}:${MERALION_INTERNAL_PORT:-8001} \
  --restart unless-stopped \
  hidear-meralion

# Wait for MERaLiON to be ready
echo "Waiting for MERaLiON to start..."
sleep 5

# Start Backend
echo "Starting Backend..."
podman run -d \
  --name hidear-backend \
  --network hidear-network \
  -e REDIS_URL=redis://hidear-redis:6379/0 \
  -e MERALION_SERVICE_URL=http://hidear-meralion:${MERALION_INTERNAL_PORT:-8001} \
  -e DATABASE_URL=${DATABASE_URL:-sqlite:///./hidear.db} \
  -e HF_TOKEN=${HF_TOKEN} \
  -e PORT=${BACKEND_INTERNAL_PORT:-8000} \
  -v ./backend:/app:z \
  -v ./backend/audio_files:/app/audio_files:z \
  -v ./backend/speaker_profiles:/app/speaker_profiles:z \
  -p ${BACKEND_PORT:-9427}:${BACKEND_INTERNAL_PORT:-8000} \
  --restart unless-stopped \
  hidear-backend \
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Start Celery Worker
echo "Starting Celery Worker..."
podman run -d \
  --name hidear-celery \
  --network hidear-network \
  -e REDIS_URL=redis://hidear-redis:6379/0 \
  -e MERALION_SERVICE_URL=http://hidear-meralion:${MERALION_INTERNAL_PORT:-8001} \
  -e HF_TOKEN=${HF_TOKEN} \
  -e HF_HOME=/app/models \
  -e TRANSFORMERS_CACHE=/app/models \
  -v ./backend:/app:z \
  -v ./backend/audio_files:/app/audio_files:z \
  -v ./backend/speaker_profiles:/app/speaker_profiles:z \
  -v hidear_celery_models:/app/models:z \
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
echo "  🤖 MERaLiON: http://localhost:${MERALION_PORT:-9428}"
echo ""
echo "Monitor logs:"
echo "  podman logs -f hidear-frontend"
echo "  podman logs -f hidear-meralion"
echo "  podman logs -f hidear-backend"
echo "  podman logs -f hidear-celery"
echo ""

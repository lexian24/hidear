#!/bin/bash
# Start MERaudio services with Podman GPU support

set -e

echo "Starting MERaudio services..."

# Load environment variables
set -a
source .env
set +a

# Stop and remove existing containers (if any)
echo "Cleaning up existing containers..."
podman rm -f meraudio-frontend meraudio-celery meraudio-backend meraudio-meralion meraudio-redis 2>/dev/null || true

# Create network if it doesn't exist
podman network exists meraudio-network || podman network create meraudio-network

# Start Redis
echo "Starting Redis..."
podman run -d \
  --name meraudio-redis \
  --network meraudio-network \
  -p ${REDIS_PORT:-7293}:6379 \
  -v meraudio_redis_data:/data \
  --health-cmd "redis-cli ping" \
  --health-interval 5s \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes

# Start MERaLiON (with GPU!)
echo "Starting MERaLiON service..."
podman run -d \
  --name meraudio-meralion \
  --network meraudio-network \
  --gpus all \
  -e MERALION_MODEL=${MERALION_MODEL:-MERaLiON/MERaLiON-2-10B} \
  -e MERALION_PORT=${MERALION_INTERNAL_PORT:-8001} \
  -e HF_HOME=/app/models \
  -e TRANSFORMERS_CACHE=/app/models \
  -e HF_TOKEN=${HF_TOKEN} \
  -e CUDA_VISIBLE_DEVICES=${GPU_ID:-0} \
  -v ./backend/audio_files:/app/audio_files \
  -v meraudio_meralion_models:/app/models \
  -p ${MERALION_PORT:-9428}:${MERALION_INTERNAL_PORT:-8001} \
  --restart unless-stopped \
  meraudio-meralion

# Wait for MERaLiON to be ready
echo "Waiting for MERaLiON to start..."
sleep 5

# Start Backend
echo "Starting Backend..."
podman run -d \
  --name meraudio-backend \
  --network meraudio-network \
  -e REDIS_URL=redis://meraudio-redis:6379/0 \
  -e MERALION_SERVICE_URL=http://meraudio-meralion:${MERALION_INTERNAL_PORT:-8001} \
  -e DATABASE_URL=${DATABASE_URL:-sqlite:///./meraudio.db} \
  -e HF_TOKEN=${HF_TOKEN} \
  -e PORT=${BACKEND_INTERNAL_PORT:-8000} \
  -v ./backend:/app \
  -v ./backend/audio_files:/app/audio_files \
  -v ./backend/speaker_profiles:/app/speaker_profiles \
  -p ${BACKEND_PORT:-9427}:${BACKEND_INTERNAL_PORT:-8000} \
  --restart unless-stopped \
  meraudio-backend

# Start Celery Worker
echo "Starting Celery Worker..."
podman run -d \
  --name meraudio-celery \
  --network meraudio-network \
  -e REDIS_URL=redis://meraudio-redis:6379/0 \
  -e MERALION_SERVICE_URL=http://meraudio-meralion:${MERALION_INTERNAL_PORT:-8001} \
  -e HF_TOKEN=${HF_TOKEN} \
  -e HF_HOME=/app/models \
  -e TRANSFORMERS_CACHE=/app/models \
  -v ./backend:/app \
  -v ./backend/audio_files:/app/audio_files \
  -v ./backend/speaker_profiles:/app/speaker_profiles \
  -v meraudio_celery_models:/app/models \
  --restart unless-stopped \
  meraudio-celery-worker

# Start Frontend
echo "Starting Frontend..."
podman run -d \
  --name meraudio-frontend \
  --network meraudio-network \
  -p ${FRONTEND_PORT:-5847}:80 \
  --restart unless-stopped \
  meraudio-frontend

echo ""
echo "✅ All services started!"
echo ""
echo "Service URLs:"
echo "  🌐 Frontend: http://localhost:${FRONTEND_PORT:-5847}"
echo "  🔧 Backend API: http://localhost:${BACKEND_PORT:-9427}"
echo "  🤖 MERaLiON: http://localhost:${MERALION_PORT:-9428}"
echo ""
echo "Monitor logs:"
echo "  podman logs -f meraudio-frontend"
echo "  podman logs -f meraudio-meralion"
echo "  podman logs -f meraudio-backend"
echo "  podman logs -f meraudio-celery"
echo ""

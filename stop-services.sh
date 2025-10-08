#!/bin/bash
# Stop MERaudio services

echo "Stopping MERaudio services..."

# Force remove containers (stop + remove)
podman rm -f meraudio-frontend 2>/dev/null || true
podman rm -f meraudio-celery 2>/dev/null || true
podman rm -f meraudio-backend 2>/dev/null || true
podman rm -f meraudio-meralion 2>/dev/null || true
podman rm -f meraudio-redis 2>/dev/null || true

echo "✅ All services stopped and removed"

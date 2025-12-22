#!/bin/bash
# Stop Hidear services

echo "Stopping Hidear services..."

# Force remove containers (stop + remove)
podman rm -f hidear-frontend 2>/dev/null || true
podman rm -f hidear-celery 2>/dev/null || true
podman rm -f hidear-backend 2>/dev/null || true
podman rm -f hidear-redis 2>/dev/null || true

echo "✅ All services stopped and removed"

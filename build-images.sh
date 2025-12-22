#!/bin/bash
# Build all Hidear Docker/Podman images

set -e

echo "============================================"
echo "Building Hidear Images"
echo "============================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Build Frontend
echo -e "${BLUE}[1/3] Building Frontend image...${NC}"
podman build -t hidear-frontend -f frontend/Dockerfile frontend/
echo -e "${GREEN}✅ Frontend image built successfully${NC}"
echo ""

# Build Backend
echo -e "${BLUE}[2/3] Building Backend image...${NC}"
podman build -t hidear-backend -f backend/Dockerfile backend/
echo -e "${GREEN}✅ Backend image built successfully${NC}"
echo ""

# Build Celery Worker
echo -e "${BLUE}[3/3] Building Celery Worker image...${NC}"
podman build -t hidear-celery-worker -f backend/Dockerfile.celery backend/
echo -e "${GREEN}✅ Celery Worker image built successfully${NC}"
echo ""

echo "============================================"
echo -e "${GREEN}All images built successfully!${NC}"
echo "============================================"
echo ""
echo "Image list:"
podman images | grep hidear
echo ""
echo "Next steps:"
echo "  1. Run: ./start-services.sh"
echo "  2. Monitor logs: podman logs -f hidear-backend"
echo ""

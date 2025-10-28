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
echo -e "${BLUE}[1/4] Building Frontend image...${NC}"
podman build -t hidear-frontend -f frontend/Dockerfile frontend/
echo -e "${GREEN}✅ Frontend image built successfully${NC}"
echo ""

# Build Backend
echo -e "${BLUE}[2/4] Building Backend image...${NC}"
podman build -t hidear-backend -f backend/Dockerfile backend/
echo -e "${GREEN}✅ Backend image built successfully${NC}"
echo ""

# Build Celery Worker
echo -e "${BLUE}[3/4] Building Celery Worker image...${NC}"
podman build -t hidear-celery-worker -f backend/Dockerfile.celery backend/
echo -e "${GREEN}✅ Celery Worker image built successfully${NC}"
echo ""

# Build MERaLiON (GPU service)
echo -e "${BLUE}[4/4] Building MERaLiON image (this may take a while)...${NC}"
podman build -t hidear-meralion -f backend/Dockerfile.meralion backend/
echo -e "${GREEN}✅ MERaLiON image built successfully${NC}"
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
echo "  2. Monitor logs: podman logs -f hidear-meralion"
echo ""

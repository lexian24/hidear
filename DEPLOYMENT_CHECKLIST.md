# Hidear Deployment Checklist

Complete this checklist before deploying Hidear to production or sharing with other users.

---

## Pre-Deployment Phase

### ✅ System Requirements
- [ ] Server has Linux OS (Ubuntu 20.04+ recommended) or macOS with Podman
- [ ] Minimum 16GB RAM
- [ ] Minimum 50GB disk space (for models and audio files)
- [ ] NVIDIA GPU with 8GB+ VRAM (optional but recommended)
  - Without GPU: Processing will be slower (CPU fallback)
  - With GPU: Enable with `ENABLE_GPU=true` in `.env`

### ✅ Dependencies
- [ ] **Podman** or Docker installed
  ```bash
  podman --version
  # or
  docker --version
  ```
- [ ] **FFmpeg** installed (for audio conversion)
  ```bash
  ffmpeg -version
  ```
- [ ] **jq** installed (for JSON parsing in scripts)
  ```bash
  jq --version
  ```
- [ ] **HuggingFace token** obtained
  - Sign up at https://huggingface.co
  - Create token at https://huggingface.co/settings/tokens
  - Accept pyannote and MERaLiON model terms

### ✅ Network Ports Available
- [ ] Port 5847 available (Frontend)
- [ ] Port 9427 available (Backend API)
- [ ] Port 9428 available (MERaLiON - internal only)
- [ ] Port 7293 available (Redis - internal only)

Check with:
```bash
netstat -tuln | grep -E '5847|9427|9428|7293'
sudo lsof -i -P -n | grep -E '5847|9427|9428|7293'
```

If ports are in use, change them in `.env`:
```env
FRONTEND_PORT=5848       # Change this
BACKEND_PORT=9430        # Change this
```

---

## Configuration Phase

### ✅ Environment Setup

1. **Set HuggingFace Token**
   ```bash
   cd /path/to/hidear
   nano .env

   # Edit these lines:
   HF_TOKEN=hf_YourActualTokenHere
   HUGGINGFACE_TOKEN=hf_YourActualTokenHere
   ```

2. **Verify Critical Environment Variables**
   ```bash
   # Required
   HF_TOKEN=hf_XXX                           ✓

   # Optional but recommended
   GPU_ID=0                                  # Which GPU to use
   MERALION_MODEL=MERaLiON/MERaLiON-2-10B   # Large model (24GB VRAM)
   # OR
   MERALION_MODEL=MERaLiON/MERaLiON-2-3B    # Small model (8GB VRAM)

   # Database
   DATABASE_URL=sqlite:///./hidear.db        # SQLite (simple, default)
   # OR for production
   DATABASE_URL=postgresql://user:pass@db:5432/hidear
   ```

3. **Choose Model Size**
   - [ ] Small model (3B params, ~8GB VRAM) for shared GPU
     ```env
     MERALION_MODEL=MERaLiON/MERaLiON-2-3B
     VLLM_GPU_MEMORY_UTILIZATION=0.60
     ```
   - [ ] Large model (10B params, ~24GB VRAM) for dedicated GPU
     ```env
     MERALION_MODEL=MERaLiON/MERaLiON-2-10B
     VLLM_GPU_MEMORY_UTILIZATION=0.90
     ```

### ✅ Optional: Set Up Database

For production, use PostgreSQL instead of SQLite:

```bash
# Create PostgreSQL container
podman run -d \
  --name hidear-postgres \
  --network hidear-network \
  -e POSTGRES_PASSWORD=secretpassword \
  -e POSTGRES_DB=hidear \
  -v hidear_postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Update .env
DATABASE_URL=postgresql://postgres:secretpassword@hidear-postgres:5432/hidear
```

---

## Deployment Phase

### ✅ Build Docker Images

Skip this if you're using pre-built images. Otherwise:

```bash
cd /path/to/hidear

# Build all images (this takes 10-20 minutes)
podman-compose build --no-cache

# Or build individually
podman build -f Dockerfile.backend -t hidear-backend .
podman build -f Dockerfile.frontend -t hidear-frontend .
podman build -f Dockerfile.celery -t hidear-celery-worker .
podman build -f Dockerfile.meralion -t hidear-meralion .
```

### ✅ Start Services

```bash
# Ensure .env is configured
cat .env | grep HF_TOKEN    # Should not be empty!

# Make script executable
chmod +x start-services.sh

# Start all services
./start-services.sh

# Verify containers are running
podman ps | grep hidear

# Expected output:
# hidear-frontend (port 5847)
# hidear-backend (port 9427)
# hidear-celery (no external port)
# hidear-meralion (port 9428)
# hidear-redis (no external port)
```

### ✅ Verify Services

1. **Check container health**
   ```bash
   podman inspect hidear-backend --format='{{.State.Running}}'  # Should be true
   podman inspect hidear-meralion --format='{{.State.Running}}'  # Should be true
   ```

2. **Test API**
   ```bash
   curl http://localhost:9427/api/docs    # Should return HTML
   curl http://localhost:9427/api/v1/tasks?limit=1  # Should return JSON
   ```

3. **Test Frontend**
   ```bash
   curl http://localhost:5847    # Should return HTML
   ```

4. **Test MERaLiON loading**
   ```bash
   podman logs hidear-meralion | tail -20
   # Look for "loaded successfully" or "listening on port 8001"
   ```

5. **Wait for model loading** (first time only)
   - MERaLiON downloads and loads the model on first request
   - This can take 5-10 minutes
   - Monitor with:
     ```bash
     podman logs -f hidear-meralion
     ```

---

## Testing Phase

### ✅ Functional Testing

1. **Test Audio Upload**
   ```bash
   # Create test audio (silence for 5 seconds)
   ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 5 -q:a 9 -acodec libmp3lame test.mp3

   # Upload
   curl -X POST "http://localhost:9427/api/v1/analysis/analyze" \
     -F "file=@test.mp3"

   # Should return task_id
   ```

2. **Test Speaker Enrollment**
   ```bash
   curl -X POST "http://localhost:9427/api/v1/persistent-speakers" \
     -F "files=@test.mp3" \
     -F "name=Test Speaker"

   # Should return speaker_id
   ```

3. **Test Web UI**
   - Open `http://your-server:5847` in browser
   - Try uploading audio
   - Try enrolling a speaker

### ✅ Performance Testing

1. **Measure response times**
   ```bash
   # Time a complete analysis
   time curl -X POST "http://localhost:9427/api/v1/analysis/analyze" \
     -F "file=@10second.wav"

   # Typical times:
   # - 30 second audio: 2-3 seconds wall-clock (returns immediately)
   # - Processing: 20-60 seconds (depending on content)
   ```

2. **Monitor resource usage**
   ```bash
   # CPU usage
   podman stats hidear-backend --no-stream
   podman stats hidear-celery --no-stream
   podman stats hidear-meralion --no-stream

   # Disk usage
   du -sh hidear_meralion_models
   du -sh backend/audio_files
   ```

### ✅ Error Handling

Test error scenarios:

```bash
# Invalid file format
curl -X POST "http://localhost:9427/api/v1/analysis/analyze" \
  -F "file=@test.txt"
# Should return 400 Bad Request

# File too large (>50MB)
dd if=/dev/zero bs=1M count=51 of=large.wav
curl -X POST "http://localhost:9427/api/v1/analysis/analyze" \
  -F "file=@large.wav"
# Should return 413 Payload Too Large

# Non-existent task
curl "http://localhost:9427/api/v1/tasks/nonexistent123"
# Should return 404 Not Found
```

---

## Security Phase

### ✅ Firewall Configuration

1. **Allow external access (if needed)**
   ```bash
   sudo ufw allow 5847/tcp    # Frontend
   sudo ufw allow 9427/tcp    # API

   # Do NOT expose 9428 and 7293 (internal services)
   ```

2. **Restrict access if sensitive**
   ```bash
   # Allow only specific IPs
   sudo ufw allow from 192.168.1.100 to any port 5847
   ```

### ✅ HTTPS Configuration

For production, enable HTTPS:

1. **With Nginx reverse proxy**
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /etc/letsencrypt/live/your-domain/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain/privkey.pem;

       location / {
           proxy_pass http://localhost:5847;
       }

       location /api/ {
           proxy_pass http://localhost:9427;
       }
   }
   ```

2. **Update `.env` with HTTPS URLs**
   ```env
   FRONTEND_URL=https://your-domain.com
   API_URL=https://your-domain.com/api
   ```

### ✅ API Key Authentication (Optional)

Add API key requirement to `main.py`:

```python
from fastapi.security import APIKey, APIKeyCookie
from fastapi.exceptions import HTTPException

async def verify_api_key(api_key: str = Header(...)) -> str:
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@router.post("/analysis/analyze")
async def analyze_audio(
    file: UploadFile,
    api_key: str = Depends(verify_api_key)
):
    # Process only if API key is valid
    ...
```

Then add to `.env`:
```env
API_KEY=sk_your_secret_key_here
```

### ✅ Database Backup

```bash
# Daily SQLite backup
cp hidear.db hidear.db.backup.$(date +%Y%m%d)

# Or with cron:
0 2 * * * cd /path/to/hidear && cp hidear.db hidear.db.backup.$(date +\%Y\%m\%d)

# For PostgreSQL:
podman exec hidear-postgres pg_dump -U postgres hidear > backup.sql
```

---

## Monitoring Phase

### ✅ Set Up Logging

1. **Enable detailed logging**
   ```env
   DEBUG=true
   DATABASE_ECHO=true  # Log all SQL queries
   ```

2. **Monitor logs**
   ```bash
   # All services
   podman logs -f hidear-backend
   podman logs -f hidear-celery
   podman logs -f hidear-meralion
   podman logs -f hidear-frontend

   # Or centralized (with log rotation)
   podman logs hidear-backend > logs/backend.log 2>&1 &
   ```

### ✅ Health Checks

Create a monitoring script:

```bash
#!/bin/bash
# health-check.sh

BACKEND="http://localhost:9427"
FRONTEND="http://localhost:5847"

echo "=== Hidear Health Check ==="
echo "Time: $(date)"

# Check containers
echo ""
echo "Container Status:"
podman ps --filter="name=hidear" --format="{{.Names}}\t{{.State}}"

# Check API
echo ""
echo "API Status:"
curl -s "$BACKEND/api/docs" > /dev/null && echo "✅ Backend API" || echo "❌ Backend API"

# Check Frontend
echo ""
echo "Frontend Status:"
curl -s "$FRONTEND" > /dev/null && echo "✅ Frontend" || echo "❌ Frontend"

# Check resources
echo ""
echo "Resource Usage:"
podman stats --no-stream hidear-backend hidear-meralion

# Database status
echo ""
echo "Database:"
if [ -f "hidear.db" ]; then
    SIZE=$(du -h hidear.db | cut -f1)
    echo "SQLite size: $SIZE"
fi
```

Run periodically:
```bash
chmod +x health-check.sh

# Run every 5 minutes
*/5 * * * * /path/to/health-check.sh >> /var/log/hidear-health.log
```

### ✅ Performance Monitoring

Track metrics over time:

```bash
#!/bin/bash
# performance-monitor.sh

while true; do
    echo "$(date +%Y-%m-%d\ %H:%M:%S) - Task count: $(curl -s http://localhost:9427/api/v1/tasks?limit=1 | jq '.total')" >> metrics.log

    BACKEND_MEM=$(podman stats hidear-backend --no-stream | tail -1 | awk '{print $7}')
    CELERY_MEM=$(podman stats hidear-celery --no-stream | tail -1 | awk '{print $7}')
    MERALION_MEM=$(podman stats hidear-meralion --no-stream | tail -1 | awk '{print $7}')

    echo "$(date +%Y-%m-%d\ %H:%M:%S) - Memory: Backend=$BACKEND_MEM Celery=$CELERY_MEM MERaLiON=$MERALION_MEM" >> metrics.log

    sleep 60
done &
```

---

## User Documentation Phase

### ✅ Create User Guides

- [ ] Copy [API_GUIDE.md](./API_GUIDE.md) to documentation folder
- [ ] Copy [QUICK_START.md](./QUICK_START.md) to documentation folder
- [ ] Copy [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md) for developers
- [ ] Create custom README with your server details

### ✅ Share with Users

1. **Provide access instructions**
   ```markdown
   # Hidear Access Instructions

   **Web Interface**: http://your-server.com:5847
   **API Documentation**: http://your-server.com:9427/api/docs
   **API Base URL**: http://your-server.com:9427/api/v1

   For full documentation, see: [API_GUIDE.md](./docs/API_GUIDE.md)
   ```

2. **Set up API keys** (if using authentication)
   - Generate unique keys for each user
   - Document key rotation policy

3. **Create support channel**
   - Email support address
   - Issue tracker (GitHub, Jira, etc.)
   - Chat channel (Slack, Discord, etc.)

---

## Post-Deployment Phase

### ✅ Continuous Updates

```bash
# Weekly: Clean up old completed tasks
curl -X POST "http://localhost:9427/api/v1/tasks/cleanup?days=7"

# Weekly: Check logs for errors
podman logs hidear-backend | grep -i error | tail -20

# Monthly: Backup database
cp hidear.db "backups/hidear.db.$(date +%Y%m%d).backup"
```

### ✅ Scaling for Multiple Users

When adding more concurrent users:

1. **Increase Celery workers**
   ```bash
   # Modify start-services.sh:
   # podman run ... --replicas=3 hidear-celery-worker
   ```

2. **Increase Redis memory**
   ```env
   REDIS_MAXMEMORY=1gb
   ```

3. **Switch to PostgreSQL** (instead of SQLite)
   ```env
   DATABASE_URL=postgresql://user:pass@postgres:5432/hidear
   ```

4. **Add load balancer** (Nginx)
   ```nginx
   upstream backend {
       server backend1:8000;
       server backend2:8000;
   }
   ```

---

## Troubleshooting Guide

### Problem: "Connection refused" when accessing API

**Solution:**
```bash
# Check if backend is running
podman ps | grep hidear-backend

# Check if port is correct
netstat -tuln | grep 9427

# Restart
podman restart hidear-backend

# Check logs
podman logs hidear-backend | tail -30
```

### Problem: Models not loading / Downloads stuck

**Solution:**
```bash
# Check HF token is set
echo $HF_TOKEN  # Should not be empty

# Check download progress
podman logs -f hidear-meralion

# Give it time (first load can take 10+ minutes)
sleep 600 && podman logs hidear-meralion | tail -50
```

### Problem: Out of Memory (OOM)

**Solution:**
```bash
# Check memory usage
podman stats hidear-meralion

# If MERaLiON OOM, use smaller model:
# Edit .env:
MERALION_MODEL=MERaLiON/MERaLiON-2-3B
VLLM_GPU_MEMORY_UTILIZATION=0.50

./stop-services.sh
./start-services.sh
```

### Problem: Slow audio processing

**Solution:**
```bash
# Check Celery queue
podman logs hidear-celery | grep -i queue

# Check if GPU is being used
podman logs hidear-meralion | grep -i cuda

# Check if other processes are consuming resources
podman stats

# If stuck, restart worker:
podman restart hidear-celery
```

---

## Final Verification Checklist

- [ ] All services running (`podman ps`)
- [ ] API responding (`curl http://localhost:9427/api/docs`)
- [ ] Frontend accessible (browser: `http://localhost:5847`)
- [ ] Audio upload works (test with sample audio)
- [ ] Speaker enrollment works
- [ ] Review queue accessible
- [ ] Logs monitored and clean
- [ ] Database backup strategy in place
- [ ] Firewall configured properly
- [ ] HTTPS enabled (if production)
- [ ] Users notified of availability
- [ ] Documentation provided
- [ ] Support contact info shared

---

## Success Criteria

You're ready for users when:

✅ All services are stable (no crashes for 1+ hour)
✅ API responds consistently (<1s response time)
✅ Audio processing completes successfully (first model load done)
✅ No errors in logs
✅ Users can access and use the web interface
✅ API documentation is available
✅ Backups are running

---

**Deployment Complete!** 🚀

Monitor logs regularly and adjust configuration based on actual usage patterns.

For issues, refer to the [QUICK_START.md](./QUICK_START.md) troubleshooting section.

---

**Last Updated**: October 27, 2024

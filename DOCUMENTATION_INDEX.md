# Hidear Documentation Index

Welcome to the Hidear documentation! This index helps you find the right guide for your use case.

---

## Quick Navigation

### 🚀 I want to get started quickly
👉 **Read**: [QUICK_START.md](./QUICK_START.md)

### 📖 I want to understand all API endpoints
👉 **Read**: [API_GUIDE.md](./API_GUIDE.md)

### 🏗️ I want to integrate Hidear into my app
👉 **Read**: [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md)

### 🔧 I want to deploy to production
👉 **Read**: [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

---

## Document Descriptions

### 1. QUICK_START.md
**For**: Users who want immediate results
**Contains**:
- How to deploy services
- How to access the web UI
- Common bash scripts for typical tasks
- Integration code snippets (JavaScript, Python)
- Basic troubleshooting

**Best for**:
- ✅ First-time users
- ✅ Quick testing
- ✅ Copy-paste examples

**Read time**: 10 minutes

---

### 2. API_GUIDE.md
**For**: Developers building on the API
**Contains**:
- Complete endpoint reference
- Request/response examples
- All parameters and status codes
- Integration examples (Python, JavaScript, cURL)
- CORS configuration
- Error handling
- Rate limiting & performance tips

**Best for**:
- ✅ Mobile app developers
- ✅ Web backend developers
- ✅ Anyone building on top of Hidear

**Read time**: 30 minutes

---

### 3. COMPONENT_INTEGRATION.md
**For**: Advanced developers using individual components
**Contains**:
- Transcription-only setup (MERaLiON direct)
- Speaker diarization integration
- Speaker identification integration
- Building custom audio pipelines
- Frontend integration (React components)
- Deployment considerations
- Security & scaling

**Best for**:
- ✅ Advanced integrations
- ✅ Custom pipelines
- ✅ Component reuse
- ✅ Production deployments

**Read time**: 45 minutes

---

### 4. DEPLOYMENT_CHECKLIST.md
**For**: System administrators deploying Hidear
**Contains**:
- System requirements
- Pre-deployment setup
- Configuration options
- Deployment steps
- Testing procedures
- Security hardening
- Monitoring & logging
- Scaling strategies
- Troubleshooting guide

**Best for**:
- ✅ Server setup & deployment
- ✅ Production configuration
- ✅ Team deployment
- ✅ Long-term maintenance

**Read time**: 45 minutes

---

## Use Case Guides

### Use Case 1: "I want to analyze audio files"

**Step 1**: Deploy Hidear
- Follow [QUICK_START.md](./QUICK_START.md) → Deployment section

**Step 2**: Access the web UI
- Open `http://your-server:5847`
- Upload audio files
- View results

✅ **Total time**: 15 minutes

---

### Use Case 2: "I want to build a React app that uses Hidear"

**Step 1**: Deploy Hidear backend
- Follow [QUICK_START.md](./QUICK_START.md) → Deployment section

**Step 2**: Read API documentation
- Review [API_GUIDE.md](./API_GUIDE.md) → Core API Endpoints

**Step 3**: Use React component
- Copy-paste from [QUICK_START.md](./QUICK_START.md) → JavaScript example
- Or read detailed example in [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md) → Part 4

**Step 4**: Handle CORS
- Update backend CORS config if needed
- See [API_GUIDE.md](./API_GUIDE.md) → CORS Configuration

✅ **Total time**: 30 minutes

---

### Use Case 3: "I want to create a Python script using Hidear"

**Step 1**: Deploy Hidear
- Follow [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

**Step 2**: Copy Python integration code
- From [QUICK_START.md](./QUICK_START.md) → Full Workflow example
- Or [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md) → Part 3

**Step 3**: Update server URL
- Replace `localhost` with your server IP

**Step 4**: Run script

✅ **Total time**: 15 minutes

---

### Use Case 4: "I want to deploy Hidear for my team"

**Step 1**: Read full deployment guide
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) from start to finish

**Step 2**: Prepare server
- Install dependencies
- Configure `.env`
- Set up networking

**Step 3**: Deploy
- Run `./start-services.sh`
- Verify services running
- Run health checks

**Step 4**: Provide user documentation
- Share [QUICK_START.md](./QUICK_START.md) with your team
- Share [API_GUIDE.md](./API_GUIDE.md) with developers

**Step 5**: Monitor
- Set up logging
- Create health check script
- Plan backups

✅ **Total time**: 2-4 hours

---

### Use Case 5: "I want to use only the transcription component"

**Option A**: Use REST API (easiest)
- Endpoint: `POST /api/v1/analysis/analyze`
- See [API_GUIDE.md](./API_GUIDE.md) → Audio Analysis section
- Returns full analysis; you can ignore speaker/emotion results

**Option B**: Use direct component
- See [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md) → Part 2, Option A
- Create custom endpoint that calls MERaLiON only
- More complex but more control

✅ **Total time**: 15-45 minutes

---

### Use Case 6: "I want to integrate speaker identification"

**Step 1**: Understand speaker enrollment
- Read [API_GUIDE.md](./API_GUIDE.md) → Speaker Enrollment

**Step 2**: Implement enrollment flow
- Create endpoint to accept audio files
- Call `POST /api/v1/persistent-speakers`
- Store returned speaker ID

**Step 3**: Identify speakers in new audio
- Upload audio normally
- System automatically identifies against enrolled speakers
- Results show matching speakers

**Step 4**: Handle unidentified speakers
- Use review queue: [API_GUIDE.md](./API_GUIDE.md) → Review Queue
- Manual enrollment from queue items

✅ **Total time**: 30 minutes

---

## Quick Reference

### Endpoints by Category

#### Audio Analysis
- `POST /api/v1/analysis/analyze` - Upload and process
- `GET /api/v1/tasks/{id}` - Check progress
- `DELETE /api/v1/tasks/{id}` - Cancel task

#### Speaker Management
- `POST /api/v1/persistent-speakers` - Enroll speaker
- `GET /api/v1/persistent-speakers` - List speakers
- `DELETE /api/v1/persistent-speakers/{id}` - Remove speaker

#### Review Queue
- `GET /api/v1/review-queue` - Get pending reviews
- `POST /api/v1/review-queue/{id}/enroll` - Enroll from queue
- `POST /api/v1/review-queue/{id}/dismiss` - Skip speaker

#### Voice Activity Detection
- `POST /api/v1/vad/start` - Start monitoring
- `POST /api/v1/vad/stop` - Stop monitoring
- `GET /api/v1/vad/status` - Check status

See [API_GUIDE.md](./API_GUIDE.md) for full documentation.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
│         (Web, Mobile, Desktop, CLI, etc.)               │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
   ┌─────────────┐           ┌──────────────┐
   │  Frontend   │           │ Your Backend │
   │  (React)    │           │  (Your Code) │
   │ Port 5847   │           │   Using API  │
   └─────────────┘           └──────────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │   Hidear Backend API   │
           │    FastAPI/Uvicorn     │
           │     Port 9427/8000     │
           └───────────┬───────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐  ┌─────────┐  ┌──────────┐
   │ Celery  │  │ Redis   │  │ Database │
   │ Workers │  │ Queue   │  │ (SQLite) │
   └────┬────┘  └─────────┘  └──────────┘
        │
        ▼
   ┌──────────────────────────────────────┐
   │  ML Services (Async Background Job)  │
   │  - Transcription (MERaLiON)          │
   │  - Diarization (PyAnnote)            │
   │  - Emotion Analysis                  │
   │  - Speaker Identification            │
   └──────────────────────────────────────┘
```

---

## Technology Stack

- **Frontend**: React + TypeScript + CSS
- **Backend**: FastAPI + Python
- **Task Queue**: Celery + Redis
- **Transcription**: MERaLiON (vLLM)
- **Diarization**: PyAnnote v3.0
- **Speaker ID**: Speaker-Encoder
- **Database**: SQLite (or PostgreSQL for production)
- **Deployment**: Podman/Docker containers
- **GPU**: NVIDIA CUDA (optional)

---

## Common Commands

### Deployment
```bash
./start-services.sh          # Start all services
./stop-services.sh           # Stop all services
podman ps                    # List running containers
podman logs hidear-backend   # View backend logs
```

### API Testing
```bash
curl http://localhost:9427/api/docs              # Interactive docs
curl http://localhost:9427/api/v1/persistent-speakers  # List speakers
```

### Monitoring
```bash
podman stats                 # Resource usage
podman logs -f hidear-celery # Follow worker logs
```

### Database
```bash
sqlite3 hidear.db .tables    # SQLite tables
sqlite3 hidear.db "SELECT COUNT(*) FROM speakers;"  # Query
```

---

## Getting Help

### Documentation
- **API Endpoints**: [API_GUIDE.md](./API_GUIDE.md)
- **Quick Examples**: [QUICK_START.md](./QUICK_START.md)
- **Integration**: [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md)
- **Deployment**: [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

### Interactive Docs
- **Swagger UI**: `http://your-server:9427/api/docs`
- **ReDoc**: `http://your-server:9427/api/redoc`

### Troubleshooting
- Check [QUICK_START.md](./QUICK_START.md) → Troubleshooting section
- Check [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) → Troubleshooting Guide
- View logs: `podman logs hidear-backend`

---

## Document Maintenance

These documents were generated on **October 27, 2024** for Hidear v2.0.0.

### Updates
- **Backend API changes**: Update [API_GUIDE.md](./API_GUIDE.md)
- **Deployment changes**: Update [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
- **New features**: Update [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md)
- **Quick examples**: Update [QUICK_START.md](./QUICK_START.md)

---

## Summary

| Document | Audience | Read Time | Best For |
|----------|----------|-----------|----------|
| [QUICK_START.md](./QUICK_START.md) | Everyone | 10 min | Getting started, quick examples |
| [API_GUIDE.md](./API_GUIDE.md) | Developers | 30 min | Building on API |
| [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md) | Advanced Dev | 45 min | Custom integrations, components |
| [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) | DevOps/Admin | 45 min | Production deployment |

---

**Ready to get started?** Pick your use case above and follow the recommended guides! 🚀

---

**Version**: 2.0.0
**Last Updated**: October 27, 2024

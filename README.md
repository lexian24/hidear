# Hidear - AI-Powered Audio Intelligence Platform

An advanced audio analysis platform using **MERaLiON-10B** for transcription and emotion recognition, with speaker diarization, identification, and intelligent speaker enrollment.

## 🎯 Key Features

### 🎤 Audio Processing
- **Multi-modal Transcription**: MERaLiON-10B for accurate speech-to-text
- **Emotion Recognition**: AI-powered emotion detection from audio
- **Speaker Diarization**: Who-spoke-when using pyannote.audio (supports 3+ speakers)
- **Speaker Identification**: Cross-session speaker recognition with speaker embeddings
- **Voice Activity Detection**: Real-time VAD with WebSocket streaming

### 👥 Speaker Management
- **Persistent Speaker Profiles**: Cross-session speaker tracking
- **Flexible Enrollment**: Enroll speakers with just 1 audio file (previously required 2-5)
- **Review Queue System**: Verify and enroll unidentified speakers
- **Audio Segment Extraction**: Extract and use specific segments for enrollment

### ⚡ Performance
- **GPU Acceleration**: CUDA support for MERaLiON-10B
- **Async Processing**: Celery workers for background tasks
- **Real-time Analysis**: WebSocket support for live audio
- **Containerized Deployment**: Podman/Docker with GPU passthrough

## 🚀 Quick Start

### Prerequisites
- **GPU Server** (recommended): NVIDIA GPU with CUDA support
- **Podman** or Docker with GPU support
- **HuggingFace Token** with access to MERaLiON-2-10B model

### 1. Clone and Configure

```bash
cd hidear

# Edit .env and add your HuggingFace token
nano .env
```

See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for detailed configuration.

### 2. Start Services

```bash
# Start all services with GPU support
./start-services.sh
```

Access the application:
- 🌐 **Frontend**: http://localhost:5847
- 🔧 **Backend API**: http://localhost:9427
- 🤖 **MERaLiON**: http://localhost:9428
- 📚 **API Docs**: http://localhost:9427/api/docs

### 3. Stop Services

```bash
./stop-services.sh
```

**New to Hidear?** Start with [QUICK_START.md](./QUICK_START.md) for a 10-minute setup guide.

## 📋 New Feature: Review Queue System

### Problem Solved
**Before**: Users needed 3-5 minutes of continuous audio to enroll a speaker.
**Now**: Enroll speakers using segments from any meeting recording!

### How It Works

1. **Upload Meeting** → System processes and identifies speakers
2. **Auto-Queue** → Unidentified speakers added to review queue
3. **Review & Verify** → Listen to speaker segments
4. **Enroll** → Create speaker profile from verified segments

### Quick Example

```bash
# 1. Check pending reviews
curl http://localhost:9427/api/v1/review-queue?status=pending

# 2. Listen to speaker segments
curl http://localhost:9427/api/v1/review-queue/1/audio -o speaker.wav
afplay speaker.wav  # macOS

# 3. Enroll speaker
curl -X POST http://localhost:9427/api/v1/review-queue/1/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "speaker_name": "Alice Johnson",
    "use_all_segments": true
  }'
```

**📖 Full Guide**: See [REVIEW_QUEUE_QUICKSTART.md](REVIEW_QUEUE_QUICKSTART.md)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│          http://localhost:5847                       │
└─────────────────────────────────────────────────────┘
                        ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────┐
│              Backend API (FastAPI)                   │
│          http://localhost:9427                       │
│  • REST API                                         │
│  • WebSocket for VAD                                │
│  • Task management                                  │
└─────────────────────────────────────────────────────┘
         ↓ Celery                      ↓ HTTP
┌─────────────────────┐      ┌─────────────────────────┐
│   Celery Worker     │      │  MERaLiON Service       │
│  • Diarization      │      │  http://localhost:9428  │
│  • Speaker ID       │      │  • Transcription        │
│  • Audio processing │      │  • Emotion Recognition  │
└─────────────────────┘      │  • GPU Accelerated      │
         ↓                    └─────────────────────────┘
┌─────────────────────┐
│   Redis (Broker)    │
│  • Task queue       │
│  • Caching          │
└─────────────────────┘
```

### Components

- **Frontend**: React TypeScript with real-time audio visualization
- **Backend API**: FastAPI with async support
- **Celery Worker**: Background processing for audio analysis
- **MERaLiON Service**: Dedicated GPU service for MERaLiON-10B model
- **Redis**: Message broker and caching layer

## 📚 API Endpoints

### Audio Analysis
- `POST /api/v1/analysis/analyze` - Upload and analyze audio
- `GET /api/v1/tasks/{task_id}` - Check processing status
- `DELETE /api/v1/tasks/{task_id}` - Cancel task
- `GET /api/v1/tasks` - List all tasks

### Speaker Management
- `GET /api/v1/persistent-speakers` - List enrolled speakers
- `POST /api/v1/persistent-speakers` - Enroll new speaker (now supports 1+ files)
- `DELETE /api/v1/persistent-speakers/{id}` - Delete speaker

### Review Queue
- `GET /api/v1/review-queue` - List pending reviews
- `POST /api/v1/review-queue/{id}/enroll` - Enroll speaker from review
- `POST /api/v1/review-queue/{id}/dismiss` - Skip speaker

### Voice Activity Detection
- `POST /api/v1/vad/start` - Start VAD monitoring
- `POST /api/v1/vad/stop` - Stop VAD monitoring
- `GET /api/v1/vad/status` - Check status
- `POST /api/v1/vad/upload-recording` - Process recording

**Full API Docs**: http://localhost:9427/api/docs

**📖 Complete documentation**: See [API_GUIDE.md](./API_GUIDE.md)

## 🛠️ Technology Stack

### AI Models
- **MERaLiON-2-10B**: Multi-modal LLM for audio (transcription + emotion)
- **Pyannote.audio 3.3**: Speaker diarization
- **SpeechBrain**: Speaker verification and identification
- **Silero VAD**: Voice activity detection

### Backend
- **FastAPI**: Async web framework
- **Celery**: Distributed task queue
- **Redis**: Message broker
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **WebSocket**: Real-time communication

### Infrastructure
- **Podman/Docker**: Containerization
- **CUDA**: GPU acceleration
- **Nginx**: Reverse proxy (in frontend)

## 📁 Project Structure

```
hidear/
├── backend/                    # FastAPI backend
│   ├── routes/                # API endpoints
│   ├── services/              # Business logic
│   ├── tasks/                 # Celery tasks
│   ├── database/              # Database layer
│   ├── schemas/               # Pydantic schemas
│   └── middleware/            # HTTP middleware
├── frontend/                  # React frontend
│   └── src/
│       ├── components/        # React components
│       ├── services/          # API clients
│       └── types/             # TypeScript types
├── .env                       # Environment config
├── start-services.sh          # Start all services
├── stop-services.sh           # Stop all services
├── API_GUIDE.md              # Complete API documentation
├── QUICK_START.md            # Quick start guide
├── COMPONENT_INTEGRATION.md  # Integration guide
├── DEPLOYMENT_CHECKLIST.md   # Deployment guide
└── DOCUMENTATION_INDEX.md    # Documentation index
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# HuggingFace
HF_TOKEN=hf_your_token_here

# Ports
FRONTEND_PORT=5847
BACKEND_PORT=9427
MERALION_PORT=9428
REDIS_PORT=7293

# GPU
GPU_ID=0  # GPU device ID

# Models
MERALION_MODEL=MERaLiON/MERaLiON-2-10B
```

### GPU Configuration

The system automatically uses GPU if available:
- MERaLiON service uses `--gpus all` flag
- Set `GPU_ID` to select specific GPU
- Falls back to CPU if GPU unavailable

## 📖 Documentation

Start here: **[DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)** - Choose your use case!

- **[QUICK_START.md](./QUICK_START.md)**: Get started in 10 minutes
- **[API_GUIDE.md](./API_GUIDE.md)**: Complete REST API reference
- **[COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md)**: Integration guides & examples
- **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)**: Production deployment

## 🧪 Testing

### API Testing

Use the interactive API docs:
```bash
open http://localhost:9427/api/docs
```

Or test with curl:
```bash
# Upload audio
curl -X POST http://localhost:9427/api/v1/analysis/analyze \
  -F "file=@meeting.wav"

# Check task status
curl http://localhost:9427/api/v1/tasks/{task_id}

# List speakers
curl http://localhost:9427/api/v1/persistent-speakers
```

See [QUICK_START.md](./QUICK_START.md) for more examples.

## 🐛 Troubleshooting

### GPU Not Detected
```bash
# Check GPU availability
podman run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### Model Download Issues
- Ensure HF_TOKEN has access to MERaLiON-2-10B
- Check internet connection
- Models cached in volumes: `meraudio_meralion_models`

### Service Won't Start
```bash
# Check logs
podman logs hidear-backend
podman logs hidear-meralion
podman logs hidear-celery

# Check if ports are available
lsof -i :9427  # Backend
lsof -i :9428  # MERaLiON
lsof -i :5847  # Frontend
```

See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for more troubleshooting.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- **MERaLiON Team**: For the amazing multi-modal audio model
- **Pyannote.audio**: For speaker diarization
- **SpeechBrain**: For speaker verification
- **HuggingFace**: For model hosting

## 📞 Support & Documentation

**Start Here**: [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)

**Quick Links**:
- 📖 [QUICK_START.md](./QUICK_START.md) - Get going in 10 minutes
- 🔌 [API_GUIDE.md](./API_GUIDE.md) - Full API reference
- 🏗️ [COMPONENT_INTEGRATION.md](./COMPONENT_INTEGRATION.md) - Integration examples
- 🚀 [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) - Production deployment
- 📊 Interactive Docs: `http://localhost:9427/api/docs`

---

**Built with ❤️ for intelligent audio processing**

**Version**: 2.0.0
**Last Updated**: October 27, 2024

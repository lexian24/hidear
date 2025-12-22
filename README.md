# Hidear - AI-Powered Audio Intelligence Platform

An advanced audio analysis platform using MERaLiON for transcription and emotion recognition, with speaker diarization, identification, and intelligent speaker enrollment.

## 🎯 Key Features

### 🎤 Audio Processing
- **Multi-modal Transcription**: MERaLiON for accurate speech-to-text
- **Emotion Recognition**: MERaLiON for AI-powered emotion detection from audio
- **Speaker Diarization**: Who-spoke-when using pyannote.audio (supports 6 speakers)
- **Speaker Identification**: Cross-session speaker recognition with speaker embeddings
- **Voice Activity Detection**: Real-time VAD with WebSocket streaming

### 👥 Speaker Management
- **Persistent Speaker Profiles**: Cross-session speaker tracking
- **Flexible Enrollment**: Enroll speakers with just 30s audio file 
- **Speaker Activation/Deactivation**: Deactivate speakers instead of deleting them for better data preservation
- **Segment-Based Enrollment**: Select specific segments from meeting recordings for enrollment
- **Review Queue System**: Verify and enroll unidentified speakers from recordings
- **Audio Segment Extraction**: Extract and preview individual segments before enrollment

### ⚡ Performance
- **GPU Acceleration**: CUDA support for MERaLiON-10B
- **Async Processing**: Celery workers for background tasks
- **Real-time Analysis**: WebSocket support for live audio
- **Containerized Deployment**: Podman/Docker with GPU passthrough

## 🚀 Quick Start

### Prerequisites
- **Podman** or Docker
- **HuggingFace Token** for speaker diarization and identification models
- **Remote MERaLiON Endpoint** URL (for transcription and emotion recognition)
- **AWS SageMaker Qwen Endpoint** (for conversation summarization)

### 1. Clone and Configure

```bash
cd hidear

# Edit .env and add your HuggingFace token
nano .env

# Build images using podman
./build-images.sh
```
### 2. Start Services

```bash
# Start all services with GPU support
./start-services.sh
```

Access the application:
- 🌐 **Frontend**: http://localhost:5847
- 🔧 **Backend API**: http://localhost:9427
- 📚 **API Docs**: http://localhost:9427/api/docs

### 3. Stop Services

```bash
./stop-services.sh
```

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
┌─────────────────────┐      ┌─────────────────────────────────┐
│   Celery Worker     │      │     Remote Endpoints            │
│  • Diarization      │      │  • MERaLiON (Transcription)    │
│  • Speaker ID       │      │  • Qwen (AWS SageMaker)        │
│  • Audio processing │      │  • Emotion Recognition         │
└─────────────────────┘      └─────────────────────────────────┘
         ↓
┌─────────────────────┐
│   Redis (Broker)    │
│  • Task queue       │
│  • Caching          │
└─────────────────────┘
```

### Components

- **Frontend**: React TypeScript with real-time audio visualization
- **Backend API**: FastAPI with async support
- **Celery Worker**: Local processing for diarization and speaker identification
- **Remote MERaLiON**: OpenAI-compatible API for transcription and emotion
- **Remote Qwen**: AWS SageMaker for conversation summarization
- **Redis**: Message broker and caching layer

## 📚 API Endpoints

### Audio Analysis
- `POST /api/v1/analysis/analyze` - Upload and analyze audio
- `GET /api/v1/tasks/{task_id}` - Check processing status
- `DELETE /api/v1/tasks/{task_id}` - Cancel task
- `GET /api/v1/tasks` - List all tasks

### Speaker Management
- `GET /api/persistent-speakers` - List all speakers (active & inactive)
- `POST /api/persistent-speakers` - Enroll new speaker (supports 1+ audio files)
- `PATCH /api/persistent-speakers/{id}/toggle-activation` - Toggle speaker activation status
- `DELETE /api/persistent-speakers/{id}` - Permanently delete speaker

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


## 🛠️ Technology Stack

### AI Models
- **MERaLiON** (Remote): Multi-modal LLM for audio (transcription + emotion)
- **Qwen** (Remote AWS SageMaker): LLM for conversation summarization
- **Pyannote.audio**: Speaker diarization (local)
- **SpeechBrain**: Speaker verification and identification (local)
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

### Remote Endpoint Configuration

Configure remote endpoints in .env:
```bash
MERALION_ENDPOINT_URL=http://192.168.140.226:8005/v1
QWEN_SAGEMAKER_ENDPOINT=your-sagemaker-endpoint
QWENVL_AWS_ACCESS_KEY_ID=your-aws-key
QWENVL_AWS_SECRET_ACCESS_KEY=your-aws-secret
```

GPU acceleration is handled by remote services.
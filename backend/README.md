# Meraudio Backend

AI-powered audio analysis backend using MERaLiON-10B for transcription and emotion recognition, with speaker diarization and identification.

## Architecture

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration settings
├── celery_app.py          # Celery worker configuration
├── meralion_worker.py     # MERaLiON service worker
├── init_db.py             # Database initialization
├── routes/                # API endpoints
│   ├── analysis.py        # Audio analysis endpoints
│   ├── vad.py            # Voice activity detection
│   ├── recordings.py     # Recording management
│   ├── speakers.py       # Speaker management
│   ├── persistent_speakers.py  # Persistent speaker profiles
│   ├── tasks.py          # Task status endpoints
│   ├── websocket.py      # WebSocket endpoints
│   └── health.py         # Health check
├── services/             # Core business logic
│   ├── meralion_client.py     # MERaLiON HTTP client
│   ├── meralion_service.py    # MERaLiON model wrapper
│   ├── diarization.py         # Speaker diarization (pyannote)
│   ├── speaker_identification.py  # Speaker ID (SpeechBrain)
│   ├── audio_processor.py     # Audio processing pipeline
│   ├── enhanced_audio_processor.py  # Enhanced pipeline with persistence
│   ├── persistent_speaker_manager.py  # Speaker profile management
│   ├── auto_recorder.py       # Automatic recording
│   └── voice_activity_detection.py  # VAD service
├── tasks/                # Celery tasks
│   └── audio_tasks.py    # Async audio processing tasks
├── database/             # Database layer
│   ├── models.py         # SQLAlchemy models
│   ├── services.py       # Database service layer
│   ├── config.py         # Database configuration
│   └── dependencies.py   # FastAPI dependencies
├── middleware/           # HTTP middleware
│   ├── logging_middleware.py  # Request logging
│   └── error_handler.py      # Global error handling
└── schemas/              # Pydantic schemas
    ├── audio.py          # Audio analysis schemas
    ├── recording.py      # Recording schemas
    ├── speaker.py        # Speaker schemas
    └── common.py         # Common schemas
```

## Features

### Core Capabilities
- **Transcription**: MERaLiON-10B for accurate speech-to-text
- **Emotion Recognition**: MERaLiON-10B for speaker emotion detection
- **Speaker Diarization**: Pyannote.audio for who-spoke-when
- **Speaker Identification**: SpeechBrain for speaker recognition
- **Persistent Speakers**: Cross-session speaker tracking
- **Voice Activity Detection**: Real-time VAD with WebSocket streaming

### API Versions
- **v1**: `/api/v1/*` - Current stable API
- **Legacy**: `/api/*`, `/vad/*` - Backward compatibility

## Technology Stack

### Core Framework
- **FastAPI**: Async web framework
- **Celery**: Distributed task queue
- **Redis**: Message broker and cache
- **SQLAlchemy**: ORM and database

### AI Models
- **MERaLiON-10B**: Multi-modal LLM for audio (transcription + emotion)
- **Pyannote.audio**: Speaker diarization
- **SpeechBrain**: Speaker verification and identification

### Audio Processing
- **librosa**: Audio analysis
- **soundfile**: Audio I/O
- **pydub**: Audio manipulation

## Setup
### Prerequisites
- Python 3.10+
- CUDA 12.4+ (for GPU acceleration)
- HuggingFace account with access to gated models

## Deployment
Quick start:
```bash
# Build images
podman build -t meraudio-backend -f Dockerfile .
podman build -t meraudio-celery-worker -f Dockerfile.celery .
podman build -t meraudio-meralion -f Dockerfile.meralion .
podman build -t meraudio-frontend -f frontend/Dockerfile frontend/
# Start services

```bash
./start-services.sh
```

## Development

### Adding New Routes
1. Create route file in `routes/`
2. Add router to `routes/__init__.py`
3. Include in appropriate version router

### Adding New Services
1. Create service file in `services/`
2. Import in relevant route or task
3. Add tests

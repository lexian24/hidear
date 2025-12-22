# Meraudio Backend

AI-powered audio analysis backend using MERaLiON-10B for transcription and emotion recognition, with speaker diarization and identification.

## Architecture

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration settings
├── celery_app.py          # Celery worker configuration
├── init_db.py             # Database initialization
├── routes/                # API endpoints
│   ├── analysis.py        # Audio analysis endpoints
│   ├── vad.py            # Voice activity detection
│   ├── recordings.py     # Recording management
│   ├── speakers.py       # Speaker management
│   ├── persistent_speakers.py  # Persistent speaker profiles
│   ├── review_queue.py   # Speaker review queue for enrollment
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
    ├── review_queue.py   # Review queue schemas
    └── common.py         # Common schemas
```

## Features

### Core Capabilities
- **Transcription**: Remote MERaLiON for accurate speech-to-text
- **Emotion Recognition**: Remote MERaLiON for speaker emotion detection
- **Summarization**: AWS SageMaker Qwen for conversation analysis
- **Speaker Diarization**: Local Pyannote.audio for who-spoke-when
- **Speaker Identification**: Local SpeechBrain for speaker recognition
- **Persistent Speakers**: Cross-session speaker tracking
- **Review Queue**: Enroll speakers from meeting recordings without dedicated enrollment sessions
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
- **MERaLiON** (remote endpoint): Multi-modal LLM for audio (transcription + emotion)
- **Qwen** (AWS SageMaker): LLM for conversation summarization
- **Pyannote.audio**: Speaker diarization (local)
- **SpeechBrain**: Speaker verification and identification (local)

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
./build-images.sh

# Start services
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

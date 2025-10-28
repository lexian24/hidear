# Hidear API Guide

## Overview

Hidear is a professional audio analysis platform with speaker identification, transcription, and diarization capabilities. This guide explains how to access and use the API endpoints for integrating Hidear components into your applications.

## Service Endpoints

All services are exposed via the ports configured in `.env`:

| Service | URL | Port | Purpose |
|---------|-----|------|---------|
| **Frontend** | `http://your-server:5847` | 5847 | Web UI for full analysis and speaker enrollment |
| **Backend API** | `http://your-server:9427` | 9427 | REST API for audio processing and management |
| **MERaLiON** | `http://your-server:9428` | 9428 | Transcription service (internal) |
| **Redis** | `http://your-server:7293` | 7293 | Message broker (internal, not for direct use) |

### Default Port Configuration

```env
FRONTEND_PORT=5847
BACKEND_PORT=9427
MERALION_PORT=9428
REDIS_PORT=7293
```

If these ports conflict with your system, edit `.env` before running `start-services.sh`.

---

## API Documentation

### Interactive API Docs

Once the backend is running, access the interactive documentation:

- **Swagger UI**: `http://localhost:9427/api/docs`
- **ReDoc**: `http://localhost:9427/api/redoc`
- **OpenAPI Schema**: `http://localhost:9427/api/openapi.json`

---

## Core API Endpoints

### Base URL
All endpoints use the prefix `/api/v1/` for versioning. Legacy paths (without `/api/v1/`) are also supported for backward compatibility.

---

## 1. Audio Analysis

### Upload and Analyze Audio
**`POST /api/v1/analysis/analyze`**

Process an audio file to extract transcription, speaker diarization, and emotion analysis.

**Request:**
```bash
curl -X POST "http://localhost:9427/api/v1/analysis/analyze" \
  -F "file=@meeting.wav"
```

**Response:**
```json
{
  "status": "queued",
  "task_id": "abc123def456",
  "recording_id": 1,
  "filename": "meeting.wav",
  "message": "Audio file uploaded successfully. Processing in background.",
  "poll_url": "/api/tasks/abc123def456"
}
```

**Supported Formats:**
- `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.webm`
- Maximum file size: 50MB
- Audio is automatically converted to 16kHz WAV mono internally

**Response Fields:**
- `task_id`: Use this to poll the processing status
- `recording_id`: Database ID for the recording
- `poll_url`: Endpoint to check task progress

---

### Get Task Status
**`GET /api/v1/tasks/{task_id}`**

Poll the status of an audio processing task.

**Request:**
```bash
curl "http://localhost:9427/api/v1/tasks/abc123def456"
```

**Response:**
```json
{
  "task_id": "abc123def456",
  "status": "completed",
  "progress": 100,
  "result": {
    "transcript": "Hello, how are you?",
    "speakers": [
      {
        "name": "Speaker 1",
        "segments": [
          {
            "start": 0.0,
            "end": 2.5,
            "text": "Hello, how are you?",
            "confidence": 0.95
          }
        ]
      }
    ],
    "emotion_analysis": [
      {
        "speaker": "Speaker 1",
        "emotions": {
          "neutral": 0.6,
          "positive": 0.3,
          "negative": 0.1
        }
      }
    ]
  },
  "error": null,
  "created_at": "2024-10-27T10:30:00",
  "started_at": "2024-10-27T10:30:05",
  "completed_at": "2024-10-27T10:35:30"
}
```

**Status Values:**
- `queued`: Waiting to be processed
- `processing`: Currently being analyzed
- `completed`: Analysis finished successfully
- `failed`: An error occurred during processing
- `cancelled`: Task was manually cancelled

---

### List Recent Tasks
**`GET /api/v1/tasks?limit=50&offset=0&status=completed`**

Get a paginated list of recent processing tasks.

**Parameters:**
- `limit`: Maximum tasks to return (1-100, default: 50)
- `offset`: Skip this many tasks for pagination (default: 0)
- `status`: Filter by status (optional): `queued`, `processing`, `completed`, `failed`, `cancelled`

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "abc123def456",
      "status": "completed",
      "progress": 100,
      "result": { ... },
      "error": null,
      "created_at": "2024-10-27T10:30:00",
      "started_at": "2024-10-27T10:30:05",
      "completed_at": "2024-10-27T10:35:30"
    }
  ],
  "total": 1
}
```

---

### Cancel a Task
**`DELETE /api/v1/tasks/{task_id}`**

Cancel a pending or processing task.

**Request:**
```bash
curl -X DELETE "http://localhost:9427/api/v1/tasks/abc123def456"
```

**Response:**
```json
{
  "status": "cancelled",
  "task_id": "abc123def456",
  "message": "Task cancelled successfully"
}
```

---

## 2. Speaker Enrollment

### Create Persistent Speaker
**`POST /api/v1/persistent-speakers`**

Enroll a new speaker with 1 or more audio files.

**Request:**
```bash
curl -X POST "http://localhost:9427/api/v1/persistent-speakers" \
  -F "files=@speaker1_sample1.wav" \
  -F "files=@speaker1_sample2.wav" \
  -F "name=John Doe"
```

**Response:**
```json
{
  "id": 5,
  "name": "John Doe",
  "embeddings_count": 8,
  "quality_score": 0.92,
  "created_at": "2024-10-27T10:30:00"
}
```

**Requirements:**
- Minimum 1 audio file (previously required 2-5)
- Audio files must be clear speech with minimal background noise
- Supported formats: `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.webm`

**Quality Assessment:**
The system automatically extracts voice segments and evaluates them on:
- Signal-to-Noise Ratio (SNR)
- RMS Energy
- Zero-Crossing Rate (ZCR)
- Speech clarity

---

### List All Persistent Speakers
**`GET /api/v1/persistent-speakers`**

Retrieve all enrolled speakers in the system.

**Request:**
```bash
curl "http://localhost:9427/api/v1/persistent-speakers"
```

**Response:**
```json
{
  "speakers": [
    {
      "id": 5,
      "name": "John Doe",
      "confidence_threshold": 0.65,
      "total_speaking_time": 3600.5,
      "total_segments": 145,
      "total_recordings": 23,
      "embedding_count": 8,
      "first_seen": "2024-10-01T10:30:00",
      "last_seen": "2024-10-27T10:30:00",
      "is_active": true
    }
  ],
  "total": 1
}
```

---

### Delete a Speaker
**`DELETE /api/v1/persistent-speakers/{speaker_id}`**

Deactivate a persistent speaker (soft delete).

**Request:**
```bash
curl -X DELETE "http://localhost:9427/api/v1/persistent-speakers/5"
```

**Response:**
```json
{
  "status": "deleted",
  "speaker_id": "5"
}
```

---

## 3. Voice Activity Detection (VAD)

### Start VAD Monitoring
**`POST /api/v1/vad/start`**

Start automatic voice activity detection on the system audio input.

**Request:**
```bash
curl -X POST "http://localhost:9427/api/v1/vad/start"
```

**Response:**
```json
{
  "status": "started",
  "message": "VAD monitoring started - ready for audio stream"
}
```

---

### Stop VAD Monitoring
**`POST /api/v1/vad/stop`**

Stop automatic voice activity detection.

**Request:**
```bash
curl -X POST "http://localhost:9427/api/v1/vad/stop"
```

**Response:**
```json
{
  "status": "stopped",
  "message": "VAD monitoring stopped"
}
```

---

### Get VAD Status
**`GET /api/v1/vad/status`**

Check the current VAD monitoring status.

**Request:**
```bash
curl "http://localhost:9427/api/v1/vad/status"
```

**Response:**
```json
{
  "is_monitoring": true,
  "status": "recording",
  "current_recording": "2024-10-27_10-30-45.wav"
}
```

---

### Upload VAD Recording
**`POST /api/v1/vad/upload-recording`**

Process a VAD-detected recording using the same pipeline as manual uploads.

**Request:**
```bash
curl -X POST "http://localhost:9427/api/v1/vad/upload-recording" \
  -F "file=@vad_recording.wav"
```

**Response:**
```json
{
  "status": "queued",
  "task_id": "xyz789abc123",
  "recording_id": 2,
  "filename": "vad_recording.wav",
  "message": "VAD recording uploaded successfully. Processing in background.",
  "poll_url": "/api/tasks/xyz789abc123"
}
```

---

## 4. Review Queue

The review queue contains unidentified speakers detected during audio analysis that are awaiting manual review and enrollment.

### Get Review Queue
**`GET /api/v1/review-queue`**

Retrieve pending speaker review items.

**Parameters:**
- `status`: Filter by status (`pending`, `reviewed`, `dismissed`)
- `recording_id`: Filter by specific recording

**Request:**
```bash
curl "http://localhost:9427/api/v1/review-queue?status=pending"
```

**Response:**
```json
{
  "items": [
    {
      "id": 10,
      "recording_id": 5,
      "session_speaker_label": "Speaker_2",
      "suggested_assignments": [
        {"speaker_id": 3, "confidence": 0.45, "speaker_name": "Alice"},
        {"speaker_id": 5, "confidence": 0.32, "speaker_name": "Bob"}
      ],
      "segment_count": 8,
      "total_duration": 120.5,
      "audio_quality": 0.88,
      "priority": 1,
      "status": "pending",
      "created_at": "2024-10-27T10:30:00",
      "resolved_at": null
    }
  ],
  "total": 1,
  "stats": {
    "pending": 5,
    "reviewed": 12,
    "dismissed": 3
  }
}
```

---

### Enroll Speaker from Review
**`POST /api/v1/review-queue/{item_id}/enroll`**

Create a new persistent speaker from a review queue item.

**Request:**
```bash
curl -X POST "http://localhost:9427/api/v1/review-queue/10/enroll" \
  -H "Content-Type: application/json" \
  -d '{"speaker_name": "Unknown Speaker"}'
```

**Response:**
```json
{
  "status": "enrolled",
  "speaker_id": 6,
  "speaker_name": "Unknown Speaker",
  "embeddings_count": 8,
  "quality_score": 0.88,
  "message": "Speaker enrolled successfully"
}
```

---

### Dismiss Review Item
**`POST /api/v1/review-queue/{item_id}/dismiss`**

Mark a review item as dismissed (don't enroll this speaker).

**Request:**
```bash
curl -X POST "http://localhost:9427/api/v1/review-queue/10/dismiss" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Not a real speaker"}'
```

**Response:**
```json
{
  "status": "dismissed",
  "item_id": 10,
  "message": "Review item dismissed successfully"
}
```

---

## 5. Recordings Management

### List All Recordings
**`GET /api/v1/recordings`**

Retrieve all processed recordings.

**Request:**
```bash
curl "http://localhost:9427/api/v1/recordings"
```

**Response:**
```json
{
  "recordings": [
    {
      "id": 1,
      "filename": "upload_2024-10-27_10-30-00.wav",
      "original_filename": "meeting.wav",
      "duration": 600.5,
      "file_size": 19200000,
      "sample_rate": 16000,
      "channels": 1,
      "created_at": "2024-10-27T10:30:00"
    }
  ],
  "total": 1
}
```

---

## Integration Examples

### Example 1: Python - Upload and Poll Results

```python
import requests
import time

BASE_URL = "http://localhost:9427/api/v1"

# Step 1: Upload audio
with open("meeting.wav", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/analysis/analyze",
        files={"file": f}
    )

task_id = response.json()["task_id"]
print(f"Task ID: {task_id}")

# Step 2: Poll until complete
while True:
    status_response = requests.get(f"{BASE_URL}/tasks/{task_id}")
    status = status_response.json()

    if status["status"] == "completed":
        print("Analysis complete!")
        print(f"Transcript: {status['result']['transcript']}")
        break
    elif status["status"] == "failed":
        print(f"Task failed: {status['error']}")
        break
    else:
        print(f"Status: {status['status']} ({status['progress']}%)")
        time.sleep(2)
```

---

### Example 2: JavaScript - Enroll Speaker

```javascript
const BACKEND_URL = "http://localhost:9427/api/v1";

async function enrollSpeaker(audioFiles, speakerName) {
    const formData = new FormData();

    // Add audio files
    for (const file of audioFiles) {
        formData.append("files", file);
    }

    // Add speaker name
    formData.append("name", speakerName);

    // Send request
    const response = await fetch(
        `${BACKEND_URL}/persistent-speakers`,
        {
            method: "POST",
            body: formData
        }
    );

    const result = await response.json();

    if (response.ok) {
        console.log(`Speaker enrolled: ${result.name} (ID: ${result.id})`);
        console.log(`Quality score: ${result.quality_score}`);
        return result;
    } else {
        throw new Error(`Enrollment failed: ${result.detail}`);
    }
}
```

---

### Example 3: cURL - Complete Workflow

```bash
# 1. Enroll a speaker
SPEAKER_ID=$(curl -X POST "http://localhost:9427/api/v1/persistent-speakers" \
  -F "files=@speaker_sample.wav" \
  -F "name=John Doe" | jq -r '.id')

echo "Enrolled speaker: $SPEAKER_ID"

# 2. Upload audio for analysis
TASK_RESPONSE=$(curl -X POST "http://localhost:9427/api/v1/analysis/analyze" \
  -F "file=@meeting.wav")

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
RECORDING_ID=$(echo $TASK_RESPONSE | jq -r '.recording_id')

echo "Task ID: $TASK_ID"
echo "Recording ID: $RECORDING_ID"

# 3. Poll status
while true; do
  STATUS=$(curl "http://localhost:9427/api/v1/tasks/$TASK_ID" | jq -r '.status')

  if [ "$STATUS" = "completed" ]; then
    echo "Analysis complete!"
    curl "http://localhost:9427/api/v1/tasks/$TASK_ID" | jq '.result'
    break
  fi

  echo "Status: $STATUS"
  sleep 2
done
```

---

## Component Integration

### Using Only the Transcription Component

If you want to use **only the MERaLiON transcription** without speaker diarization and emotion analysis, you can:

1. **Option A: Call MERaLiON directly** (internal service, requires being on the same network)
   ```python
   import requests

   meralion_url = "http://localhost:9428"  # Internal port

   response = requests.post(
       f"{meralion_url}/transcribe_segment",
       json={"audio_path": "/app/audio_files/sample.wav"}
   )

   transcript = response.json()["text"]
   ```

2. **Option B: Use the Backend API**
   Create a custom endpoint in the backend that calls the transcription service without diarization.

---

## CORS Configuration

The backend currently allows requests from:
- `http://localhost:3000`
- `http://127.0.0.1:3000`

To allow requests from other domains, modify `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://yourdomain.com",
        "https://app.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid input) |
| 404 | Resource not found |
| 413 | File too large (>50MB) |
| 500 | Server error |

**Error Response Format:**
```json
{
  "detail": "Error message explaining what went wrong"
}
```

---

## Rate Limiting & Performance

- **File Size Limit**: 50MB per file
- **Concurrent Tasks**: Limited by Celery worker configuration
- **Processing Time**: Varies based on audio length and content
  - Average: 1-2 seconds of audio processes in 5-10 seconds

---

## Troubleshooting

### Issue: "File too large" error
**Solution**: Files must be ≤50MB. Split larger files or check `.env` `MAX_FILE_SIZE_MB`.

### Issue: "Connection refused" on port 9427
**Solution**: Verify backend container is running:
```bash
podman logs hidear-backend
podman ps | grep hidear
```

### Issue: Task shows "processing" indefinitely
**Solution**: Check Celery worker logs:
```bash
podman logs hidear-celery
```

### Issue: MERaLiON transcription fails
**Solution**: Ensure MERaLiON service is running:
```bash
podman logs hidear-meralion
```

---

## Performance Tips

1. **Use short audio clips** (< 5 minutes) for faster processing
2. **Batch multiple analyses** rather than sequential requests
3. **Monitor task queue** to avoid overloading the worker
4. **Use persistent speakers** for faster identification (instead of enrolling each time)
5. **Clean up old tasks** periodically:
   ```bash
   curl -X POST "http://localhost:9427/api/v1/tasks/cleanup?days=7"
   ```

---

## Support

For detailed API documentation with interactive examples, visit:
- **Swagger UI**: `http://localhost:9427/api/docs`
- **ReDoc**: `http://localhost:9427/api/redoc`

For issues, check container logs:
```bash
./stop-services.sh
./start-services.sh
podman logs -f hidear-backend
```

---

## Version History

- **v2.0.0** (Current)
  - Speaker enrollment with 1+ files (reduced from 2-5)
  - Enhanced speaker diarization with configurable max_speakers
  - Review queue for unidentified speakers
  - Full transcription + diarization + emotion analysis
  - WebSocket support for real-time updates

---

**Last Updated**: October 27, 2024

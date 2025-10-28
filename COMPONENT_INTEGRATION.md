# Hidear Component Integration Guide

This guide explains how to integrate individual Hidear components into your own applications.

---

## Available Components

Hidear is modular and can be used in several ways:

### 1. **Full Stack** (Web UI + API)
- Use the entire Hidear system via the web interface
- Best for: Complete out-of-the-box audio analysis

### 2. **REST API Only**
- Integrate the API endpoints into your application
- Best for: Mobile apps, web backends, command-line tools

### 3. **Individual Services**
- Use specific components directly (transcription, diarization, etc.)
- Best for: Custom pipelines, specific use cases

---

## Part 1: Using the REST API

### Setup

All components are accessed through the Backend API on port 9427.

```
http://your-server:9427/api/v1/
```

### Key Endpoints by Component

#### Transcription + Diarization + Emotion
```
POST   /analysis/analyze           (upload and process audio)
GET    /tasks/{task_id}            (check progress)
DELETE /tasks/{task_id}            (cancel task)
GET    /tasks                      (list all tasks)
```

#### Speaker Identification
```
POST   /persistent-speakers        (enroll speaker)
GET    /persistent-speakers        (list speakers)
DELETE /persistent-speakers/{id}   (remove speaker)
```

#### Review Queue (for unidentified speakers)
```
GET    /review-queue               (get pending reviews)
POST   /review-queue/{id}/enroll   (enroll from review)
POST   /review-queue/{id}/dismiss  (skip speaker)
```

#### Voice Activity Detection
```
POST   /vad/start                  (start monitoring)
POST   /vad/stop                   (stop monitoring)
GET    /vad/status                 (check status)
POST   /vad/upload-recording       (process recording)
```

### Real-World Example: Meeting Transcription App

```javascript
// meeting-app.js

class MeetingApp {
    constructor(backendUrl = "http://localhost:9427") {
        this.backendUrl = `${backendUrl}/api/v1`;
    }

    async recordMeeting(audioFile) {
        // 1. Upload audio
        const formData = new FormData();
        formData.append("file", audioFile);

        const uploadResp = await fetch(`${this.backendUrl}/analysis/analyze`, {
            method: "POST",
            body: formData
        });

        const { task_id, recording_id } = await uploadResp.json();

        // 2. Poll for results
        const results = await this.waitForResults(task_id);

        // 3. Extract speaker information
        return {
            transcript: results.transcript,
            speakers: results.speakers,
            emotions: results.emotion_analysis,
            recordingId: recording_id
        };
    }

    async waitForResults(taskId, maxWait = 600000) {
        const startTime = Date.now();

        while (Date.now() - startTime < maxWait) {
            const response = await fetch(`${this.backendUrl}/tasks/${taskId}`);
            const task = await response.json();

            if (task.status === "completed") {
                return task.result;
            } else if (task.status === "failed") {
                throw new Error(`Processing failed: ${task.error}`);
            }

            // Wait 2 seconds before next poll
            await new Promise(resolve => setTimeout(resolve, 2000));
        }

        throw new Error("Processing timeout");
    }

    async generateMeetingMinutes(recording) {
        // Combine transcript with speaker info
        const minutes = [];

        for (const speaker of recording.speakers) {
            minutes.push(`\n## ${speaker.name}\n`);

            for (const segment of speaker.segments) {
                const emotion = this.getEmotionFor(speaker.name, recording.emotions);
                minutes.push(`- **${segment.text}** (Emotion: ${emotion})\n`);
            }
        }

        return minutes.join("");
    }

    getEmotionFor(speakerName, emotionAnalysis) {
        const emotion = emotionAnalysis.find(e => e.speaker === speakerName);
        if (!emotion) return "Unknown";

        const emotions = emotion.emotions;
        return Object.entries(emotions)
            .sort(([, a], [, b]) => b - a)[0][0];
    }
}

// Usage
const app = new MeetingApp();
const audioFile = document.getElementById("audioInput").files[0];
const meeting = await app.recordMeeting(audioFile);
const minutes = app.generateMeetingMinutes(meeting);
document.getElementById("minutes").innerHTML = minutes;
```

---

## Part 2: Direct Component Integration

### Option A: Transcription Only (MERaLiON)

If you only want transcription without speaker identification:

#### Method 1: Use Backend API

Create a custom endpoint in `backend/routes/transcription.py`:

```python
from fastapi import APIRouter, File, UploadFile, HTTPException
import requests
import os

router = APIRouter()

@router.post("/transcribe-only")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcription without diarization"""
    try:
        # Save file
        content = await file.read()
        filepath = f"temp_{file.filename}"
        with open(filepath, 'wb') as f:
            f.write(content)

        # Call MERaLiON directly
        meralion_url = os.getenv("MERALION_SERVICE_URL", "http://meralion:8001")

        # Convert path for container
        container_path = f"/app/audio_files/{os.path.basename(filepath)}"

        response = requests.post(
            f"{meralion_url}/transcribe_segment",
            json={"audio_path": container_path}
        )

        transcript = response.json()["text"]

        # Cleanup
        os.unlink(filepath)

        return {
            "transcript": transcript,
            "confidence": response.json().get("confidence", 0.0)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

Then in `routes/__init__.py`:

```python
from .transcription import router as transcription_router
api_v1_router.include_router(transcription_router, prefix="/transcription", tags=["transcription"])
```

Usage:

```bash
curl -X POST "http://localhost:9427/api/v1/transcription/transcribe-only" \
  -F "file=@audio.wav"
```

#### Method 2: Direct MERaLiON Service

If MERaLiON is accessible on your network:

```python
import requests

MERALION_URL = "http://localhost:9428"  # External port

def transcribe(audio_path):
    # For files on the MERaLiON host
    # Path must be accessible from container
    # Usually /app/audio_files/ or /app/recordings/

    response = requests.post(
        f"{MERALION_URL}/transcribe_segment",
        json={"audio_path": audio_path}
    )

    return response.json()["text"]

# Usage
result = transcribe("/app/audio_files/meeting.wav")
print(result)
```

---

### Option B: Speaker Diarization Only

Hidear uses **pyannote.audio** for speaker diarization. Use it directly:

```python
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.speaker_diarization import SpeakerDiarization

# Initialize pipeline
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.0", use_auth_token="YOUR_HF_TOKEN")

# Process audio
diarization = pipeline("meeting.wav", max_speakers=4)

# Access results
for turn, speaker, spk_id in diarization.itertracks(yield_label=True):
    print(f"{speaker} speaks between {turn.start:.1f}s and {turn.end:.1f}s")
```

Or use Hidear's wrapper:

```python
from services.diarization import DiarizationService

diarizer = DiarizationService()
diarization = diarizer.diarize("audio.wav", max_speakers=4)
```

---

### Option C: Speaker Identification

Hidear uses **speaker-encoder** from the TitaNet model family:

```python
from services.speaker_identification import SpeakerIdentifier
from services.persistent_speaker_manager import PersistentSpeakerManager
from database import get_database_service

# Initialize
identifier = SpeakerIdentifier()
db_service = get_database_service()
manager = PersistentSpeakerManager(db_service, identifier)

# Enroll speakers
enrollment = await manager.enroll_speaker_from_files(
    speaker_name="John Doe",
    audio_files=["john_sample1.wav", "john_sample2.wav"]
)

# Identify speaker in new audio
identification = identifier.identify_speaker(
    audio_path="meeting.wav",
    speaker_id=enrollment["speaker_id"]
)

print(f"Confidence: {identification['confidence']:.2%}")
print(f"Speaker: {identification['name']}")
```

---

## Part 3: Building Custom Pipelines

### Example: Extract Meeting Insights

```python
import asyncio
from services.diarization import DiarizationService
from services.meralion_service import MERaLiONService
from services.emotion_analysis import EmotionAnalyzer
from database import get_database_service

class MeetingAnalyzer:
    def __init__(self):
        self.diarizer = DiarizationService()
        self.transcriber = MERaLiONService()
        self.emotion = EmotionAnalyzer()
        self.db = get_database_service()

    async def analyze(self, audio_path, max_speakers=5):
        """Complete meeting analysis"""

        # 1. Diarize speakers
        print("🎤 Identifying speakers...")
        diarization = self.diarizer.diarize(audio_path, max_speakers=max_speakers)

        # 2. Extract segments
        segments = self._extract_segments(audio_path, diarization)

        # 3. Transcribe each segment
        print("📝 Transcribing...")
        for segment in segments:
            transcript = self.transcriber.transcribe_segment(segment['path'])
            segment['text'] = transcript

        # 4. Analyze emotions
        print("😊 Analyzing emotions...")
        for segment in segments:
            if segment['text']:
                emotion = self.emotion.analyze(segment['text'])
                segment['emotion'] = emotion

        # 5. Generate report
        report = self._generate_report(segments)
        return report

    def _extract_segments(self, audio_path, diarization):
        # Extract audio for each speaker
        import librosa
        import soundfile as sf

        y, sr = librosa.load(audio_path, sr=16000)
        segments = []

        for turn, speaker, spk_id in diarization.itertracks(yield_label=True):
            start_sample = int(turn.start * sr)
            end_sample = int(turn.end * sr)

            segment_audio = y[start_sample:end_sample]
            segment_path = f"segment_{spk_id}_{turn.start:.2f}.wav"

            sf.write(segment_path, segment_audio, sr)

            segments.append({
                'speaker_id': spk_id,
                'start': turn.start,
                'end': turn.end,
                'path': segment_path
            })

        return segments

    def _generate_report(self, segments):
        report = {
            'speakers': list(set(s['speaker_id'] for s in segments)),
            'segments': segments,
            'summary': self._summarize_transcript([s['text'] for s in segments if s.get('text')])
        }
        return report

    def _summarize_transcript(self, texts):
        # Use a summarization model (not included, implement as needed)
        return " ".join(texts[:50])  # Simple truncation

# Usage
async def main():
    analyzer = MeetingAnalyzer()
    report = await analyzer.analyze("meeting.wav", max_speakers=4)
    print(report)

asyncio.run(main())
```

---

## Part 4: Frontend Integration

### React Component for Audio Upload

```jsx
import React, { useState } from "react";

const AudioUploader = ({ backendUrl = "http://localhost:9427" }) => {
    const [file, setFile] = useState(null);
    const [taskId, setTaskId] = useState(null);
    const [status, setStatus] = useState(null);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);

    const handleFileSelect = (e) => {
        setFile(e.target.files[0]);
        setError(null);
    };

    const uploadAudio = async () => {
        if (!file) {
            setError("Please select a file");
            return;
        }

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch(
                `${backendUrl}/api/v1/analysis/analyze`,
                { method: "POST", body: formData }
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            const data = await response.json();
            setTaskId(data.task_id);
            setStatus("processing");

            // Start polling
            pollStatus(data.task_id);
        } catch (err) {
            setError(err.message);
        }
    };

    const pollStatus = async (id) => {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(
                    `${backendUrl}/api/v1/tasks/${id}`
                );
                const data = await response.json();

                setStatus(data.status);

                if (data.status === "completed") {
                    setResults(data.result);
                    clearInterval(pollInterval);
                } else if (data.status === "failed") {
                    setError(data.error);
                    clearInterval(pollInterval);
                }
            } catch (err) {
                setError(err.message);
                clearInterval(pollInterval);
            }
        }, 2000);
    };

    return (
        <div className="audio-uploader">
            <h2>Audio Analysis</h2>

            {!results ? (
                <>
                    <input
                        type="file"
                        accept="audio/*"
                        onChange={handleFileSelect}
                    />

                    <button
                        onClick={uploadAudio}
                        disabled={!file || status === "processing"}
                    >
                        {status === "processing" ? "Processing..." : "Upload"}
                    </button>

                    {status === "processing" && (
                        <p>⏳ Processing audio...</p>
                    )}

                    {error && <p style={{ color: "red" }}>{error}</p>}
                </>
            ) : (
                <div className="results">
                    <h3>Results</h3>

                    <section>
                        <h4>Transcript</h4>
                        <p>{results.transcript}</p>
                    </section>

                    <section>
                        <h4>Speakers</h4>
                        {results.speakers.map((speaker, idx) => (
                            <div key={idx}>
                                <strong>{speaker.name}</strong>
                                <ul>
                                    {speaker.segments.map((seg, i) => (
                                        <li key={i}>
                                            {seg.text} ({seg.start.toFixed(1)}s)
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </section>

                    <section>
                        <h4>Emotion Analysis</h4>
                        {results.emotion_analysis?.map((item, idx) => (
                            <div key={idx}>
                                <strong>{item.speaker}</strong>
                                <ul>
                                    {Object.entries(item.emotions).map(
                                        ([emotion, score]) => (
                                            <li key={emotion}>
                                                {emotion}: {(score * 100).toFixed(1)}%
                                            </li>
                                        )
                                    )}
                                </ul>
                            </div>
                        ))}
                    </section>

                    <button onClick={() => setResults(null)}>New Analysis</button>
                </div>
            )}
        </div>
    );
};

export default AudioUploader;
```

---

## Part 5: Deployment Considerations

### Security

1. **CORS Setup**: Update `main.py` to allow your frontend domain
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

2. **Authentication**: Add API key validation
   ```python
   from fastapi.security import APIKey, APIKeyCookie

   @router.post("/analyze")
   async def analyze_audio(
       file: UploadFile,
       api_key: APIKey = Depends(verify_api_key)
   ):
       # Process only if API key is valid
   ```

3. **Rate Limiting**: Add request throttling
   ```bash
   pip install slowapi
   ```

### Scaling

- **Multiple Workers**: Increase Celery worker count
  ```bash
  podman run ... celery -A tasks worker --concurrency=4
  ```

- **Load Balancing**: Use Nginx/HAProxy in front of multiple backends
  ```nginx
  upstream hidear_backend {
      server backend1:8000;
      server backend2:8000;
      server backend3:8000;
  }
  ```

- **Database**: Migrate from SQLite to PostgreSQL
  ```env
  DATABASE_URL=postgresql://user:pass@postgres:5432/hidear
  ```

---

## Part 6: Troubleshooting Integration

### "Connection refused" on API calls

```bash
# Check if backend is running
curl http://localhost:9427/api/docs

# Check ports
netstat -tuln | grep 9427

# Restart backend
podman restart hidear-backend
```

### CORS errors

In browser console: `Access-Control-Allow-Origin` error?

Add your domain to `main.py`:

```python
allow_origins=[
    "http://localhost:3000",
    "https://yourdomain.com",  # Add this
]
```

### Long processing times

Check task status and Celery logs:

```bash
podman logs hidear-celery | tail -50

# Check if worker is busy
curl "http://localhost:9427/api/v1/tasks?limit=1" | jq '.tasks[0]'
```

---

## Conclusion

Hidear is designed to be modular and composable. Choose the integration approach that best fits your use case:

- **Full Web UI** → Use the frontend at port 5847
- **API Integration** → Use REST endpoints at port 9427
- **Custom Pipelines** → Import components directly in Python
- **Hybrid Approach** → Mix and match as needed

For detailed API documentation, visit: `http://localhost:9427/api/docs`

---

**Last Updated**: October 27, 2024

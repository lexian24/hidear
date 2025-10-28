# Hidear Quick Start Guide

## 1. Deploy the Services

### On Your Server

```bash
# Navigate to the hidear directory
cd /path/to/hidear

# Configure environment (edit if needed)
# nano .env

# Start all services
./start-services.sh

# Verify services are running
podman ps | grep hidear
```

**Expected Output:**
```
👂 Hidear Frontend: http://localhost:5847
🔧 Backend API: http://localhost:9427
🤖 MERaLiON: http://localhost:9428
```

### From Another Machine

Replace `localhost` with your server IP/domain:
- Frontend: `http://192.168.1.100:5847`
- API: `http://192.168.1.100:9427`

---

## 2. Access the Web UI

Navigate to `http://your-server:5847` in your browser.

### Enroll a Speaker
1. Click "Speaker Management"
2. Select 1+ audio files (previously required 2-5)
3. Enter speaker name
4. Click "Enroll"
5. Wait for confirmation

### Upload and Analyze Audio
1. Click "Audio Analysis"
2. Select your audio file
3. Click "Upload"
4. Wait for analysis to complete
5. View transcript, speaker identification, and emotion analysis

---

## 3. Use the API Directly

### Quick Test - Check if API is running

```bash
curl http://localhost:9427/api/docs
```

This opens the interactive API documentation in a browser (if available).

---

## 4. Common Tasks

### Task A: Upload Audio and Get Results

```bash
#!/bin/bash

BACKEND="http://localhost:9427"

# Upload
echo "📤 Uploading audio..."
RESPONSE=$(curl -s -X POST "$BACKEND/api/v1/analysis/analyze" \
  -F "file=@meeting.wav")

TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "Task ID: $TASK_ID"

# Poll every 2 seconds
echo "⏳ Processing..."
while true; do
  STATUS=$(curl -s "$BACKEND/api/v1/tasks/$TASK_ID" | jq -r '.status')

  case $STATUS in
    "completed")
      echo "✅ Done!"
      curl -s "$BACKEND/api/v1/tasks/$TASK_ID" | jq '.result'
      break
      ;;
    "failed")
      echo "❌ Failed!"
      curl -s "$BACKEND/api/v1/tasks/$TASK_ID" | jq '.error'
      break
      ;;
    *)
      PROGRESS=$(curl -s "$BACKEND/api/v1/tasks/$TASK_ID" | jq '.progress')
      echo "  Status: $STATUS ($PROGRESS%)"
      sleep 2
      ;;
  esac
done
```

---

### Task B: Enroll Multiple Speakers

```bash
#!/bin/bash

BACKEND="http://localhost:9427"

# Speaker 1: John
echo "Enrolling John..."
curl -s -X POST "$BACKEND/api/v1/persistent-speakers" \
  -F "files=@john_sample1.wav" \
  -F "files=@john_sample2.wav" \
  -F "name=John" | jq

# Speaker 2: Alice
echo "Enrolling Alice..."
curl -s -X POST "$BACKEND/api/v1/persistent-speakers" \
  -F "files=@alice_sample1.wav" \
  -F "files=@alice_sample2.wav" \
  -F "name=Alice" | jq

# List all speakers
echo "Enrolled speakers:"
curl -s "$BACKEND/api/v1/persistent-speakers" | jq '.speakers[] | {id, name}'
```

---

### Task C: Monitor Processing Status

```bash
#!/bin/bash

BACKEND="http://localhost:9427"

# Get recent tasks
echo "Recent tasks:"
curl -s "$BACKEND/api/v1/tasks?limit=10" | jq '.tasks[] | {task_id, status, progress}'

# Get failed tasks
echo "Failed tasks:"
curl -s "$BACKEND/api/v1/tasks?status=failed" | jq '.tasks[] | {task_id, error}'
```

---

### Task D: Handle Review Queue Items

```bash
#!/bin/bash

BACKEND="http://localhost:9427"

# Check pending reviews
echo "Pending reviews:"
curl -s "$BACKEND/api/v1/review-queue?status=pending" | jq '.items[] | {id, session_speaker_label, segment_count}'

# Enroll first pending speaker
ITEM_ID=$(curl -s "$BACKEND/api/v1/review-queue?status=pending" | jq -r '.items[0].id')
echo "Enrolling speaker from review item $ITEM_ID..."

curl -s -X POST "$BACKEND/api/v1/review-queue/$ITEM_ID/enroll" \
  -H "Content-Type: application/json" \
  -d '{"speaker_name": "New Speaker"}' | jq

# Or dismiss it
# curl -s -X POST "$BACKEND/api/v1/review-queue/$ITEM_ID/dismiss" \
#   -H "Content-Type: application/json" \
#   -d '{"reason": "Not a real speaker"}' | jq
```

---

## 5. Integration Code Snippets

### JavaScript/React - Upload Audio

```javascript
const uploadAudio = async (audioFile) => {
    const formData = new FormData();
    formData.append("file", audioFile);

    const response = await fetch(
        "http://localhost:9427/api/v1/analysis/analyze",
        {
            method: "POST",
            body: formData
        }
    );

    const data = await response.json();
    return data.task_id;
};

const pollResults = async (taskId) => {
    let result = null;
    let attempts = 0;
    const maxAttempts = 300; // 5 minutes with 1-second polls

    while (!result && attempts < maxAttempts) {
        const response = await fetch(
            `http://localhost:9427/api/v1/tasks/${taskId}`
        );
        const data = await response.json();

        if (data.status === "completed") {
            result = data.result;
        } else if (data.status === "failed") {
            throw new Error(data.error);
        } else {
            console.log(`Processing: ${data.progress}%`);
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
        }
    }

    if (!result) throw new Error("Task timeout");
    return result;
};

// Usage
const file = document.getElementById("audioInput").files[0];
const taskId = await uploadAudio(file);
const results = await pollResults(taskId);
console.log("Transcript:", results.transcript);
console.log("Speakers:", results.speakers);
```

---

### Python - Enroll Speaker

```python
import requests

def enroll_speaker(audio_files, speaker_name):
    """Enroll a speaker with audio samples"""

    files = []
    for audio_file in audio_files:
        with open(audio_file, 'rb') as f:
            files.append(("files", f.read()))

    response = requests.post(
        "http://localhost:9427/api/v1/persistent-speakers",
        files=files,
        data={"name": speaker_name}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Enrolled {data['name']} (ID: {data['id']})")
        print(f"   Quality: {data['quality_score']:.2%}")
        print(f"   Embeddings: {data['embeddings_count']}")
        return data
    else:
        print(f"❌ Enrollment failed: {response.json()['detail']}")
        return None

# Usage
enroll_speaker(
    ["john_sample1.wav", "john_sample2.wav"],
    "John Doe"
)
```

---

### Python - Full Workflow

```python
import requests
import time

class HidearClient:
    def __init__(self, base_url="http://localhost:9427"):
        self.base_url = f"{base_url}/api/v1"

    def analyze_audio(self, file_path, timeout=600):
        """Upload and analyze audio"""
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/analysis/analyze",
                files={"file": f}
            )

        task_id = response.json()["task_id"]
        return self.wait_for_task(task_id, timeout)

    def wait_for_task(self, task_id, timeout=600):
        """Wait for task to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = requests.get(f"{self.base_url}/tasks/{task_id}")
            task = response.json()

            if task["status"] == "completed":
                return task["result"]
            elif task["status"] == "failed":
                raise Exception(f"Task failed: {task['error']}")

            time.sleep(2)

        raise TimeoutError("Task did not complete within timeout")

    def enroll_speaker(self, name, audio_files):
        """Enroll a persistent speaker"""
        files = [("files", open(f, 'rb')) for f in audio_files]

        response = requests.post(
            f"{self.base_url}/persistent-speakers",
            files=files,
            data={"name": name}
        )

        for _, f in files:
            f.close()

        return response.json()

    def get_speakers(self):
        """Get all enrolled speakers"""
        response = requests.get(f"{self.base_url}/persistent-speakers")
        return response.json()["speakers"]

# Usage
client = HidearClient()

# Analyze audio
results = client.analyze_audio("meeting.wav")
print(f"Transcript: {results['transcript']}")
print(f"Speakers: {len(results['speakers'])}")

# Enroll speakers
speaker = client.enroll_speaker("John", ["john1.wav", "john2.wav"])
print(f"Enrolled: {speaker['name']}")

# List speakers
for speaker in client.get_speakers():
    print(f"  - {speaker['name']}: {speaker['embedding_count']} embeddings")
```

---

## 6. Troubleshooting

### Backend not responding

```bash
# Check if container is running
podman ps | grep hidear-backend

# View logs
podman logs hidear-backend

# Restart
podman stop hidear-backend
podman start hidear-backend
```

### Port already in use

```bash
# Find what's using the port
lsof -i :9427

# Change port in .env and restart
# BACKEND_PORT=9428
./stop-services.sh
./start-services.sh
```

### Audio file format issues

All formats are supported (`.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.webm`), but internally converted to 16kHz WAV mono.

If you have issues with specific formats, pre-convert with FFmpeg:

```bash
ffmpeg -i input.m4a -acodec pcm_s16le -ar 16000 -ac 1 output.wav
```

### Slow processing

Check Celery worker status:

```bash
podman logs hidear-celery

# If stuck, restart worker
podman restart hidear-celery
```

---

## 7. Advanced Configuration

### Change Default Ports

Edit `.env` before running `start-services.sh`:

```env
FRONTEND_PORT=5847      # Change this
BACKEND_PORT=9427       # Change this
MERALION_PORT=9428      # Change this
REDIS_PORT=7293         # Change this
```

Then restart:

```bash
./stop-services.sh
./start-services.sh
```

### Adjust GPU Usage

```env
# GPU to use (0, 1, 2, 3)
GPU_ID=2

# Memory utilization (0.5-0.95)
# Lower = shared GPU friendly, Higher = faster processing
VLLM_GPU_MEMORY_UTILIZATION=0.70

# Maximum sequence length (reduce if OOM errors)
VLLM_MAX_MODEL_LEN=8192
```

### Database

Default is SQLite (`hidear.db`). To use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@postgres:5432/hidear
```

---

## 8. Next Steps

- Read the full [API Guide](./API_GUIDE.md)
- Access interactive docs at `http://localhost:9427/api/docs`
- Check out integration examples in individual sections above
- Monitor container logs for debugging

---

**Questions?** Check the logs:
```bash
podman logs -f hidear-backend
podman logs -f hidear-celery
podman logs -f hidear-meralion
```

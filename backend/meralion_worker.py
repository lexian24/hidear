"""
Standalone MERaLiON Worker Service
Runs in separate Docker container with specific dependencies
Provides HTTP API for transcription and emotion recognition
"""
import os
import sys
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import numpy as np
import base64
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import MERaLiON service
sys.path.append(os.path.dirname(__file__))
from services.meralion_service import MERaLiONService

# Initialize FastAPI app
app = FastAPI(
    title="MERaLiON Worker",
    description="Standalone service for MERaLiON-10B transcription and emotion recognition",
    version="1.0.0"
)

# Global MERaLiON instance (loaded once at startup)
meralion_service: Optional[MERaLiONService] = None


# Request/Response models
class TranscribeRequest(BaseModel):
    audio_path: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class TranscribeArrayRequest(BaseModel):
    audio_data: str  # Base64 encoded numpy array
    sample_rate: int = 16000


class EmotionRequest(BaseModel):
    audio_path: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class TranscribeResponse(BaseModel):
    text: str
    success: bool = True


class EmotionResponse(BaseModel):
    emotion: str
    confidence: float
    success: bool = True


class InfoResponse(BaseModel):
    service: str
    model: str
    capabilities: list
    loaded: bool
    dtype: str
    backend: str


@app.on_event("startup")
async def startup_event():
    """Load MERaLiON model on startup"""
    global meralion_service

    logger.info("=" * 60)
    logger.info("Starting MERaLiON Worker Service")
    logger.info("=" * 60)

    # Get model name from environment
    model_name = os.getenv("MERALION_MODEL", "MERaLiON/MERaLiON-2-10B")
    logger.info(f"Loading model: {model_name}")

    try:
        meralion_service = MERaLiONService(model_name=model_name)
        logger.info("✅ MERaLiON service ready")
    except Exception as e:
        logger.error(f"❌ Failed to load MERaLiON: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if meralion_service is None or meralion_service.llm is None:
        raise HTTPException(status_code=503, detail="MERaLiON service not loaded")

    return {
        "status": "healthy",
        "service": "meralion-worker",
        "model_loaded": True
    }


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest):
    """
    Transcribe audio segment

    Args:
        request: TranscribeRequest with audio_path and optional time range

    Returns:
        TranscribeResponse with transcribed text
    """
    if meralion_service is None:
        raise HTTPException(status_code=503, detail="MERaLiON service not loaded")

    try:
        logger.info(f"Transcribing: {request.audio_path} "
                   f"[{request.start_time}s - {request.end_time}s]")

        text = meralion_service.transcribe_segment(
            audio_path=request.audio_path,
            start_time=request.start_time,
            end_time=request.end_time
        )

        return TranscribeResponse(text=text, success=True)

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.post("/emotion", response_model=EmotionResponse)
async def predict_emotion(request: EmotionRequest):
    """
    Predict emotion from audio segment

    Args:
        request: EmotionRequest with audio_path and optional time range

    Returns:
        EmotionResponse with emotion label and confidence
    """
    if meralion_service is None:
        raise HTTPException(status_code=503, detail="MERaLiON service not loaded")

    try:
        logger.info(f"Predicting emotion: {request.audio_path} "
                   f"[{request.start_time}s - {request.end_time}s]")

        emotion, confidence = meralion_service.predict_emotion(
            audio_path=request.audio_path,
            start_time=request.start_time,
            end_time=request.end_time
        )

        return EmotionResponse(emotion=emotion, confidence=confidence, success=True)

    except Exception as e:
        logger.error(f"Emotion prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emotion prediction failed: {str(e)}")


@app.post("/transcribe_array", response_model=TranscribeResponse)
async def transcribe_array(request: TranscribeArrayRequest):
    """
    Transcribe audio from numpy array

    Args:
        request: TranscribeArrayRequest with base64-encoded audio data

    Returns:
        TranscribeResponse with transcribed text
    """
    if meralion_service is None:
        raise HTTPException(status_code=503, detail="MERaLiON service not loaded")

    try:
        # Decode base64 audio data
        audio_bytes = base64.b64decode(request.audio_data)
        buffer = io.BytesIO(audio_bytes)
        audio_array = np.load(buffer)

        logger.info(f"Transcribing array: shape={audio_array.shape}, sr={request.sample_rate}")

        text = meralion_service.transcribe_audio_array(
            audio_data=audio_array,
            sample_rate=request.sample_rate
        )

        return TranscribeResponse(text=text, success=True)

    except Exception as e:
        logger.error(f"Array transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Array transcription failed: {str(e)}")


@app.get("/info", response_model=InfoResponse)
async def get_info():
    """Get model information"""
    if meralion_service is None:
        raise HTTPException(status_code=503, detail="MERaLiON service not loaded")

    info = meralion_service.get_info()
    return InfoResponse(**info)


if __name__ == "__main__":
    import uvicorn

    # Get port from environment
    port = int(os.getenv("MERALION_PORT", "8001"))

    logger.info(f"Starting MERaLiON worker on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

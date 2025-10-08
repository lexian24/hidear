"""
HTTP Client for MERaLiON Service
Used by Celery worker to call MERaLiON service in separate container
"""
import os
import requests
import logging
import numpy as np
from typing import Tuple, Dict, Any
import base64
import io

logger = logging.getLogger(__name__)


class MERaLiONClient:
    """
    HTTP client for MERaLiON service
    Provides same interface as MERaLiONService but calls HTTP endpoint
    """

    def __init__(self, base_url: str = None):
        """
        Initialize MERaLiON client

        Args:
            base_url: URL of MERaLiON service (default: http://meralion:8001)
        """
        self.base_url = base_url or os.getenv("MERALION_SERVICE_URL", "http://meralion:8001")
        logger.info(f"MERaLiON client configured for: {self.base_url}")

        # Test connection
        self._check_connection()

    def _check_connection(self):
        """Check if MERaLiON service is available"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Connected to MERaLiON service")
            else:
                logger.warning(f"MERaLiON service returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Cannot connect to MERaLiON service: {e}")

    def transcribe_segment(
        self,
        audio_path: str,
        start_time: float = None,
        end_time: float = None
    ) -> str:
        """
        Transcribe audio segment via HTTP call

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (None = full file)
            end_time: End time in seconds (None = full file)

        Returns:
            Transcribed text
        """
        try:
            # Prepare request payload
            payload = {
                "audio_path": audio_path,
            }

            if start_time is not None:
                payload["start_time"] = start_time
            if end_time is not None:
                payload["end_time"] = end_time

            # Call transcription endpoint
            response = requests.post(
                f"{self.base_url}/transcribe",
                json=payload,
                timeout=60  # Transcription can take time
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "")
                logger.debug(f"Transcribed segment: {text[:50]}...")
                return text
            else:
                logger.error(f"Transcription failed: {response.status_code} - {response.text}")
                return "[transcription failed]"

        except Exception as e:
            logger.error(f"Transcription request failed: {e}")
            return "[transcription failed]"

    def predict_emotion(
        self,
        audio_path: str,
        start_time: float = None,
        end_time: float = None
    ) -> Tuple[str, float]:
        """
        Predict emotion via HTTP call

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (None = full file)
            end_time: End time in seconds (None = full file)

        Returns:
            (emotion, confidence) tuple
        """
        try:
            # Prepare request payload
            payload = {
                "audio_path": audio_path,
            }

            if start_time is not None:
                payload["start_time"] = start_time
            if end_time is not None:
                payload["end_time"] = end_time

            # Call emotion endpoint
            response = requests.post(
                f"{self.base_url}/emotion",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                emotion = result.get("emotion", "neutral")
                confidence = result.get("confidence", 0.5)
                logger.debug(f"Predicted emotion: {emotion} ({confidence:.2f})")
                return emotion, confidence
            else:
                logger.error(f"Emotion prediction failed: {response.status_code} - {response.text}")
                return "neutral", 0.5

        except Exception as e:
            logger.error(f"Emotion request failed: {e}")
            return "neutral", 0.5

    def transcribe_audio_array(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio array via HTTP call

        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate of the audio

        Returns:
            Transcribed text
        """
        try:
            # Convert numpy array to base64 for transmission
            buffer = io.BytesIO()
            np.save(buffer, audio_data)
            buffer.seek(0)
            audio_b64 = base64.b64encode(buffer.read()).decode('utf-8')

            # Prepare request payload
            payload = {
                "audio_data": audio_b64,
                "sample_rate": sample_rate
            }

            # Call array transcription endpoint
            response = requests.post(
                f"{self.base_url}/transcribe_array",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("text", "")
            else:
                logger.error(f"Array transcription failed: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"Array transcription request failed: {e}")
            return ""

    def get_info(self) -> Dict[str, Any]:
        """Get model information via HTTP call"""
        try:
            response = requests.get(f"{self.base_url}/info", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Cannot fetch info"}
        except Exception as e:
            logger.error(f"Info request failed: {e}")
            return {"error": str(e)}

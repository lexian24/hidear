"""
OpenAI SDK Client for Remote MERaLiON Service
Calls OpenAI-compatible remote MERaLiON endpoint via OpenAI Python SDK
Configured via MERALION_ENDPOINT_URL environment variable

Uses base64-encoded audio for proper remote endpoint support.
"""
import os
import re
import logging
import base64
import json
import numpy as np
from typing import Tuple, Dict, Any, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class MERaLiONClient:
    """
    OpenAI SDK client for remote OpenAI-compatible MERaLiON endpoint.
    Handles transcription, emotion recognition, and summarization via OpenAI API.
    Requires MERALION_ENDPOINT_URL environment variable to be set.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize MERaLiON client

        Args:
            base_url: URL of remote MERaLiON service (OpenAI-compatible API)
        """
        # Use MERALION_ENDPOINT_URL for remote endpoint (e.g., http://192.168.140.226:8005/v1)
        self.base_url = base_url or os.getenv("MERALION_ENDPOINT_URL")

        if not self.base_url:
            raise ValueError(
                "MERALION_ENDPOINT_URL environment variable not set. "
                "Please configure the remote MERaLiON endpoint URL."
            )

        logger.info(f"MERaLiON client configured for: {self.base_url}")

        # Initialize OpenAI client with custom base_url
        self.client = OpenAI(
            api_key="EMPTY",  # No authentication needed for internal endpoints
            base_url=self.base_url,
        )

        # Test connection
        self._check_connection()

    def _check_connection(self):
        """Check if MERaLiON service is available"""
        try:
            models = self.client.models.list()
            available_models = [model.id for model in models.data]
            logger.info(f"✅ Connected to MERaLiON service")
            logger.info(f"   Available models: {available_models}")
        except Exception as e:
            logger.warning(f"Cannot connect to MERaLiON service: {e}")

    def _extract_audio_segment(self, audio_path: str, start_time: float = None, end_time: float = None) -> bytes:
        """
        Extract audio segment from file (in seconds).

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (None = from beginning)
            end_time: End time in seconds (None = to end)

        Returns:
            Audio bytes for the segment
        """
        try:
            import librosa
            import soundfile as sf

            # Load audio
            y, sr = librosa.load(audio_path, sr=None)

            # Calculate sample indices
            start_sample = int(start_time * sr) if start_time is not None else 0
            end_sample = int(end_time * sr) if end_time is not None else len(y)

            # Extract segment
            segment = y[start_sample:end_sample]

            # Convert back to audio bytes
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                sf.write(tmp.name, segment, sr)
                tmp_path = tmp.name

            # Read and cleanup
            with open(tmp_path, 'rb') as f:
                audio_bytes = f.read()
            os.unlink(tmp_path)

            return audio_bytes

        except Exception as e:
            logger.warning(f"Failed to extract audio segment: {e}. Using full file.")
            with open(audio_path, 'rb') as f:
                return f.read()

    def transcribe_segment(
        self,
        audio_path: str,
        start_time: float = None,
        end_time: float = None
    ) -> str:
        """
        Transcribe audio segment via OpenAI API with base64 encoding

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (None = full file)
            end_time: End time in seconds (None = full file)

        Returns:
            Transcribed text
        """
        try:
            logger.info(f"Transcribing segment from {audio_path} ({start_time}s to {end_time}s)")

            # Extract audio segment
            if start_time is not None or end_time is not None:
                audio_bytes = self._extract_audio_segment(audio_path, start_time, end_time)
            else:
                with open(audio_path, 'rb') as f:
                    audio_bytes = f.read()

            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Determine audio format from file extension
            ext = os.path.splitext(audio_path)[1].lower()
            audio_format = "ogg" if ext in [".ogg", ".opus"] else ext.strip(".")
            if not audio_format:
                audio_format = "wav"

            # Build content with audio
            content = [
                {
                    "type": "text",
                    "text": "Please transcribe this audio."
                },
                {
                    "type": "audio_url",
                    "audio_url": {
                        "url": f"data:audio/{audio_format};base64,{audio_base64}"
                    },
                },
            ]

            # Get available models
            models = self.client.models.list()
            available_models = [model.id for model in models.data]

            if not available_models:
                logger.error("No models available on MERaLiON endpoint")
                return "[transcription failed]"

            model_name = available_models[0]
            logger.debug(f"Using model: {model_name}")

            # Call MERaLiON endpoint
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{
                    "role": "user",
                    "content": content,
                }],
                max_tokens=1024,
                temperature=0.0,
                top_p=0.9,
            )

            text = response.choices[0].message.content
            # Remove any <SpeakerId>: prefixes that MERaLiON may have added
            text_cleaned = re.sub(r'<[^>]+>:\s*', '', text)
            logger.debug(f"Transcribed segment: {text_cleaned[:50]}...")
            return text_cleaned

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "[transcription failed]"

    def predict_emotion(
        self,
        audio_path: str,
        start_time: float = None,
        end_time: float = None
    ) -> Tuple[str, float]:
        """
        Predict emotion via OpenAI API with base64 encoding

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (None = full file)
            end_time: End time in seconds (None = full file)

        Returns:
            (emotion, confidence) tuple
        """
        try:
            logger.info(f"Predicting emotion from {audio_path} ({start_time}s to {end_time}s)")

            # Extract audio segment
            if start_time is not None or end_time is not None:
                audio_bytes = self._extract_audio_segment(audio_path, start_time, end_time)
            else:
                with open(audio_path, 'rb') as f:
                    audio_bytes = f.read()

            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Determine audio format from file extension
            ext = os.path.splitext(audio_path)[1].lower()
            audio_format = "ogg" if ext in [".ogg", ".opus"] else ext.strip(".")
            if not audio_format:
                audio_format = "wav"

            # Build content with audio
            content = [
                {
                    "type": "text",
                    "text": "Describe the speaker's emotion in one simple word. Respond with only the emotion word and a confidence score (0-1) in JSON format like {\"emotion\": \"happy\", \"confidence\": 0.95}"
                },
                {
                    "type": "audio_url",
                    "audio_url": {
                        "url": f"data:audio/{audio_format};base64,{audio_base64}"
                    },
                },
            ]

            # Get available models
            models = self.client.models.list()
            available_models = [model.id for model in models.data]

            if not available_models:
                logger.error("No models available on MERaLiON endpoint")
                return "neutral", 0.5

            model_name = available_models[0]

            # Call MERaLiON endpoint
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{
                    "role": "user",
                    "content": content,
                }],
                max_tokens=256,
                temperature=0.0,
                top_p=0.9,
            )

            result_text = response.choices[0].message.content

            # Parse JSON response
            try:
                result = json.loads(result_text)
                emotion = result.get("emotion", "neutral").lower()
                confidence = float(result.get("confidence", 0.5))
            except (json.JSONDecodeError, ValueError):
                # Fallback: extract first word as emotion
                emotion = result_text.split()[0].lower() if result_text else "neutral"
                confidence = 0.5

            logger.debug(f"Predicted emotion: {emotion} ({confidence:.2f})")
            return emotion, confidence

        except Exception as e:
            logger.error(f"Emotion prediction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "neutral", 0.5

    def transcribe_audio_array(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio array via OpenAI API with base64 encoding

        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate of the audio

        Returns:
            Transcribed text
        """
        try:
            import soundfile as sf
            import tempfile

            # Convert numpy array to WAV format
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                sf.write(tmp.name, audio_data, sample_rate)
                tmp_path = tmp.name

            # Use transcribe_segment with the temporary file
            result = self.transcribe_segment(tmp_path)

            # Cleanup
            os.unlink(tmp_path)

            return result

        except Exception as e:
            logger.error(f"Array transcription failed: {e}")
            return "[transcription failed]"

    def summarize(self, transcription: str, speaker_segments: List[Dict] = None) -> Dict[str, str]:
        """
        Summarize transcription using remote text LLM

        For now, this uses MERaLiON's text capability.
        TODO: Integrate with SageMaker Qwen for better summarization.

        Args:
            transcription: Full transcribed text
            speaker_segments: Optional list of speaker segments for context

        Returns:
            {
                "intention": str,
                "conclusion": str,
                "speaker_pov": dict,
                "model": str,
                "generated_at": str
            }
        """
        try:
            logger.info(f"Generating summary for {len(transcription)} characters of transcription")

            # Build speaker context
            speaker_context = ""
            if speaker_segments:
                for seg in speaker_segments:
                    speaker_id = seg.get('speaker_id', 'Unknown')
                    text = seg.get('text', '')
                    emotion = seg.get('emotion', 'neutral')
                    speaker_context += f"{speaker_id}: {text} (emotion: {emotion})\n"

            # Prepare prompts for summarization
            intention_prompt = f"""Analyze this conversation and in 1-2 sentences, what is the main purpose/intention of this conversation?

Conversation:
{speaker_context or transcription}"""

            conclusion_prompt = f"""Analyze this conversation and in 2-3 sentences, what is the key conclusion or outcome?

Conversation:
{speaker_context or transcription}"""

            # Get available models
            models = self.client.models.list()
            available_models = [model.id for model in models.data]

            if not available_models:
                logger.error("No models available on MERaLiON endpoint")
                return {
                    "intention": "[summarization failed]",
                    "conclusion": "",
                    "speaker_pov": {},
                    "model": "unknown",
                    "generated_at": ""
                }

            model_name = available_models[0]

            # Generate intention
            response_intention = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": intention_prompt}],
                max_tokens=256,
                temperature=0.0,
            )
            intention = response_intention.choices[0].message.content

            # Generate conclusion
            response_conclusion = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": conclusion_prompt}],
                max_tokens=512,
                temperature=0.0,
            )
            conclusion = response_conclusion.choices[0].message.content

            # Generate speaker POV
            speaker_pov = {}
            if speaker_segments:
                unique_speakers = {}
                for seg in speaker_segments:
                    speaker_id = seg.get('speaker_id', 'Unknown')
                    if speaker_id not in unique_speakers:
                        unique_speakers[speaker_id] = seg.get('text', '')

                for speaker_id in unique_speakers.keys():  # Generate POV for all speakers
                    pov_prompt = f"""Analyze this conversation and in 1-2 sentences, what is the point of view from {speaker_id}'s perspective?

Conversation:
{speaker_context or transcription}"""

                    response_pov = self.client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": pov_prompt}],
                        max_tokens=256,
                        temperature=0.0,
                    )
                    speaker_pov[speaker_id] = response_pov.choices[0].message.content

            logger.info(f"Summary generated successfully")

            return {
                "intention": intention,
                "conclusion": conclusion,
                "speaker_pov": speaker_pov,
                "model": model_name,
                "generated_at": ""
            }

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "intention": f"[Error: {str(e)[:100]}]",
                "conclusion": "",
                "speaker_pov": {},
                "model": "unknown",
                "generated_at": ""
            }

    def get_info(self) -> Dict[str, Any]:
        """Get model information from endpoint"""
        try:
            models = self.client.models.list()
            model_list = [{"id": model.id, "object": model.object} for model in models.data]
            return {
                "models": model_list,
                "endpoint": self.base_url
            }
        except Exception as e:
            logger.error(f"Info request failed: {e}")
            return {"error": str(e)}

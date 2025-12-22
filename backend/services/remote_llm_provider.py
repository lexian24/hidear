"""
Remote LLM Endpoint Provider for OpenAI-compatible API
Follows the pattern of meralion_utils.py for accessing shared remote models
"""
import base64
import logging
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)


class RemoteLLMProvider:
    """
    Client for remote OpenAI-compatible LLM endpoints.
    Supports MERaLiON (transcription/emotion) and Llama/Qwen (summarization).

    Based on meralion_utils.py pattern:
    - Uses OpenAI client with custom base_url
    - Supports both text-only and audio-enabled endpoints
    - No authentication needed (internal use)
    """

    def __init__(
        self,
        meralion_base_url: str = "http://192.168.140.226:8005/v1",
        llama_base_url: Optional[str] = None,
    ):
        """
        Initialize remote LLM provider.

        Args:
            meralion_base_url: URL for MERaLiON endpoint (audio + text)
            llama_base_url: URL for Llama/Qwen endpoint (text only)
                           If None, uses same as meralion_base_url
        """
        self.meralion_base_url = meralion_base_url
        self.llama_base_url = llama_base_url or meralion_base_url

        # Initialize OpenAI clients for both endpoints
        self.meralion_client = self._create_client(self.meralion_base_url)

        # Only create separate Llama client if endpoints are different
        if self.llama_base_url != self.meralion_base_url:
            self.llama_client = self._create_client(self.llama_base_url)
        else:
            self.llama_client = self.meralion_client

        logger.info(f"✅ RemoteLLMProvider initialized")
        logger.info(f"   MERaLiON endpoint: {self.meralion_base_url}")
        logger.info(f"   Llama endpoint: {self.llama_base_url}")

    @staticmethod
    def _create_client(base_url: str) -> OpenAI:
        """Create OpenAI client with custom base_url"""
        return OpenAI(
            api_key="EMPTY",  # No authentication needed for internal endpoints
            base_url=base_url,
        )

    def get_available_models(self, endpoint_type: str = "meralion") -> list:
        """
        Get available models from the remote endpoint.

        Args:
            endpoint_type: 'meralion' or 'llama'

        Returns:
            List of available model names
        """
        try:
            client = self.meralion_client if endpoint_type == "meralion" else self.llama_client
            models = client.models.list()
            model_names = [model.id for model in models.data]
            logger.info(f"Available {endpoint_type} models: {model_names}")
            return model_names
        except Exception as e:
            logger.error(f"Error fetching models from {endpoint_type}: {e}")
            return []

    def transcribe(
        self,
        audio_file_path: str,
        prompt: str = "Please transcribe this speech.",
    ) -> str:
        """
        Transcribe audio using remote MERaLiON endpoint.

        Args:
            audio_file_path: Path to audio file
            prompt: Transcription prompt

        Returns:
            Transcribed text
        """
        try:
            logger.info(f"Transcribing with remote MERaLiON: {audio_file_path}")

            # Load and encode audio to base64
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Build content with audio
            content = [
                {
                    "type": "text",
                    "text": f"Instruction: {prompt}\nFollow the text instruction based on the following audio: <SpeechHere>"
                },
                {
                    "type": "audio_url",
                    "audio_url": {
                        "url": f"data:audio/ogg;base64,{audio_base64}"
                    },
                },
            ]

            # Get available models and pick the first one
            models = self.get_available_models("meralion")
            if not models:
                raise ValueError("No MERaLiON models available on endpoint")

            model_name = models[0]

            # Call MERaLiON endpoint
            response = self.meralion_client.chat.completions.create(
                model=model_name,
                messages=[{
                    "role": "user",
                    "content": content,
                }],
                max_tokens=1024,
                temperature=0.0,
                top_p=0.9,
            )

            transcription = response.choices[0].message.content
            logger.info(f"✅ Transcription complete: {transcription[:80]}...")
            return transcription

        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return "[transcription failed]"

    def predict_emotion(
        self,
        audio_file_path: str,
        prompt: str = "Describe the speaker's emotion in one simple word",
    ) -> Tuple[str, float]:
        """
        Predict emotion using remote MERaLiON endpoint.

        Args:
            audio_file_path: Path to audio file
            prompt: Emotion prediction prompt

        Returns:
            (emotion, confidence) tuple
        """
        try:
            logger.info(f"Predicting emotion with remote MERaLiON: {audio_file_path}")

            # Load and encode audio to base64
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Build content with audio
            content = [
                {
                    "type": "text",
                    "text": f"Instruction: {prompt}\nFollow the text instruction based on the following audio: <SpeechHere>"
                },
                {
                    "type": "audio_url",
                    "audio_url": {
                        "url": f"data:audio/ogg;base64,{audio_base64}"
                    },
                },
            ]

            # Get available models
            models = self.get_available_models("meralion")
            if not models:
                raise ValueError("No MERaLiON models available on endpoint")

            model_name = models[0]

            # Call MERaLiON endpoint
            response = self.meralion_client.chat.completions.create(
                model=model_name,
                messages=[{
                    "role": "user",
                    "content": content,
                }],
                max_tokens=128,
                temperature=0.0,
                top_p=0.9,
            )

            emotion = response.choices[0].message.content.strip()
            confidence = 0.8  # Default confidence for MERaLiON predictions

            logger.info(f"✅ Emotion predicted: {emotion} (confidence: {confidence})")
            return emotion, confidence

        except Exception as e:
            logger.error(f"❌ Emotion prediction failed: {e}")
            return "neutral", 0.5

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        endpoint_type: str = "llama",
    ) -> str:
        """
        Generate text using remote LLM endpoint (Llama/Qwen for summarization).

        Args:
            prompt: Text prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            endpoint_type: 'llama' or 'meralion'

        Returns:
            Generated text
        """
        try:
            logger.info(f"Generating text with remote {endpoint_type}...")

            client = self.meralion_client if endpoint_type == "meralion" else self.llama_client

            # Get available models
            models = self.get_available_models(endpoint_type)
            if not models:
                raise ValueError(f"No {endpoint_type} models available on endpoint")

            model_name = models[0]

            # Call LLM endpoint
            response = client.chat.completions.create(
                model=model_name,
                messages=[{
                    "role": "user",
                    "content": prompt,
                }],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
            )

            generated_text = response.choices[0].message.content.strip()
            logger.info(f"✅ Generation complete: {generated_text[:80]}...")
            return generated_text

        except Exception as e:
            logger.error(f"❌ Text generation failed: {e}")
            return "[generation failed]"

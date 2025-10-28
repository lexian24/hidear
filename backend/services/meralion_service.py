"""
MERaLiON-10B Service for Transcription + Emotion Recognition
Replaces Whisper and Emotion Recognition while keeping Diarization and Speaker ID
"""
import os
import re
import torch
import librosa
import numpy as np
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MERaLiONService:
    """
    MERaLiON-10B for transcription and emotion recognition
    Uses vLLM with MERaLiON plugin for efficient inference
    """

    def __init__(self, model_name: str = "MERaLiON/MERaLiON-2-10B"):
        """
        Initialize MERaLiON service

        Args:
            model_name: MERaLiON model variant
                - MERaLiON/MERaLiON-2-10B (general)
                - MERaLiON/MERaLiON-2-10B-ASR (ASR optimized)
                - MERaLiON/MERaLiON-2-3B (smaller, for testing)
        """
        logger.info(f"Loading MERaLiON model: {model_name}...")

        self.model_name = model_name
        self.llm = None
        self.sampling_params = None

        self._load_model()

        logger.info("✅ MERaLiON loaded successfully")

    def _load_model(self):
        """Load vLLM with MERaLiON plugin"""
        try:
            from vllm import LLM, SamplingParams
            from vllm_plugin_meralion2 import NoRepeatNGramLogitsProcessor

            # Check CUDA availability
            logger.info(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                logger.info(f"CUDA devices: {torch.cuda.device_count()}")
                logger.info(f"Current CUDA device: {torch.cuda.current_device()}")

            # Get memory configuration from environment (for shared GPU scenarios)
            gpu_memory_utilization = float(os.getenv("VLLM_GPU_MEMORY_UTILIZATION", "0.90"))
            max_model_len = int(os.getenv("VLLM_MAX_MODEL_LEN", "8192"))

            logger.info(f"vLLM config: gpu_memory_utilization={gpu_memory_utilization}, max_model_len={max_model_len}")

            # Load vLLM with MERaLiON - with memory optimization for shared GPU
            self.llm = LLM(
                model=self.model_name,
                tokenizer=self.model_name,
                limit_mm_per_prompt={"audio": 1},
                trust_remote_code=True,
                dtype=torch.bfloat16,
                device="cuda",  # Explicitly specify CUDA device
                tensor_parallel_size=1,
                # Memory optimization parameters for shared GPU environments
                gpu_memory_utilization=gpu_memory_utilization,  # Reduce from default 0.90 to leave room for other users
                max_model_len=max_model_len,  # Limit max sequence length to reduce KV cache memory
                enforce_eager=False,  # Use CUDA graphs for efficiency when possible
                swap_space=4,  # Allow 4GB swap space for handling memory spikes
            )

            # Sampling parameters (from MERaLiON example)
            self.sampling_params = SamplingParams(
                temperature=0.0,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.0,
                seed=42,
                max_tokens=1024,
                logits_processors=[NoRepeatNGramLogitsProcessor(6)]
            )

        except Exception as e:
            logger.error(f"Failed to load MERaLiON: {e}")
            raise

    def transcribe_segment(
        self,
        audio_path: str,
        start_time: float = None,
        end_time: float = None
    ) -> str:
        """
        Transcribe audio segment using MERaLiON-10B

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (None = full file)
            end_time: End time in seconds (None = full file)

        Returns:
            Transcribed text
        """
        try:
            # Load audio at 16kHz (MERaLiON requirement)
            audio_array, sample_rate = librosa.load(audio_path, sr=16000)

            # Extract segment if specified
            if start_time is not None and end_time is not None:
                start_sample = int(start_time * sample_rate)
                end_sample = int(end_time * sample_rate)
                audio_array = audio_array[start_sample:end_sample]

            # Build prompt using MERaLiON template
            query = "Please transcribe this speech."
            prompt = (
                "<start_of_turn>user\n"
                f"Instruction: {query} \n"
                "Follow the text instruction based on the following audio: <SpeechHere><end_of_turn>\n"
                "<start_of_turn>model\n"
            )

            # Prepare multi-modal inputs
            mm_data = {"audio": [(audio_array, sample_rate)]}
            inputs = {"prompt": prompt, "multi_modal_data": mm_data}

            # Generate transcription
            outputs = self.llm.generate([inputs], sampling_params=self.sampling_params)

            # Extract text from output
            text = outputs[0].outputs[0].text.strip()

            # Parse output (handle variations)
            text = self._parse_transcription(text)

            logger.debug(f"Transcribed {end_time - start_time if start_time else 0:.1f}s: {text[:50]}...")

            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return "[transcription failed]"

    def predict_emotion(
        self,
        audio_path: str,
        start_time: float = None,
        end_time: float = None
    ) -> Tuple[str, float]:
        """
        Predict emotion using MERaLiON-10B

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (None = full file)
            end_time: End time in seconds (None = full file)

        Returns:
            (emotion, confidence) tuple
        """
        try:
            # Load audio
            audio_array, sample_rate = librosa.load(audio_path, sr=16000)

            # Extract segment
            if start_time is not None and end_time is not None:
                start_sample = int(start_time * sample_rate)
                end_sample = int(end_time * sample_rate)
                audio_array = audio_array[start_sample:end_sample]

            # Build emotion prompt - request single word response
            query = "Describe the speaker's emotion in one simple word"
            prompt = (
                "<start_of_turn>user\n"
                f"Instruction: {query} \n"
                "Follow the text instruction based on the following audio: <SpeechHere><end_of_turn>\n"
                "<start_of_turn>model\n"
            )

            # Prepare multi-modal inputs
            mm_data = {"audio": [(audio_array, sample_rate)]}
            inputs = {"prompt": prompt, "multi_modal_data": mm_data}

            # Generate emotion prediction
            outputs = self.llm.generate([inputs], sampling_params=self.sampling_params)

            # Extract emotion - use the whole output from MERaLiON
            # The prompt asks for one word, so we trust the model's response
            emotion = outputs[0].outputs[0].text.strip()

            # Default confidence (MERaLiON is generally confident in its predictions)
            confidence = 0.8

            logger.info(f"Predicted emotion: {emotion} (confidence: {confidence:.2f})")

            return emotion, confidence

        except Exception as e:
            logger.error(f"Emotion prediction failed: {e}")
            return "neutral", 0.5

    def transcribe_audio_array(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio array directly (for compatibility with old interface)

        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate of the audio

        Returns:
            Transcribed text
        """
        try:
            # Resample if needed
            if sample_rate != 16000:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                sample_rate = 16000

            # Build prompt
            query = "Please transcribe this speech."
            prompt = (
                "<start_of_turn>user\n"
                f"Instruction: {query} \n"
                "Follow the text instruction based on the following audio: <SpeechHere><end_of_turn>\n"
                "<start_of_turn>model\n"
            )

            # Prepare inputs
            mm_data = {"audio": [(audio_data, sample_rate)]}
            inputs = {"prompt": prompt, "multi_modal_data": mm_data}

            # Generate
            outputs = self.llm.generate([inputs], sampling_params=self.sampling_params)

            # Parse
            text = outputs[0].outputs[0].text.strip()
            text = self._parse_transcription(text)

            return text

        except Exception as e:
            logger.error(f"Array transcription failed: {e}")
            return ""

    def _parse_transcription(self, text: str) -> str:
        """
        Parse MERaLiON transcription output

        Handles variations like:
        - "The speech says: Hello world"
        - "Transcription: Hello world"
        - "Hello world"
        - "The speaker says 'Hello world'"
        - "<Speaker1>Hello world"
        """
        # Common prefixes to remove
        prefixes = [
            "the speech says:",
            "the speaker says:",
            "transcription:",
            "transcript:",
            "text:",
        ]
        text_lower = text.lower().strip()

        # Try to remove known prefixes
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                # Remove prefix and return rest
                text = text[len(prefix):].strip()
            
        # Remove quotes if present
        text = text.strip("'\"")
        
        # Remove anything in angle brackets (like <Speaker1>)
        text = re.sub(r'<[^>]*>', '', text).strip()
        
        # If no prefix found, return as-is (might be direct transcription)
        return text


    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "service": "MERaLiON",
            "model": self.model_name,
            "capabilities": ["transcription", "emotion"],
            "loaded": self.llm is not None,
            "dtype": "bfloat16",
            "backend": "vLLM"
        }

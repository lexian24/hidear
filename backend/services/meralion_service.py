"""
MERaLiON-10B Service for Transcription + Emotion Recognition
Replaces Whisper and Emotion Recognition while keeping Diarization and Speaker ID
"""
import os
import re
import torch
import librosa
import numpy as np
from typing import Tuple, Dict, Any, List, Optional
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
            # Changed default to 0.50 to leave room for summary model on same GPU
            gpu_memory_utilization = float(os.getenv("VLLM_GPU_MEMORY_UTILIZATION", "0.50"))
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

            # Load Llama-3-8B-Instruct for summarization
            logger.info("Loading Llama-3-8B-Instruct for summarization...")
            from transformers import AutoTokenizer

            # Get summary model memory config from environment
            summary_gpu_memory = float(os.getenv("SUMMARY_GPU_MEMORY_UTILIZATION", "0.30"))

            logger.info(f"Loading Llama-3-8B with gpu_memory_utilization={summary_gpu_memory}")

            self.summary_llm = LLM(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                tokenizer="meta-llama/Meta-Llama-3-8B-Instruct",
                trust_remote_code=True,
                dtype=torch.bfloat16,
                device="cuda",
                tensor_parallel_size=1,
                gpu_memory_utilization=summary_gpu_memory,  # 30% for summary model (~24GB available)
                max_model_len=2048,             # Reduced from 4096 for summary task
                enforce_eager=False,
                swap_space=4,
            )

            # Create tokenizer for Llama-3
            self.summary_tokenizer = AutoTokenizer.from_pretrained(
                "meta-llama/Meta-Llama-3-8B-Instruct"
            )

            # Sampling parameters for summarization (more creative, shorter output)
            self.summary_sampling_params = SamplingParams(
                temperature=0.3,
                top_p=0.9,
                max_tokens=256,
                seed=42
            )

            logger.info("✅ Llama-3-8B-Instruct loaded successfully for summarization")

        except Exception as e:
            logger.error(f"Failed to load MERaLiON or summarization model: {e}")
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

    def _generate_with_llm(self, prompt: str) -> str:
        """Helper method to generate text with Llama-3-8B"""
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = self.summary_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        outputs = self.summary_llm.generate(
            [formatted_prompt],
            sampling_params=self.summary_sampling_params
        )
        return outputs[0].outputs[0].text.strip()

    def summarize(self, transcription: str, speaker_segments: List[Dict] = None) -> Dict[str, Any]:
        """
        Summarize transcription with intention, conclusion, and per-speaker POV analysis using Llama-3-8B.
        Uses 3 separate LLM calls to avoid token limit issues and improve output quality.

        Args:
            transcription: Full concatenated transcribed text
            speaker_segments: Optional list of speaker segments with speaker_id, text, and emotion

        Returns:
            {
                "intention": str,
                "conclusion": str,
                "speaker_pov": {speaker_id: pov_text, ...},
                "model": str,
                "generated_at": str
            }
        """
        try:
            from datetime import datetime

            # Build conversation text with speaker and emotion inline
            conversation_with_speakers = ""
            speaker_context = "the conversation"
            speakers = []  # Keep order of first appearance
            speaker_set = set()

            if speaker_segments and len(speaker_segments) > 0:
                # Build formatted conversation with speaker and emotion
                for seg in speaker_segments:
                    speaker_name = seg.get('speaker_id', 'Unknown')
                    emotion = seg.get('emotion', 'neutral')
                    text = seg.get('text', '')

                    if speaker_name and speaker_name != 'Unknown':
                        if speaker_name not in speaker_set:
                            speakers.append(speaker_name)
                            speaker_set.add(speaker_name)

                    if text.strip():
                        # Format: Speaker (Emotion): text
                        conversation_with_speakers += f"{speaker_name} ({emotion}): {text}\n"

                if speakers:
                    speaker_context = f"a conversation between {', '.join(speakers)}"

                # Use formatted conversation instead of original transcription
                transcription = conversation_with_speakers

            # Truncate transcription if too long (keep within token limits)
            max_chars = 4000
            if len(transcription) > max_chars:
                transcription = transcription[:max_chars] + "..."
                logger.info(f"Truncated transcription from {len(transcription)} to {max_chars} chars for summarization")

            # ==========================================
            # STEP 1: Generate Intention
            # ==========================================
            logger.info("Step 1: Generating conversation intention...")
            intention_prompt = (
                f"Analyze this conversation:\n\n"
                f"Conversation:\n{transcription}\n\n"
                f"In 1-2 sentences, what is the main purpose/intention of this conversation?"
            )
            intention_text = self._generate_with_llm(intention_prompt)
            intention = intention_text.strip()
            logger.info(f"Generated intention: {intention[:100]}...")

            # ==========================================
            # STEP 2: Generate Conclusion
            # ==========================================
            logger.info("Step 2: Generating conversation conclusion...")
            conclusion_prompt = (
                f"Analyze this conversation:\n\n"
                f"Conversation:\n{transcription}\n\n"
                f"In 2-3 sentences, what is the key conclusion or outcome, considering each speaker's perspective and emotional state?"
            )
            conclusion_text = self._generate_with_llm(conclusion_prompt)
            conclusion = conclusion_text.strip()
            logger.info(f"Generated conclusion: {conclusion[:100]}...")

            # ==========================================
            # STEP 3: Generate Per-Speaker POV
            # ==========================================
            speaker_pov = {}
            if speakers:
                logger.info(f"Step 3: Generating POV for {len(speakers)} speakers...")

                for speaker in speakers:
                    logger.info(f"  Generating POV for {speaker}...")
                    pov_prompt = (
                        f"Analyze this conversation:\n\n"
                        f"Conversation:\n{transcription}\n\n"
                        f"In 1-2 sentences, what is the point of view and main idea from {speaker}'s perspective?"
                    )
                    pov_text = self._generate_with_llm(pov_prompt)

                    # Clean up the response (remove any leading markers)
                    pov_text = pov_text.strip()
                    if pov_text.startswith('*') or pov_text.startswith('-'):
                        pov_text = pov_text[1:].strip()

                    speaker_pov[speaker] = pov_text
                    logger.info(f"  POV for {speaker}: {pov_text[:80]}...")

                logger.info(f"Parsed speaker POVs for: {list(speaker_pov.keys())}")

            logger.info(f"Generated speaker-aware summary - Intention: {intention[:60]}...")
            logger.info(f"Final summary_json will include: intention={bool(intention)}, conclusion={bool(conclusion)}, speaker_pov={list(speaker_pov.keys())}")

            result_dict = {
                "intention": intention or "Unable to determine conversation intention",
                "conclusion": conclusion or "Unable to determine conclusion",
                "speaker_pov": speaker_pov,
                "model": "meta-llama/Meta-Llama-3-8B-Instruct",
                "generated_at": datetime.utcnow().isoformat()
            }
            logger.info(f"Returning summary result: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "intention": f"[Summarization failed: {str(e)[:100]}]",
                "conclusion": "",
                "speaker_pov": {},
                "model": "meta-llama/Meta-Llama-3-8B-Instruct",
                "generated_at": ""
            }

    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "service": "MERaLiON + Llama-3-Summary",
            "models": [self.model_name, "meta-llama/Meta-Llama-3-8B-Instruct"],
            "capabilities": ["transcription", "emotion", "summarization"],
            "loaded": self.llm is not None and self.summary_llm is not None,
            "dtype": "bfloat16",
            "backend": "vLLM"
        }

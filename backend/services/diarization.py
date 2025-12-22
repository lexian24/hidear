"""
Speaker Diarization Service
Simple speaker diarization using pyannote.audio
"""
import torch
import os
from pyannote.audio import Pipeline
from typing import List, Tuple, Any
import logging

# Patch torchaudio compatibility issue with pyannote
# Newer torchaudio removed list_audio_backends() which pyannote still tries to use
try:
    import torchaudio
    if not hasattr(torchaudio, 'list_audio_backends'):
        # Provide a stub function that returns empty list
        torchaudio.list_audio_backends = lambda: []
except (ImportError, AttributeError):
    pass

logger = logging.getLogger(__name__)


class SpeakerDiarizer:
    """
    Simple pyannote-based speaker diarization service
    """
    
    def __init__(self, use_auth_token: bool = True):
        """
        Initialize speaker diarization pipeline

        Args:
            use_auth_token: Whether to use HuggingFace auth token for pretrained models
        """
        self.pipeline = None
        self.use_auth_token = use_auth_token  # For backwards compatibility
        self._load_pipeline()
    
    def _load_pipeline(self):
        """Load pyannote speaker diarization pipeline from HuggingFace Hub"""
        try:
            logger.info("Loading pyannote speaker diarization model...")

            # Get auth token from environment if available
            auth_token = os.getenv("HUGGINGFACE_TOKEN")

            # Load the pretrained pipeline from HuggingFace Hub
            # pyannote.audio 4.0+ uses token parameter (not use_auth_token)
            try:
                logger.info("Downloading from HuggingFace Hub (community version)...")
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-community-1",
                    token=auth_token if auth_token else True
                )
            except TypeError as e:
                if "use_auth_token" in str(e) or "token" in str(e):
                    # Fallback for older pyannote.audio versions
                    logger.info("Retrying with use_auth_token parameter...")
                    self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-community-1",
                        use_auth_token=auth_token if auth_token else True
                    )
                else:
                    raise

            # Move to GPU if available
            if torch.cuda.is_available():
                self.pipeline = self.pipeline.to(torch.device("cuda"))
                logger.info("Using GPU for diarization")

            logger.info("✅ Speaker diarization model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load speaker diarization model: {e}")
            logger.info("💡 The model will be downloaded from HuggingFace Hub on first use. Make sure HF_TOKEN is set.")
            raise
    
    def diarize(self, audio_path: str, max_speakers: int = None) -> Any:
        """
        Perform speaker diarization on audio file

        Args:
            audio_path: Path to the audio file
            max_speakers: Maximum number of speakers to detect (None = unlimited, defaults to 100)

        Returns:
            Pyannote diarization result
        """
        try:
            if not self.pipeline:
                raise RuntimeError("Diarization pipeline not loaded")

            # Default to 100 speakers if not specified (allows detection of many speakers)
            if max_speakers is None:
                max_speakers = 100

            logger.info(f"Running speaker diarization on: {audio_path} (max_speakers={max_speakers})")

            # Apply the pipeline to the audio file
            # pyannote.audio community-1 supports: num_speakers, min_speakers, max_speakers
            diarization = self.pipeline(audio_path, max_speakers=max_speakers)

            # Count unique speakers using the new community-1 API
            speakers = set()
            segment_count = 0

            # pyannote.audio community-1 uses output.speaker_diarization
            # which is an iterable of (turn, speaker) tuples
            if hasattr(diarization, 'speaker_diarization'):
                # New community-1 API
                for turn, speaker in diarization.speaker_diarization:
                    speakers.add(speaker)
                    segment_count += 1
            else:
                # Fallback for older API (shouldn't happen with community-1, but just in case)
                logger.warning("Using fallback iteration method - unexpected diarization format")
                try:
                    for segment, track, speaker in diarization.itertracks(yield_label=True):
                        speakers.add(speaker)
                        segment_count += 1
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Fallback iteration failed: {e}")
                    raise

            logger.info(f"Diarization completed: {len(speakers)} speakers, {segment_count} segments")

            return diarization

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            raise
    
    def get_segments_list(self, diarization: Any) -> list:
        """
        Convert diarization result to a simple list format

        Args:
            diarization: Pyannote diarization result

        Returns:
            List of dictionaries with segment information
        """
        segments = []

        # pyannote.audio community-1 uses output.speaker_diarization
        # which is an iterable of (turn, speaker) tuples where turn is a Segment
        if hasattr(diarization, 'speaker_diarization'):
            # New community-1 API
            for turn, speaker in diarization.speaker_diarization:
                segments.append({
                    'start_time': turn.start,
                    'end_time': turn.end,
                    'speaker_id': speaker,
                    'duration': turn.end - turn.start
                })
        else:
            # Fallback for older API
            try:
                for segment, track, speaker in diarization.itertracks(yield_label=True):
                    segments.append({
                        'start_time': segment.start,
                        'end_time': segment.end,
                        'speaker_id': speaker,
                        'duration': segment.end - segment.start
                    })
            except (AttributeError, TypeError):
                logger.warning("Could not extract segments - unexpected diarization format")

        # Sort by start time
        segments.sort(key=lambda x: x['start_time'])

        return segments
    
    def get_info(self) -> dict:
        """Get diarization service information"""
        return {
            "model": "pyannote-speaker-diarization",
            "provider": "pyannote.audio",
            "loaded": self.pipeline is not None,
            "auth_token_used": self.use_auth_token,
            "gpu_enabled": torch.cuda.is_available()
        }
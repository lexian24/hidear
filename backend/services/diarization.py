"""
Speaker Diarization Service
Simple speaker diarization using pyannote.audio
"""
import torch
import os
from pyannote.audio import Pipeline
from typing import List, Tuple, Any
import logging

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
        self.use_auth_token = use_auth_token
        self._load_pipeline()
    
    def _load_pipeline(self):
        """Load pyannote speaker diarization pipeline"""
        try:
            logger.info("Loading pyannote speaker diarization model...")
            
            # Get auth token from environment if available
            auth_token = os.getenv("HUGGINGFACE_TOKEN")
            
            # Load the pretrained pipeline
            # pyannote.audio 3.x uses use_auth_token parameter
            try:
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=auth_token if auth_token else True
                )
            except Exception as e:
                logger.warning(f"Failed to load latest model: {e}")
                logger.info("Trying older model version...")
                try:
                    self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization",
                        use_auth_token=auth_token if auth_token else True
                    )
                except Exception as e2:
                    logger.error(f"Failed to load any diarization model: {e2}")
                    raise
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.pipeline = self.pipeline.to(torch.device("cuda"))
                logger.info("Using GPU for diarization")
            
            logger.info("✅ Speaker diarization model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load speaker diarization model: {e}")
            logger.info("💡 Tip: You may need a HuggingFace token for the latest models")
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

            # Apply the pipeline to the audio file with max_speakers parameter
            diarization = self.pipeline(audio_path, max_speakers=max_speakers)

            # Count unique speakers
            speakers = set()
            segment_count = 0
            for segment, track, speaker in diarization.itertracks(yield_label=True):
                speakers.add(speaker)
                segment_count += 1

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
        
        for segment, track, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start_time': segment.start,
                'end_time': segment.end,
                'speaker_id': speaker,
                'duration': segment.end - segment.start
            })
        
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
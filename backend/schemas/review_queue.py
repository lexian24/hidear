"""
Pydantic schemas for speaker review queue.

These schemas handle validation and serialization for the speaker review workflow,
where unidentified speakers are queued for manual review and enrollment.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SuggestedAssignment(BaseModel):
    """A suggested speaker assignment with confidence scores"""
    speaker_id: str
    speaker_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    similarity_score: float = Field(ge=0.0, le=1.0)


class AudioSegment(BaseModel):
    """Audio segment information for playback"""
    start_time: float
    end_time: float
    duration: float
    text: Optional[str] = None
    confidence: Optional[float] = None


class ReviewQueueItem(BaseModel):
    """Complete review queue item with all context"""
    id: int
    recording_id: int
    recording_filename: Optional[str] = None
    session_speaker_label: str

    # Suggested assignments
    suggested_assignments: List[SuggestedAssignment] = []

    # Review metadata
    status: str = "pending"  # pending, reviewed, dismissed
    priority: int = 1  # 1=high, 2=medium, 3=low

    # Speaker context
    segment_count: Optional[int] = None
    total_duration: Optional[float] = None
    audio_quality: Optional[float] = None

    # Audio segments for this speaker
    segments: List[AudioSegment] = []

    # Resolution (if reviewed)
    resolved_speaker_id: Optional[str] = None
    resolution_method: Optional[str] = None

    # Timestamps
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewQueueListResponse(BaseModel):
    """Response for listing review queue items"""
    items: List[ReviewQueueItem]
    total: int
    pending_count: int
    reviewed_count: int


class EnrollFromReviewRequest(BaseModel):
    """Request to enroll a speaker from review queue"""
    speaker_name: str = Field(..., min_length=1, max_length=100, description="Name for the new speaker")
    use_all_segments: bool = Field(default=True, description="Use all segments or only selected ones")
    selected_segment_indices: Optional[List[int]] = Field(default=None, description="Indices of segments to use (if not using all)")


class EnrollFromReviewResponse(BaseModel):
    """Response after enrolling speaker from review queue"""
    success: bool
    speaker_id: str
    speaker_name: str
    embeddings_count: int
    total_duration: float
    message: str


class DismissReviewRequest(BaseModel):
    """Request to dismiss a review queue item"""
    reason: Optional[str] = Field(default=None, description="Reason for dismissing")


class ReviewQueueStats(BaseModel):
    """Statistics about the review queue"""
    total_items: int
    pending_count: int
    reviewed_count: int
    dismissed_count: int
    by_recording: Dict[int, int] = {}  # recording_id -> count
    avg_segment_count: Optional[float] = None
    avg_duration: Optional[float] = None

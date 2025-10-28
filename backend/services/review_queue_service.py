"""
Review Queue Service for Hidear application.

This module handles the business logic for the speaker review queue workflow,
including fetching pending reviews, calculating statistics, and managing
speaker enrollments from review items.
"""

import logging
import json
import tempfile
import os
from typing import List, Dict, Any, Optional
from pydub import AudioSegment as PydubAudioSegment

from database.services import DatabaseService
from schemas.review_queue import (
    ReviewQueueItem,
    AudioSegment as AudioSegmentSchema
)
from .persistent_speaker_manager import PersistentSpeakerManager
from .speaker_identification import SpeakerIdentifier

logger = logging.getLogger(__name__)


class ReviewQueueService:
    """
    Service layer for speaker review queue operations.

    Handles fetching, formatting, and processing of speaker review items
    that need manual enrollment decisions.
    """

    def __init__(self, db_service: DatabaseService):
        """
        Initialize the review queue service.

        Args:
            db_service: Database service instance
        """
        self.db = db_service

    async def get_pending_reviews_list(
        self,
        status: Optional[str] = None,
        recording_id: Optional[int] = None
    ) -> List[ReviewQueueItem]:
        """
        Get all pending review items with optional filtering.

        Args:
            status: Filter by status (pending, reviewed, dismissed)
            recording_id: Filter by recording ID

        Returns:
            List of ReviewQueueItem objects
        """
        try:
            # Get review items based on filters
            if recording_id:
                review_items = await self.db.speaker_review_queue.get_pending_for_recording(recording_id)
            else:
                review_items = await self.db.speaker_review_queue.get_pending_reviews()

            # Apply status filter if provided
            if status:
                review_items = [item for item in review_items if item.status == status]

            # Convert to response schema
            items = []
            for review_item in review_items:
                item = await self._format_review_item(review_item)
                items.append(item)

            return items

        except Exception as e:
            logger.error(f"Failed to get pending reviews: {e}", exc_info=True)
            raise Exception(f"Failed to get pending reviews: {str(e)}")

    async def get_review_item_details(self, review_id: int) -> ReviewQueueItem:
        """
        Get a specific review queue item with full details.

        Args:
            review_id: The review item ID

        Returns:
            ReviewQueueItem with all details
        """
        try:
            review_item = await self.db.speaker_review_queue.get_review_by_id(review_id)
            if not review_item:
                raise Exception("Review item not found")

            return await self._format_review_item(review_item)

        except Exception as e:
            logger.error(f"Failed to get review item details: {e}", exc_info=True)
            raise

    async def _format_review_item(self, review_item) -> ReviewQueueItem:
        """
        Format a review item database object into a ReviewQueueItem schema.

        Args:
            review_item: Review item from database

        Returns:
            Formatted ReviewQueueItem
        """
        try:
            # Get recording info
            recording = await self.db.recordings.get_recording(review_item.recording_id)

            # Parse suggested assignments (stored as JSON)
            suggested_assignments = []
            if review_item.suggested_assignments:
                try:
                    suggested_data = (
                        json.loads(review_item.suggested_assignments)
                        if isinstance(review_item.suggested_assignments, str)
                        else review_item.suggested_assignments
                    )

                    if isinstance(suggested_data, list):
                        # Transform database format to schema format
                        for assignment in suggested_data:
                            speaker_id = assignment.get('persistent_speaker_id', '')
                            # Try to get the actual speaker name from the database
                            speaker_name = speaker_id  # Default to ID
                            if speaker_id:
                                try:
                                    speaker = await self.db.persistent_speakers.get_speaker(speaker_id)
                                    if speaker:
                                        speaker_name = speaker.name
                                except Exception:
                                    # If we can't fetch the name, use the ID
                                    pass

                            transformed = {
                                'speaker_id': speaker_id,
                                'speaker_name': speaker_name,
                                'confidence': assignment.get('confidence', 0.0),
                                'similarity_score': assignment.get('similarity_score', 0.0)
                            }
                            suggested_assignments.append(transformed)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse suggested assignments: {parse_err}")

            return ReviewQueueItem(
                id=review_item.id,
                recording_id=review_item.recording_id,
                recording_filename=recording.filename if recording else None,
                session_speaker_label=review_item.session_speaker_label,
                suggested_assignments=suggested_assignments,
                status=review_item.status,
                priority=review_item.priority,
                segment_count=review_item.segment_count or 0,
                total_duration=review_item.total_duration or 0.0,
                audio_quality=review_item.audio_quality,
                segments=[],  # Empty as segments are tied to processing results
                resolved_speaker_id=review_item.resolved_speaker_id,
                resolution_method=review_item.resolution_method,
                created_at=review_item.created_at,
                reviewed_at=review_item.reviewed_at
            )

        except Exception as e:
            logger.error(f"Failed to format review item: {e}", exc_info=True)
            raise

    async def get_review_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the review queue.

        Returns:
            Dictionary with review queue statistics
        """
        try:
            stats = await self.db.speaker_review_queue.get_review_stats()

            # Get per-recording breakdown
            all_items = await self.db.speaker_review_queue.get_pending_reviews()
            by_recording = {}
            for item in all_items:
                by_recording[item.recording_id] = by_recording.get(item.recording_id, 0) + 1

            return {
                'total_items': stats['total_items'],
                'pending_count': stats['pending_count'],
                'reviewed_count': stats['reviewed_count'],
                'dismissed_count': stats['dismissed_count'],
                'by_recording': by_recording,
                'avg_segment_count': None,  # Would require segment data
                'avg_duration': None  # Would require segment data
            }

        except Exception as e:
            logger.error(f"Failed to get review stats: {e}", exc_info=True)
            raise Exception(f"Failed to get review stats: {str(e)}")

    async def get_review_audio(self, review_id: int) -> str:
        """
        Get audio file path for a review item.

        Extracts and concatenates only the segments for this specific speaker,
        so reviewers can hear isolated speaker audio without other speakers.

        Args:
            review_id: The review item ID

        Returns:
            Path to temporary audio file containing only this speaker's segments
        """
        try:
            # Get review item
            review_item = await self.db.speaker_review_queue.get_review_by_id(review_id)
            if not review_item:
                raise Exception("Review item not found")

            # Get recording
            recording = await self.db.recordings.get_recording(review_item.recording_id)
            if not recording:
                raise Exception("Recording not found")

            # Get audio file path
            audio_file_path = recording.file_path
            if not os.path.exists(audio_file_path):
                raise Exception("Audio file not found")

            # Get segments for this specific speaker
            speaker_label = review_item.session_speaker_label
            segments = await self.db.speaker_segments.get_segments_for_speaker_in_recording(
                review_item.recording_id,
                speaker_label
            )

            if not segments:
                logger.warning(f"No segments found for {speaker_label} in recording {review_item.recording_id}")
                raise Exception(f"No audio segments found for {speaker_label}")

            logger.info(f"Found {len(segments)} segments for {speaker_label}, total duration: "
                       f"{sum(s.duration for s in segments):.2f}s")

            # Load full audio
            full_audio = PydubAudioSegment.from_file(audio_file_path)

            # Extract and concatenate only this speaker's segments
            speaker_audio_parts = []
            for segment in segments:
                start_ms = int(segment.start_time * 1000)
                end_ms = int(segment.end_time * 1000)
                segment_audio = full_audio[start_ms:end_ms]
                speaker_audio_parts.append(segment_audio)

            # Concatenate all segments
            if len(speaker_audio_parts) == 0:
                raise Exception(f"No audio segments extracted for {speaker_label}")

            combined_audio = speaker_audio_parts[0]
            for audio_part in speaker_audio_parts[1:]:
                combined_audio += audio_part

            logger.info(f"Combined audio duration: {len(combined_audio) / 1000.0:.2f}s")

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            combined_audio.export(temp_file.name, format='wav')
            temp_file.close()

            return temp_file.name

        except Exception as e:
            logger.error(f"Failed to get review audio: {e}", exc_info=True)
            raise

    async def enroll_speaker_from_review(
        self,
        review_id: int,
        speaker_name: str
    ) -> Dict[str, Any]:
        """
        Enroll a new speaker using only their segments from a review item.

        Extracts and uses only the specific speaker's segments for enrollment,
        ensuring clean speaker profiles without contamination from other speakers.

        Args:
            review_id: The review item ID
            speaker_name: Name for the new speaker

        Returns:
            Dictionary with enrollment result
        """
        try:
            # Get review item
            review_item = await self.db.speaker_review_queue.get_review_by_id(review_id)
            if not review_item:
                raise Exception("Review item not found")

            if review_item.status != "pending":
                raise Exception(f"Review item already {review_item.status}")

            # Get recording
            recording = await self.db.recordings.get_recording(review_item.recording_id)
            if not recording:
                raise Exception("Recording not found")

            # Get audio file path
            audio_file_path = recording.file_path
            if not os.path.exists(audio_file_path):
                raise Exception("Audio file not found")

            # Get segments for this specific speaker
            speaker_label = review_item.session_speaker_label
            segments = await self.db.speaker_segments.get_segments_for_speaker_in_recording(
                review_item.recording_id,
                speaker_label
            )

            if not segments:
                raise Exception(f"No audio segments found for {speaker_label}")

            logger.info(f"Found {len(segments)} segments for {speaker_label}, extracting audio...")

            # Load full audio
            full_audio = PydubAudioSegment.from_file(audio_file_path)

            # Extract and concatenate only this speaker's segments
            speaker_audio_parts = []
            for segment in segments:
                start_ms = int(segment.start_time * 1000)
                end_ms = int(segment.end_time * 1000)
                segment_audio = full_audio[start_ms:end_ms]
                speaker_audio_parts.append(segment_audio)

            # Concatenate all segments
            if len(speaker_audio_parts) == 0:
                raise Exception(f"No audio segments extracted for {speaker_label}")

            combined_audio = speaker_audio_parts[0]
            for audio_part in speaker_audio_parts[1:]:
                combined_audio += audio_part

            total_duration = len(combined_audio) / 1000.0  # Convert milliseconds to seconds

            # Check if we have enough audio
            if total_duration < 1.0:  # Minimum 1 second
                raise Exception(
                    f"Audio too short for enrollment. Need at least 1s, got {total_duration:.2f}s"
                )

            # Save speaker audio to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            combined_audio.export(temp_file.name, format='wav')
            temp_file.close()
            temp_files = [temp_file.name]

            try:
                logger.info(f"Enrolling speaker '{speaker_name}' from review {review_id}, "
                           f"speaker segments duration: {total_duration:.2f}s")

                # Initialize speaker identifier and manager
                speaker_identifier = SpeakerIdentifier()
                speaker_manager = PersistentSpeakerManager(self.db, speaker_identifier)

                # Enroll speaker
                result = await speaker_manager.enroll_speaker_from_files(
                    speaker_name=speaker_name,
                    audio_files=temp_files
                )

                if result.get('status') != 'enrolled':
                    raise Exception(result.get('message', 'Enrollment failed'))

                # Mark review as resolved
                await self.db.speaker_review_queue.mark_reviewed(
                    review_id=review_id,
                    resolved_speaker_id=result['speaker_id'],
                    resolution_method='enrolled_from_review'
                )

                return {
                    'success': True,
                    'speaker_id': result['speaker_id'],
                    'speaker_name': speaker_name,
                    'embeddings_count': result['embeddings_count'],
                    'total_duration': total_duration,
                    'message': f"Successfully enrolled speaker '{speaker_name}'"
                }

            finally:
                # Clean up temp files
                for temp_file_path in temp_files:
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to delete temp file {temp_file_path}: {cleanup_err}")

        except Exception as e:
            logger.error(f"Failed to enroll speaker from review: {e}", exc_info=True)
            raise

    async def dismiss_review(self, review_id: int) -> bool:
        """
        Dismiss a review queue item.

        Args:
            review_id: The review item ID

        Returns:
            True if successful, False if item not found
        """
        try:
            success = await self.db.speaker_review_queue.dismiss_review(review_id)
            return success

        except Exception as e:
            logger.error(f"Failed to dismiss review: {e}", exc_info=True)
            raise

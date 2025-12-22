"""
Audio Processor with Persistent Speaker Management

Complete audio processing pipeline:
1. Speaker diarization (pyannote identifies speakers)
2. MERaLiON transcription + emotion recognition (per speaker segment)
3. Segment merging (consecutive same-speaker segments)
4. Persistent speaker identification and enrollment (database integration)
"""
import logging
import warnings
from typing import Dict, List, Any, Optional
import librosa
import numpy as np
import tempfile
import os
from pydub import AudioSegment

from .meralion_client import MERaLiONClient
from .diarization import SpeakerDiarizer
from .speaker_identification import SpeakerIdentifier
from .persistent_speaker_manager import PersistentSpeakerManager
from database.services import DatabaseService

# Suppress common audio processing warnings
warnings.filterwarnings("ignore", message=".*torchaudio.*deprecated.*")
warnings.filterwarnings("ignore", message=".*MPEG_LAYER_III subtype is unknown.*")
warnings.filterwarnings("ignore", message=".*degrees of freedom is <= 0.*")

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Complete audio processing pipeline with persistent speaker management.

    Features:
    1. Speaker diarization (pyannote identifies speakers)
    2. MERaLiON-10B transcription + emotion (per speaker segment)
    3. Segment merging (consecutive same-speaker segments)
    4. Automatic speaker identification against persistent database
    5. New speaker enrollment with high-quality segments
    6. Session-to-persistent speaker mappings
    7. Review queue for ambiguous speaker assignments
    """

    def __init__(self, db_service: Optional[DatabaseService] = None):
        """
        Initialize audio processing components.

        Args:
            db_service: Optional database service for persistent speaker management
        """
        logger.info("Initializing audio processing components...")

        # Initialize core components
        self.meralion = MERaLiONClient()
        self.diarizer = SpeakerDiarizer()
        self.speaker_identifier = SpeakerIdentifier()

        # Database and persistent speaker management (optional)
        self.db = db_service
        self.persistent_speaker_manager = None

        logger.info("All audio processing components loaded")

    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Process audio file through the complete pipeline.

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary with speakers, segments, and analysis results
        """
        try:
            logger.info(f"Starting audio processing: {audio_path}")

            # Step 1: Speaker diarization
            logger.info("Running speaker diarization...")
            diarization = self.diarizer.diarize(audio_path)

            # Step 2: Extract segments for transcription
            # Support both pyannote community-1 (new) and older API
            segments = []
            if hasattr(diarization, 'speaker_diarization'):
                # New pyannote.audio community-1 API
                for turn, speaker in diarization.speaker_diarization:
                    segments.append({
                        'start_time': turn.start,
                        'end_time': turn.end,
                        'speaker_id': speaker
                    })
            else:
                # Fallback for older pyannote.audio API
                for segment, _, speaker in diarization.itertracks(yield_label=True):
                    segments.append({
                        'start_time': segment.start,
                        'end_time': segment.end,
                        'speaker_id': speaker
                    })

            logger.info(f"Found {len(segments)} speech segments from {len(set(s['speaker_id'] for s in segments))} speakers")

            # Step 3: Merge consecutive segments from the same speaker
            logger.info("Merging consecutive segments from same speakers...")
            merged_segments = self._merge_consecutive_speaker_segments(segments)
            logger.info(f"Merged {len(segments)} segments into {len(merged_segments)} continuous speaker blocks")

            # Step 4: Filter out merged segments shorter than 1 second (noise/empty sound)
            min_segment_duration = 1.0  # 1 second minimum
            filtered_merged_segments = []
            removed_count = 0
            for segment in merged_segments:
                duration = segment['end_time'] - segment['start_time']
                if duration >= min_segment_duration:
                    filtered_merged_segments.append(segment)
                else:
                    removed_count += 1
                    logger.debug(f"Removing short merged segment ({duration:.2f}s): {segment['speaker_id']} [{segment['start_time']:.2f}s - {segment['end_time']:.2f}s]")

            if removed_count > 0:
                logger.info(f"Filtered out {removed_count} merged segments shorter than {min_segment_duration}s (noise/empty audio)")

            merged_segments = filtered_merged_segments

            # Step 5: Transcribe and analyze merged segments using MERaLiON
            logger.info("Transcribing and analyzing merged segments with MERaLiON...")
            final_segments = []

            for i, segment in enumerate(merged_segments):
                # Transcribe the entire merged segment using MERaLiON
                text = self.meralion.transcribe_segment(
                    audio_path,
                    segment['start_time'],
                    segment['end_time']
                )

                # Analyze emotion for the entire merged segment using MERaLiON
                emotion, confidence = self.meralion.predict_emotion(
                    audio_path,
                    segment['start_time'],
                    segment['end_time']
                )

                final_segments.append({
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'speaker_id': segment['speaker_id'],
                    'text': text,
                    'emotion': emotion,
                    'emotion_confidence': confidence,
                    'duration': segment['end_time'] - segment['start_time'],
                    'original_segment_count': segment.get('segment_count', 1)
                })

                logger.info(f"Processed speaker {segment['speaker_id']}: {len(text)} chars, emotion: {emotion}")

            # Step 7: Generate speaker summary
            speakers = self._generate_speaker_summary(final_segments)

            result = {
                'speakers': speakers,
                'segments': final_segments,
                'total_speakers': len(speakers),
                'total_segments': len(final_segments)
            }

            logger.info("Audio processing completed successfully")
            return result

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise

    async def process_audio_with_persistent_speakers(
        self,
        audio_path: str,
        recording_id: int,
        db_service: DatabaseService,
        auto_enroll_new_speakers: bool = True,
        confidence_threshold: float = 0.45
    ) -> Dict[str, Any]:
        """
        Process audio with persistent speaker management.

        Args:
            audio_path: Path to audio file
            recording_id: Database ID of the recording
            db_service: Database service instance
            auto_enroll_new_speakers: Whether to auto-enroll unrecognized speakers
            confidence_threshold: Minimum confidence for speaker matching

        Returns:
            Enhanced processing results with persistent speaker assignments
        """
        # Initialize database service and manager if needed
        if self.db is None:
            self.db = db_service
        if self.persistent_speaker_manager is None:
            self.persistent_speaker_manager = PersistentSpeakerManager(
                self.db, self.speaker_identifier
            )
        try:
            logger.info(f"Processing audio with persistent speakers: {audio_path}")

            # Step 1: Run standard audio processing (diarization, transcription, emotion)
            base_result = self.process_audio(audio_path)

            if not base_result['segments']:
                logger.info("No speech segments found, skipping speaker processing")
                return base_result

            # Step 2: Group segments by session speaker
            session_speakers = {}
            for segment in base_result['segments']:
                speaker_id = segment['speaker_id']
                if speaker_id not in session_speakers:
                    session_speakers[speaker_id] = []
                session_speakers[speaker_id].append(segment)

            logger.info(f"Found {len(session_speakers)} unique session speakers")

            # Step 3: Process each session speaker for persistent assignment
            persistent_assignments = {}
            enrollment_results = {}
            review_queue_items = []

            for session_speaker, segments in session_speakers.items():
                try:
                    assignment_result = await self._process_session_speaker(
                        session_speaker,
                        segments,
                        recording_id,
                        audio_path,
                        auto_enroll_new_speakers,
                        confidence_threshold
                    )

                    if assignment_result['method'] == 'matched_existing':
                        persistent_assignments[session_speaker] = assignment_result
                    elif assignment_result['method'] == 'enrolled_new':
                        enrollment_results[session_speaker] = assignment_result
                    elif assignment_result['method'] == 'needs_review':
                        review_queue_items.append(assignment_result)

                except Exception as e:
                    logger.error(f"Failed to process session speaker {session_speaker}: {e}")
                    continue

            # Step 4: Apply persistent speaker assignments to segments
            # Detect sync vs async context
            from sqlalchemy.orm import Session
            is_sync_context = isinstance(self.db.db, Session)

            if is_sync_context:
                # Use sync version (Celery context)
                enhanced_segments = self._apply_persistent_assignments_sync(
                    base_result['segments'],
                    persistent_assignments,
                    enrollment_results
                )
            else:
                # Use async version (FastAPI context)
                enhanced_segments = await self._apply_persistent_assignments(
                    base_result['segments'],
                    persistent_assignments,
                    enrollment_results
                )

            # Step 5: Generate enhanced result
            enhanced_result = {
                **base_result,
                'segments': enhanced_segments,
                'persistent_speaker_assignments': persistent_assignments,
                'new_speaker_enrollments': enrollment_results,
                'review_queue_items': review_queue_items,
                'speakers': self._generate_enhanced_speaker_summary(enhanced_segments)
            }

            logger.info(f"✅ Enhanced processing completed: "
                       f"{len(persistent_assignments)} matched, "
                       f"{len(enrollment_results)} enrolled, "
                       f"{len(review_queue_items)} for review")

            return enhanced_result

        except Exception as e:
            logger.error(f"Enhanced audio processing failed: {e}")
            # Fallback to basic processing
            return self.process_audio(audio_path)

    async def _process_session_speaker(
        self,
        session_speaker: str,
        segments: List[Dict[str, Any]],
        recording_id: int,
        audio_path: str,
        auto_enroll: bool,
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """Process a single session speaker for persistent assignment."""
        logger.info(f"Processing session speaker {session_speaker} with {len(segments)} segments")

        # Detect if we're in sync or async context
        from sqlalchemy.orm import Session
        is_sync_context = isinstance(self.db.db, Session)

        # Step 1: Try to match against existing persistent speakers
        if is_sync_context:
            match_result = self.persistent_speaker_manager.find_matching_persistent_speaker_sync(
                segments, audio_path, confidence_threshold
            )
        else:
            match_result = await self.persistent_speaker_manager.find_matching_persistent_speaker(
                segments, audio_path, confidence_threshold
            )

        if match_result:
            # High confidence match found
            logger.info(f"Matched {session_speaker} to {match_result['persistent_speaker_id']} "
                       f"(confidence: {match_result['confidence']:.3f})")

            # Create mapping
            if is_sync_context:
                self.persistent_speaker_manager.create_speaker_mapping_sync(
                    recording_id,
                    session_speaker,
                    match_result['persistent_speaker_id'],
                    match_result['confidence'],
                    match_result['similarity_score'],
                    match_result['method']
                )
            else:
                await self.persistent_speaker_manager.create_speaker_mapping(
                    recording_id,
                    session_speaker,
                    match_result['persistent_speaker_id'],
                    match_result['confidence'],
                    match_result['similarity_score'],
                    match_result['method']
                )

            return {
                'method': 'matched_existing',
                'session_speaker': session_speaker,
                'persistent_speaker_id': match_result['persistent_speaker_id'],
                'confidence': match_result['confidence'],
                'similarity_score': match_result['similarity_score']
            }

        # Step 2: No good match found - check for medium confidence matches
        medium_confidence_matches = []
        if not is_sync_context:
            medium_confidence_matches = await self._find_medium_confidence_matches(
                segments, audio_path, confidence_threshold * 0.8
            )

        if not auto_enroll:
            # Queue for manual review
            if is_sync_context:
                self._add_to_review_queue_sync(
                    recording_id, session_speaker, segments, medium_confidence_matches
                )
            else:
                await self._add_to_review_queue(
                    recording_id, session_speaker, segments, medium_confidence_matches
                )

            return {
                'method': 'needs_review',
                'session_speaker': session_speaker,
                'suggested_matches': medium_confidence_matches,
                'reason': 'medium_confidence_matches' if medium_confidence_matches else 'no_match'
            }

        # Step 3: No match or auto-enrollment enabled
        if auto_enroll and not is_sync_context:
            enrollment_result = await self.persistent_speaker_manager.enroll_speaker_from_segments(
                session_speaker,
                segments,
                recording_id,
                audio_path,
                speaker_name=None
            )

            if enrollment_result['success']:
                # Create mapping for new speaker
                if is_sync_context:
                    self.persistent_speaker_manager.create_speaker_mapping_sync(
                        recording_id,
                        session_speaker,
                        enrollment_result['persistent_speaker_id'],
                        1.0,
                        1.0,
                        'auto_enrolled'
                    )
                else:
                    await self.persistent_speaker_manager.create_speaker_mapping(
                        recording_id,
                        session_speaker,
                        enrollment_result['persistent_speaker_id'],
                        1.0,
                        1.0,
                        'auto_enrolled'
                    )

                logger.info(f"Auto-enrolled {session_speaker} as {enrollment_result['persistent_speaker_id']}")

                return {
                    'method': 'enrolled_new',
                    'session_speaker': session_speaker,
                    'persistent_speaker_id': enrollment_result['persistent_speaker_id'],
                    'enrollment_quality': enrollment_result['overall_quality'],
                    'segments_used': enrollment_result['embeddings_count']
                }
            else:
                logger.warning(f"Failed to enroll {session_speaker}: {enrollment_result['message']}")

        # Step 4: Fallback - queue for manual review
        if is_sync_context:
            self._add_to_review_queue_sync(
                recording_id, session_speaker, segments, []
            )
        else:
            await self._add_to_review_queue(
                recording_id, session_speaker, segments, []
            )

        return {
            'method': 'needs_review',
            'session_speaker': session_speaker,
            'suggested_matches': [],
            'reason': 'enrollment_failed' if auto_enroll else 'auto_enroll_disabled'
        }

    async def _find_medium_confidence_matches(
        self,
        segments: List[Dict[str, Any]],
        audio_path: str,
        min_confidence: float
    ) -> List[Dict[str, Any]]:
        """Find medium confidence matches for manual review."""
        try:
            persistent_speakers = await self.db.persistent_speakers.get_all_persistent_speakers()

            if not persistent_speakers:
                return []

            best_segment = max(segments, key=lambda s: s['end_time'] - s['start_time'])

            audio = AudioSegment.from_file(audio_path)
            start_ms = int(best_segment['start_time'] * 1000)
            end_ms = int(best_segment['end_time'] * 1000)
            segment_audio = audio[start_ms:end_ms]

            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                segment_audio.export(temp_file.name, format="wav")

                identification_speakers = []
                for speaker in persistent_speakers:
                    embeddings = await self.db.speaker_embeddings.get_embeddings_as_numpy(speaker.id)
                    if embeddings:
                        identification_speakers.append({
                            'speaker_id': speaker.id,
                            'speaker_name': speaker.name or speaker.id,
                            'embeddings': embeddings,
                            'enrollment_threshold': speaker.confidence_threshold
                        })

                result = self.speaker_identifier.identify_speaker(
                    temp_file.name, identification_speakers
                )

                os.unlink(temp_file.name)

                candidates = []
                if result['all_scores']:
                    for speaker_name, score_data in result['all_scores'].items():
                        if score_data['max_score'] >= min_confidence:
                            candidates.append({
                                'persistent_speaker_id': speaker_name,
                                'confidence': score_data['max_score'],
                                'similarity_score': score_data['max_score']
                            })

                candidates.sort(key=lambda x: x['confidence'], reverse=True)
                return candidates[:3]

        except Exception as e:
            logger.error(f"Medium confidence matching failed: {e}")
            return []

    def _add_to_review_queue_sync(
        self,
        recording_id: int,
        session_speaker: str,
        segments: List[Dict[str, Any]],
        suggested_matches: List[Dict[str, Any]]
    ) -> None:
        """Add speaker assignment to review queue (sync version for Celery)."""
        try:
            total_duration = sum(seg['end_time'] - seg['start_time'] for seg in segments)
            avg_quality = np.mean([0.7] * len(segments))

            self.db.speaker_review_queue.add_to_review_queue_sync(
                recording_id=recording_id,
                session_speaker_label=session_speaker,
                suggested_assignments=suggested_matches,
                segment_count=len(segments),
                total_duration=total_duration,
                audio_quality=avg_quality,
                priority=1 if len(suggested_matches) > 0 else 2
            )
            logger.info(f"Added {session_speaker} to review queue for recording {recording_id}")

        except Exception as e:
            logger.error(f"Failed to add to review queue: {e}")

    async def _add_to_review_queue(
        self,
        recording_id: int,
        session_speaker: str,
        segments: List[Dict[str, Any]],
        suggested_matches: List[Dict[str, Any]]
    ) -> None:
        """Add speaker assignment to review queue (async version for FastAPI)."""
        try:
            total_duration = sum(seg['end_time'] - seg['start_time'] for seg in segments)
            avg_quality = np.mean([0.7] * len(segments))

            await self.db.speaker_review_queue.add_to_review_queue(
                recording_id=recording_id,
                session_speaker_label=session_speaker,
                suggested_assignments=suggested_matches,
                segment_count=len(segments),
                total_duration=total_duration,
                audio_quality=avg_quality,
                priority=1 if len(suggested_matches) > 0 else 2
            )

        except Exception as e:
            logger.error(f"Failed to add to review queue: {e}")

    def _apply_persistent_assignments_sync(
        self,
        segments: List[Dict[str, Any]],
        persistent_assignments: Dict[str, Any],
        enrollment_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply persistent speaker assignments to segments (sync version for Celery)."""
        from database.models import PersistentSpeaker
        from sqlalchemy.orm import Session

        enhanced_segments = []

        for segment in segments:
            enhanced_segment = segment.copy()
            session_speaker = segment['speaker_id']

            if session_speaker in persistent_assignments:
                assignment = persistent_assignments[session_speaker]
                enhanced_segment['persistent_speaker_id'] = assignment['persistent_speaker_id']
                enhanced_segment['assignment_confidence'] = assignment['confidence']
                enhanced_segment['assignment_method'] = 'matched_existing'

                if isinstance(self.db.db, Session):
                    speaker = self.db.db.query(PersistentSpeaker).filter(
                        PersistentSpeaker.id == assignment['persistent_speaker_id']
                    ).first()
                    speaker_name = speaker.name if speaker and speaker.name else assignment['persistent_speaker_id']
                else:
                    speaker_name = assignment['persistent_speaker_id']

                enhanced_segment['persistent_speaker_name'] = speaker_name
                enhanced_segment['speaker_id'] = speaker_name

            elif session_speaker in enrollment_results:
                enrollment = enrollment_results[session_speaker]
                enhanced_segment['persistent_speaker_id'] = enrollment['persistent_speaker_id']
                enhanced_segment['assignment_confidence'] = 1.0
                enhanced_segment['assignment_method'] = 'enrolled_new'

                if isinstance(self.db.db, Session):
                    speaker = self.db.db.query(PersistentSpeaker).filter(
                        PersistentSpeaker.id == enrollment['persistent_speaker_id']
                    ).first()
                    speaker_name = speaker.name if speaker and speaker.name else enrollment['persistent_speaker_id']
                else:
                    speaker_name = enrollment['persistent_speaker_id']

                enhanced_segment['persistent_speaker_name'] = speaker_name
                enhanced_segment['speaker_id'] = speaker_name

            else:
                enhanced_segment['persistent_speaker_id'] = None
                enhanced_segment['assignment_confidence'] = 0.0
                enhanced_segment['assignment_method'] = 'unassigned'
                enhanced_segment['persistent_speaker_name'] = None

            enhanced_segments.append(enhanced_segment)

        return enhanced_segments

    async def _apply_persistent_assignments(
        self,
        segments: List[Dict[str, Any]],
        persistent_assignments: Dict[str, Any],
        enrollment_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply persistent speaker assignments to segments (async version for FastAPI)."""
        enhanced_segments = []

        for segment in segments:
            enhanced_segment = segment.copy()
            session_speaker = segment['speaker_id']

            if session_speaker in persistent_assignments:
                assignment = persistent_assignments[session_speaker]
                enhanced_segment['persistent_speaker_id'] = assignment['persistent_speaker_id']
                enhanced_segment['assignment_confidence'] = assignment['confidence']
                enhanced_segment['assignment_method'] = 'matched_existing'

                speaker = await self.db.persistent_speakers.get_persistent_speaker(
                    assignment['persistent_speaker_id']
                )
                if speaker:
                    speaker_name = speaker.name or speaker.id
                else:
                    speaker_name = assignment['persistent_speaker_id']
                enhanced_segment['persistent_speaker_name'] = speaker_name
                enhanced_segment['speaker_id'] = speaker_name

            elif session_speaker in enrollment_results:
                enrollment = enrollment_results[session_speaker]
                enhanced_segment['persistent_speaker_id'] = enrollment['persistent_speaker_id']
                enhanced_segment['assignment_confidence'] = 1.0
                enhanced_segment['assignment_method'] = 'enrolled_new'

                speaker = await self.db.persistent_speakers.get_persistent_speaker(
                    enrollment['persistent_speaker_id']
                )
                if speaker:
                    speaker_name = speaker.name or speaker.id
                else:
                    speaker_name = enrollment['persistent_speaker_id']
                enhanced_segment['persistent_speaker_name'] = speaker_name
                enhanced_segment['speaker_id'] = speaker_name

            else:
                enhanced_segment['persistent_speaker_id'] = None
                enhanced_segment['assignment_confidence'] = 0.0
                enhanced_segment['assignment_method'] = 'unassigned'
                enhanced_segment['persistent_speaker_name'] = None

            enhanced_segments.append(enhanced_segment)

        return enhanced_segments

    def _generate_enhanced_speaker_summary(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate speaker summary with persistent speaker information."""
        speakers = {}

        for segment in segments:
            speaker_key = segment.get('persistent_speaker_id') or segment['speaker_id']

            if speaker_key not in speakers:
                speakers[speaker_key] = {
                    'speaker_id': segment['speaker_id'],
                    'persistent_speaker_id': segment.get('persistent_speaker_id'),
                    'persistent_speaker_name': segment.get('persistent_speaker_name'),
                    'assignment_method': segment.get('assignment_method'),
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'total_speaking_time': segment['end_time'] - segment['start_time'],
                    'avg_confidence': segment.get('assignment_confidence', 0.0),
                    'segment_count': 1
                }
            else:
                speakers[speaker_key]['start_time'] = min(
                    speakers[speaker_key]['start_time'], segment['start_time']
                )
                speakers[speaker_key]['end_time'] = max(
                    speakers[speaker_key]['end_time'],
                    segment['end_time']
                )
                speakers[speaker_key]['total_speaking_time'] += (
                    segment['end_time'] - segment['start_time']
                )

                current_count = speakers[speaker_key]['segment_count']
                current_avg = speakers[speaker_key]['avg_confidence']
                new_confidence = segment.get('assignment_confidence', 0.0)
                speakers[speaker_key]['avg_confidence'] = (
                    (current_avg * current_count + new_confidence) / (current_count + 1)
                )
                speakers[speaker_key]['segment_count'] += 1

        return list(speakers.values())

    def _generate_speaker_summary(self, segments: List[Dict]) -> List[Dict]:
        """Generate speaker summary with timing information."""
        speakers = {}

        for segment in segments:
            speaker_id = segment['speaker_id']
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    'speaker_id': speaker_id,
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time']
                }
            else:
                speakers[speaker_id]['start_time'] = min(
                    speakers[speaker_id]['start_time'],
                    segment['start_time']
                )
                speakers[speaker_id]['end_time'] = max(
                    speakers[speaker_id]['end_time'],
                    segment['end_time']
                )

        return list(speakers.values())

    def _merge_consecutive_speaker_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Merge consecutive segments from the same speaker into continuous blocks.
        """
        if not segments:
            return []

        sorted_segments = sorted(segments, key=lambda x: x['start_time'])

        merged_segments = []
        current_segment = sorted_segments[0].copy()
        current_segment['segment_count'] = 1

        for next_segment in sorted_segments[1:]:
            if (next_segment['speaker_id'] == current_segment['speaker_id'] and
                next_segment['start_time'] <= current_segment['end_time'] + 5.0):

                current_segment['end_time'] = max(current_segment['end_time'], next_segment['end_time'])
                current_segment['segment_count'] += 1

            else:
                merged_segments.append(current_segment)
                current_segment = next_segment.copy()
                current_segment['segment_count'] = 1

        merged_segments.append(current_segment)

        logger.info(f"Segment merging stats:")
        for segment in merged_segments:
            duration = segment['end_time'] - segment['start_time']
            logger.info(f"  {segment['speaker_id']}: {duration:.1f}s (merged {segment['segment_count']} segments)")

        return merged_segments

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            'meralion': self.meralion.get_info(),
            'diarization': self.diarizer.get_info(),
            'pipeline': 'diarization → MERaLiON (transcription + emotion) → persistent speaker management'
        }

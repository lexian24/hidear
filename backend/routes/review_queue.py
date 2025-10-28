"""
Review queue endpoints for speaker enrollment from diarization.

This module provides REST API endpoints for the speaker review queue workflow,
where unidentified speakers from recordings are queued for manual review
and can be enrolled as persistent speakers.
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from database import get_database_service
from database.services import DatabaseService
from schemas.review_queue import (
    ReviewQueueItem,
    ReviewQueueListResponse,
    EnrollFromReviewRequest,
    EnrollFromReviewResponse,
    DismissReviewRequest,
    ReviewQueueStats
)
from services.review_queue_service import ReviewQueueService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=ReviewQueueListResponse)
async def get_review_queue(
    status: Optional[str] = None,
    recording_id: Optional[int] = None,
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Get all items in the review queue.

    Args:
        status: Filter by status (pending, reviewed, dismissed)
        recording_id: Filter by recording ID
    """
    try:
        service = ReviewQueueService(db_service)

        # Get review items with optional filters
        items = await service.get_pending_reviews_list(status=status, recording_id=recording_id)

        # Get statistics
        stats = await service.get_review_queue_stats()

        return ReviewQueueListResponse(
            items=items,
            total=len(items),
            pending_count=stats['pending_count'],
            reviewed_count=stats['reviewed_count']
        )

    except Exception as e:
        logger.error(f"Failed to get review queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get review queue: {str(e)}")


@router.get("/stats", response_model=ReviewQueueStats)
async def get_review_stats(
    db_service: DatabaseService = Depends(get_database_service)
):
    """Get statistics about the review queue"""
    try:
        service = ReviewQueueService(db_service)
        stats = await service.get_review_queue_stats()

        return ReviewQueueStats(
            total_items=stats['total_items'],
            pending_count=stats['pending_count'],
            reviewed_count=stats['reviewed_count'],
            dismissed_count=stats['dismissed_count'],
            by_recording=stats['by_recording'],
            avg_segment_count=stats['avg_segment_count'],
            avg_duration=stats['avg_duration']
        )

    except Exception as e:
        logger.error(f"Failed to get review stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get review stats: {str(e)}")


@router.get("/{review_id}", response_model=ReviewQueueItem)
async def get_review_item(
    review_id: int,
    db_service: DatabaseService = Depends(get_database_service)
):
    """Get a specific review queue item by ID"""
    try:
        service = ReviewQueueService(db_service)
        return await service.get_review_item_details(review_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get review item: {str(e)}")


@router.get("/{review_id}/audio")
async def get_review_audio(
    review_id: int,
    segment_index: Optional[int] = None,
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Get audio segments for a review item.

    Args:
        review_id: The review item ID
        segment_index: Optional specific segment index to return (0-based).
                      If not provided, returns all segments concatenated.
    """
    try:
        service = ReviewQueueService(db_service)
        audio_file_path = await service.get_review_audio(review_id)

        # Return as file response
        return FileResponse(
            audio_file_path,
            media_type='audio/wav',
            filename=f"review_{review_id}_segment_{segment_index if segment_index is not None else 'all'}.wav",
            background=lambda: os.unlink(audio_file_path)  # Clean up after sending
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get review audio: {str(e)}")


@router.post("/{review_id}/enroll", response_model=EnrollFromReviewResponse)
async def enroll_from_review(
    review_id: int,
    request: EnrollFromReviewRequest,
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Enroll a new speaker using segments from a review queue item.

    This extracts the speaker's segments from the recording and creates
    a new persistent speaker profile.
    """
    try:
        service = ReviewQueueService(db_service)
        result = await service.enroll_speaker_from_review(review_id, request.speaker_name)

        return EnrollFromReviewResponse(
            success=True,
            speaker_id=result['speaker_id'],
            speaker_name=result['speaker_name'],
            embeddings_count=result['embeddings_count'],
            total_duration=result['total_duration'],
            message=result['message']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enroll from review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to enroll from review: {str(e)}")


@router.post("/{review_id}/dismiss")
async def dismiss_review(
    review_id: int,
    request: DismissReviewRequest = None,
    db_service: DatabaseService = Depends(get_database_service)
):
    """Dismiss a review queue item"""
    try:
        service = ReviewQueueService(db_service)
        success = await service.dismiss_review(review_id)

        if not success:
            raise HTTPException(status_code=404, detail="Review item not found")

        return {
            "status": "dismissed",
            "review_id": review_id,
            "reason": request.reason if request else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to dismiss review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to dismiss review: {str(e)}")


@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    db_service: DatabaseService = Depends(get_database_service)
):
    """Delete a specific review queue item"""
    try:
        success = await db_service.speaker_review_queue.delete_review(review_id)

        if not success:
            raise HTTPException(status_code=404, detail="Review item not found")

        return {
            "status": "deleted",
            "review_id": review_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete review: {str(e)}")


@router.delete("")
async def clear_review_queue(
    status: Optional[str] = None,
    db_service: DatabaseService = Depends(get_database_service)
):
    """
    Clear review queue items.

    Args:
        status: Filter by status to delete only specific items (pending, reviewed, dismissed).
               If not provided, deletes ALL review items.
    """
    try:
        count = await db_service.speaker_review_queue.clear_review_queue(status=status)

        return {
            "status": "cleared",
            "deleted_count": count,
            "filter": status or "all"
        }

    except Exception as e:
        logger.error(f"Failed to clear review queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear review queue: {str(e)}")

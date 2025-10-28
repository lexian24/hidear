/**
 * Types for Review Queue functionality
 */

export interface AudioSegment {
  start_time: number;
  end_time: number;
  duration: number;
  text?: string;
  confidence?: number;
}

export interface SuggestedAssignment {
  speaker_id: string;
  speaker_name: string;
  confidence: number;
  similarity_score: number;
}

export interface ReviewQueueItem {
  id: number;
  recording_id: number;
  recording_filename?: string;
  session_speaker_label: string;
  suggested_assignments: SuggestedAssignment[];
  status: 'pending' | 'reviewed' | 'dismissed';
  priority: number;
  segment_count?: number;
  total_duration?: number;
  audio_quality?: number;
  segments: AudioSegment[];
  resolved_speaker_id?: string;
  resolution_method?: string;
  resolved_at?: string;
  created_at: string;
  reviewed_at?: string;
}

export interface ReviewQueueStats {
  total_items: number;
  pending_count: number;
  reviewed_count: number;
  dismissed_count: number;
  by_recording: Record<number, number>;
  avg_segment_count?: number;
  avg_duration?: number;
}

export interface EnrollFromReviewRequest {
  speaker_name: string;
  use_all_segments: boolean;
  selected_segment_indices?: number[];
}

export interface EnrollFromReviewResponse {
  success: boolean;
  speaker_id: string;
  speaker_name: string;
  embeddings_count: number;
  total_duration: number;
  message: string;
}

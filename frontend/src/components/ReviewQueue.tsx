import React, { useState, useEffect, useRef } from 'react';
import { ReviewQueueItem, EnrollFromReviewRequest, ReviewQueueStats } from '../types/reviewQueue';
import './ReviewQueue.css';

interface ReviewQueueProps {
  onBack: () => void;
}

const ReviewQueue: React.FC<ReviewQueueProps> = ({ onBack }) => {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [stats, setStats] = useState<ReviewQueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [enrollmentName, setEnrollmentName] = useState('');
  const [selectedSegments, setSelectedSegments] = useState<number[]>([]);
  const [useAllSegments, setUseAllSegments] = useState(true);
  const [enrolling, setEnrolling] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const API_BASE = ''; // Use relative URLs to go through nginx proxy

  useEffect(() => {
    fetchReviewQueue();
    fetchStats();
  }, []);

  useEffect(() => {
    // Cleanup audio URL when component unmounts or audio changes
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const fetchReviewQueue = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/v1/review-queue?status=pending`);
      if (!response.ok) throw new Error('Failed to fetch review queue');

      const data = await response.json();
      setItems(data.items || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load review queue');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/review-queue/stats`);
      if (!response.ok) throw new Error('Failed to fetch stats');

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const handleSelectItem = async (item: ReviewQueueItem) => {
    setSelectedItem(item);
    setEnrollmentName('');
    // Initialize with all segments selected
    setSelectedSegments(item.segments.map((_, idx) => idx));
    setUseAllSegments(false); // Changed to false so users can review segments

    // Load audio for this item
    await loadAudio(item.id);
  };

  const loadAudio = async (reviewId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/review-queue/${reviewId}/audio`);
      if (!response.ok) throw new Error('Failed to load audio');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      // Revoke old URL if exists
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }

      setAudioUrl(url);
    } catch (err) {
      console.error('Failed to load audio:', err);
      setError('Failed to load audio preview');
    }
  };

  const handleEnroll = async () => {
    if (!selectedItem || !enrollmentName.trim()) {
      setError('Please enter a speaker name');
      return;
    }

    if (selectedSegments.length === 0) {
      setError('Please select at least one segment');
      return;
    }

    const selectedDuration = calculateSelectedDuration();
    if (selectedDuration < 30) {
      setError(`Insufficient audio. Need at least 30s, selected ${selectedDuration.toFixed(1)}s`);
      return;
    }

    try {
      setEnrolling(true);
      setError(null);

      const request: EnrollFromReviewRequest = {
        speaker_name: enrollmentName.trim(),
        use_all_segments: false, // Always use selected segments
        selected_segment_indices: selectedSegments
      };

      const response = await fetch(`${API_BASE}/api/v1/review-queue/${selectedItem.id}/enroll`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Enrollment failed');
      }

      const result = await response.json();

      // Show success message
      alert(`✅ ${result.message}\n\nSpeaker ID: ${result.speaker_id}\nEmbeddings: ${result.embeddings_count}\nDuration: ${result.total_duration.toFixed(1)}s`);

      // Refresh the queue
      await fetchReviewQueue();
      await fetchStats();

      // Clear selection
      setSelectedItem(null);
      setAudioUrl(null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enrollment failed');
    } finally {
      setEnrolling(false);
    }
  };

  const handleDismiss = async (itemId: number) => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm('Are you sure you want to dismiss this review?')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/review-queue/${itemId}/dismiss`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: 'User dismissed' })
      });

      if (!response.ok) throw new Error('Failed to dismiss');

      // Refresh the queue
      await fetchReviewQueue();
      await fetchStats();

      if (selectedItem?.id === itemId) {
        setSelectedItem(null);
        setAudioUrl(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to dismiss');
    }
  };

  const handleDeleteReview = async (itemId: number) => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm('Are you sure you want to delete this review? This cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/review-queue/${itemId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete review');

      // Refresh the queue
      await fetchReviewQueue();
      await fetchStats();

      if (selectedItem?.id === itemId) {
        setSelectedItem(null);
        setAudioUrl(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete review');
    }
  };

  const handleClearAll = async () => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm('⚠️ This will DELETE ALL review items. This cannot be undone. Continue?')) {
      return;
    }

    try {
      setClearing(true);
      setError(null);

      const response = await fetch(`${API_BASE}/api/v1/review-queue`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to clear review queue');

      const result = await response.json();
      alert(`✅ Deleted ${result.deleted_count} review items`);

      // Refresh the queue
      await fetchReviewQueue();
      await fetchStats();

      // Clear selection
      setSelectedItem(null);
      setAudioUrl(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear review queue');
    } finally {
      setClearing(false);
    }
  };

  const toggleSegment = (index: number) => {
    if (selectedSegments.includes(index)) {
      setSelectedSegments(selectedSegments.filter(i => i !== index));
    } else {
      setSelectedSegments([...selectedSegments, index]);
    }
  };

  const selectAllSegments = () => {
    if (selectedItem) {
      setSelectedSegments(selectedItem.segments.map((_, idx) => idx));
    }
  };

  const deselectAllSegments = () => {
    setSelectedSegments([]);
  };

  const playSegment = async (reviewId: number, segmentIndex: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/review-queue/${reviewId}/audio?segment_index=${segmentIndex}`);
      if (!response.ok) throw new Error('Failed to load segment audio');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      // Create temporary audio element to play this segment
      const audio = new Audio(url);
      audio.play();

      // Cleanup after playing
      audio.onended = () => {
        URL.revokeObjectURL(url);
      };
    } catch (err) {
      console.error('Failed to play segment:', err);
      setError('Failed to play segment audio');
    }
  };

  const calculateSelectedDuration = () => {
    if (!selectedItem) return 0;
    return selectedSegments.reduce((total, idx) => {
      return total + (selectedItem.segments[idx]?.duration || 0);
    }, 0);
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  return (
    <div className="review-queue-container">
      <header className="review-queue-header">
        <button className="back-button" onClick={onBack}>
          ← Back
        </button>
        <div className="header-content">
          <h1>🔍 Speaker Review Queue</h1>
          <p>Review and enroll unidentified speakers from recordings</p>
        </div>
        {stats && (
          <div className="queue-stats">
            <div className="stat-item">
              <span className="stat-value">{stats.pending_count}</span>
              <span className="stat-label">Pending</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.reviewed_count}</span>
              <span className="stat-label">Reviewed</span>
            </div>
            <button
              className="clear-all-button"
              onClick={handleClearAll}
              disabled={clearing || items.length === 0}
              title="Delete all review items"
            >
              {clearing ? '⏳ Clearing...' : '🗑️ Clear All'}
            </button>
          </div>
        )}
      </header>

      {error && (
        <div className="error-banner">
          <span className="error-icon">❌</span>
          <span className="error-text">{error}</span>
          <button className="error-close" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="review-queue-content">
        {/* Left Panel - Queue List */}
        <div className="queue-list-panel">
          <h2>Pending Reviews ({items.length})</h2>

          {loading ? (
            <div className="loading">Loading...</div>
          ) : items.length === 0 ? (
            <div className="empty-state">
              <p>✨ No pending reviews</p>
              <p className="empty-subtitle">Process recordings with unidentified speakers to populate the queue</p>
            </div>
          ) : (
            <div className="queue-items">
              {items.map(item => (
                <div
                  key={item.id}
                  className={`queue-item ${selectedItem?.id === item.id ? 'selected' : ''}`}
                  onClick={() => handleSelectItem(item)}
                >
                  <div className="item-header">
                    <span className="speaker-label">{item.session_speaker_label}</span>
                    <span className="item-id">#{item.id}</span>
                  </div>
                  <div className="item-info">
                    <div className="info-row">
                      <span className="info-label">📁</span>
                      <span className="info-value">{item.recording_filename || `Recording ${item.recording_id}`}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-label">🎤</span>
                      <span className="info-value">{item.segment_count} segments • {formatDuration(item.total_duration)}</span>
                    </div>
                    {item.audio_quality && (
                      <div className="info-row">
                        <span className="info-label">📊</span>
                        <span className="info-value">Quality: {(item.audio_quality * 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>
                  {item.suggested_assignments && item.suggested_assignments.length > 0 && (
                    <div className="suggested-matches">
                      <span className="suggestion-label">💡 Possible match:</span>
                      <span className="suggestion-name">{item.suggested_assignments[0].speaker_name}</span>
                      <span className="suggestion-confidence">({(item.suggested_assignments[0].confidence * 100).toFixed(0)}%)</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Panel - Detail View */}
        <div className="item-detail-panel">
          {selectedItem ? (
            <>
              <div className="detail-header">
                <h2>{selectedItem.session_speaker_label}</h2>
                <div className="detail-buttons">
                  <button
                    className="dismiss-button"
                    onClick={() => handleDismiss(selectedItem.id)}
                    title="Mark as dismissed (keeps record)"
                  >
                    ✋ Dismiss
                  </button>
                  <button
                    className="delete-button"
                    onClick={() => handleDeleteReview(selectedItem.id)}
                    title="Delete this review (cannot be undone)"
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>

              <div className="detail-info">
                <div className="info-card">
                  <h3>📊 Statistics</h3>
                  <p>Segments: {selectedItem.segment_count}</p>
                  <p>Total Duration: {formatDuration(selectedItem.total_duration)}</p>
                  {selectedItem.audio_quality && (
                    <p>Audio Quality: {(selectedItem.audio_quality * 100).toFixed(0)}%</p>
                  )}
                </div>

                {selectedItem.suggested_assignments && selectedItem.suggested_assignments.length > 0 && (
                  <div className="info-card">
                    <h3>💡 Suggested Matches</h3>
                    {selectedItem.suggested_assignments.map((suggestion, idx) => (
                      <div key={idx} className="suggestion-item">
                        <span className="suggestion-speaker">{suggestion.speaker_name}</span>
                        <span className="suggestion-score">Confidence: {(suggestion.confidence * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Audio Player */}
              <div className="audio-player-section">
                <h3>🎵 Audio Preview</h3>
                {audioUrl ? (
                  <audio ref={audioRef} controls className="audio-player" src={audioUrl}>
                    Your browser does not support audio playback.
                  </audio>
                ) : (
                  <p>Loading audio...</p>
                )}
              </div>

              {/* Segments List */}
              <div className="segments-section">
                <div className="segments-header">
                  <h3>📝 Segments ({selectedItem.segments.length})</h3>
                  <div className="segment-controls">
                    <button className="segment-control-btn" onClick={selectAllSegments}>
                      ✓ Select All
                    </button>
                    <button className="segment-control-btn" onClick={deselectAllSegments}>
                      ✗ Deselect All
                    </button>
                    <div className="selected-info">
                      <strong>{selectedSegments.length}</strong> selected •
                      <strong> {formatDuration(calculateSelectedDuration())}</strong>
                    </div>
                  </div>
                </div>
                <div className="segments-list">
                  {selectedItem.segments.map((segment, idx) => (
                    <div
                      key={idx}
                      className={`segment-item ${selectedSegments.includes(idx) ? 'selected' : 'deselected'}`}
                    >
                      <div className="segment-header">
                        <input
                          type="checkbox"
                          checked={selectedSegments.includes(idx)}
                          onChange={() => toggleSegment(idx)}
                        />
                        <span className="segment-time">
                          {formatTime(segment.start_time)} - {formatTime(segment.end_time)}
                        </span>
                        <span className="segment-duration">({segment.duration.toFixed(1)}s)</span>
                        <button
                          className="play-segment-btn"
                          onClick={() => playSegment(selectedItem.id, idx)}
                          title="Play this segment"
                        >
                          ▶️
                        </button>
                      </div>
                      {segment.text && (
                        <p className="segment-text">{segment.text}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Enrollment Form */}
              <div className="enrollment-section">
                <h3>👤 Enroll as New Speaker</h3>
                <div className="enrollment-form">
                  <input
                    type="text"
                    placeholder="Enter speaker name..."
                    value={enrollmentName}
                    onChange={(e) => setEnrollmentName(e.target.value)}
                    className="speaker-name-input"
                  />

                  <div className="enrollment-summary">
                    <div className="summary-item">
                      <span className="summary-label">Selected Segments:</span>
                      <span className="summary-value">{selectedSegments.length} / {selectedItem.segments.length}</span>
                    </div>
                    <div className="summary-item">
                      <span className="summary-label">Total Duration:</span>
                      <span className="summary-value">{formatDuration(calculateSelectedDuration())}</span>
                    </div>
                    {calculateSelectedDuration() < 30 && (
                      <div className="warning-message">
                        ⚠️ Need at least 30 seconds for enrollment
                      </div>
                    )}
                  </div>

                  <button
                    className="enroll-button"
                    onClick={handleEnroll}
                    disabled={enrolling || !enrollmentName.trim() || selectedSegments.length === 0 || calculateSelectedDuration() < 30}
                  >
                    {enrolling ? '⏳ Enrolling...' : '✅ Enroll Speaker'}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="no-selection">
              <p>👈 Select a review item from the list to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReviewQueue;

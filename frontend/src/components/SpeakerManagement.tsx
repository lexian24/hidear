import React, { useState, useEffect } from 'react';
import './SpeakerManagement.css';

interface Speaker {
  id: string;
  name: string;
  confidence_threshold: number;
  total_speaking_time: number;
  total_segments: number;
  total_recordings: number;
  embedding_count: number;
  first_seen: string;
  last_seen: string;
  is_active: boolean;
}

interface SpeakerManagementProps {
  onBack: () => void;
}

const SpeakerManagement: React.FC<SpeakerManagementProps> = ({ onBack }) => {
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEnrollment, setShowEnrollment] = useState(false);
  const [enrollmentData, setEnrollmentData] = useState({
    name: '',
    files: [] as File[]
  });
  const [enrolling, setEnrolling] = useState(false);

  const API_BASE = ''; // Use relative URLs to go through nginx proxy

  useEffect(() => {
    fetchSpeakers();
  }, []);

  const fetchSpeakers = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/persistent-speakers`);
      if (!response.ok) {
        throw new Error('Failed to fetch speakers');
      }
      const data = await response.json();
      setSpeakers(data.speakers);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load speakers');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);

    // Validate file types
    const validFiles = files.filter(file => file.type.startsWith('audio/'));
    if (validFiles.length !== files.length) {
      setError('All files must be audio files');
      return;
    }

    setEnrollmentData(prev => ({ ...prev, files: validFiles }));
    setError(null);
  };

  const handleEnrollSpeaker = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!enrollmentData.name.trim()) {
      setError('Please enter a speaker name');
      return;
    }

    if (enrollmentData.files.length === 0) {
      setError('Please select at least one audio file');
      return;
    }

    setEnrolling(true);
    setError(null);

    try {
      const formData = new FormData();

      enrollmentData.files.forEach((file, index) => {
        formData.append('files', file);
      });

      const url = `${API_BASE}/api/persistent-speakers?speaker_name=${encodeURIComponent(enrollmentData.name.trim())}`;
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to enroll speaker');
      }

      const result = await response.json();

      // Reset form and refresh speakers list
      setEnrollmentData({ name: '', files: [] });
      setShowEnrollment(false);
      await fetchSpeakers();

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enroll speaker');
    } finally {
      setEnrolling(false);
    }
  };

  const handleToggleSpeakerActivation = async (speakerId: string, speakerName: string, currentStatus: boolean) => {
    const action = currentStatus ? 'deactivate' : 'activate';

    try {
      const response = await fetch(`${API_BASE}/api/persistent-speakers/${speakerId}/toggle-activation`, {
        method: 'PATCH',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to ${action} speaker`);
      }

      await fetchSpeakers();

    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} speaker`);
    }
  };

  const handleDeleteSpeaker = async (speakerId: string, speakerName: string) => {
    if (!window.confirm(`Are you sure you want to delete speaker "${speakerName}"?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/persistent-speakers/${speakerId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete speaker');
      }

      await fetchSpeakers();
      alert(`Speaker "${speakerName}" deleted successfully`);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete speaker');
    }
  };

  const formatDateTime = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const formatSpeakingTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="speaker-management">
        <div className="loading">Loading speakers...</div>
      </div>
    );
  }

  return (
    <div className="speaker-management">
      <header className="speaker-header">
        <button className="back-button" onClick={onBack}>
          ← Back
        </button>
        <h1>Speaker Management</h1>
        <p>Enroll known speakers for automatic identification in meetings</p>
      </header>

      {error && (
        <div className="error-banner">
          <span className="error-icon">❌</span>
          <span className="error-text">{error}</span>
          <button className="error-close" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="speaker-actions">
        <button
          className="enroll-button"
          onClick={() => setShowEnrollment(true)}
          disabled={showEnrollment}
        >
          + Enroll New Speaker
        </button>
        <button className="refresh-button" onClick={fetchSpeakers}>
          🔄 Refresh
        </button>
      </div>

      {showEnrollment && (
        <div className="enrollment-form">
          <h3>Enroll New Speaker</h3>
          <form onSubmit={handleEnrollSpeaker}>
            <div className="form-group">
              <label>Speaker Name:</label>
              <input
                type="text"
                value={enrollmentData.name}
                onChange={(e) => setEnrollmentData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter speaker's name"
                disabled={enrolling}
                required
              />
            </div>

            <div className="form-group">
              <label>Audio Samples (1-5 files):</label>
              <input
                type="file"
                multiple
                accept="audio/*"
                onChange={handleFileSelect}
                disabled={enrolling}
                required
              />
              <small>
                Select one or more audio files of the speaker talking.
                More files and diverse recordings provide better accuracy.
              </small>
            </div>

            {enrollmentData.files.length > 0 && (
              <div className="file-list">
                <strong>Selected files:</strong>
                {enrollmentData.files.map((file, index) => (
                  <div key={index} className="file-item">
                    📄 {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
                  </div>
                ))}
              </div>
            )}

            <div className="form-actions">
              <button type="submit" disabled={enrolling || enrollmentData.files.length === 0}>
                {enrolling ? '⏳ Enrolling...' : 'Enroll Speaker'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowEnrollment(false);
                  setEnrollmentData({ name: '', files: [] });
                }}
                disabled={enrolling}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="speakers-section">
        <h2>Enrolled Speakers ({speakers.length})</h2>

        {speakers.length === 0 ? (
          <div className="no-speakers">
            <p>No speakers enrolled yet.</p>
            <p>Enroll speakers to enable automatic identification in meetings.</p>
          </div>
        ) : (
          <div className="speakers-list">
            {speakers.map((speaker) => (
              <div key={speaker.id} className="speaker-item">
                <div className="speaker-info">
                  <div className="speaker-name">{speaker.name}</div>
                  <div className="speaker-meta">
                    <span>⏱️ {formatSpeakingTime(speaker.total_speaking_time)} total</span>
                    <span>📅 {formatDateTime(speaker.first_seen)}</span>
                  </div>
                </div>

                <div className="speaker-actions-row">
                  <button
                    className={`toggle-activation-button ${speaker.is_active ? 'active' : 'inactive'}`}
                    onClick={() => handleToggleSpeakerActivation(speaker.id, speaker.name, speaker.is_active)}
                    title={speaker.is_active ? 'Deactivate this speaker' : 'Activate this speaker'}
                  />
                  <button
                    className="delete-button"
                    onClick={() => handleDeleteSpeaker(speaker.id, speaker.name)}
                    title="Delete this speaker permanently"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SpeakerManagement;
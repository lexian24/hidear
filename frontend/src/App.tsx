import React, { useState } from 'react';
import './App.css';
import AudioUploader from './components/AudioUploader';
import TranscriptViewer from './components/TranscriptViewer';
import StreamingInterface from './components/StreamingInterface';
import SpeakerManagement from './components/SpeakerManagement';
import RecordingHistory from './components/RecordingHistory';
import ReviewQueue from './components/ReviewQueue';
import { AudioAnalysisResult } from './types/audio';

type ViewMode = 'upload' | 'streaming' | 'speakers' | 'history' | 'review';

function App() {
  const [analysisResult, setAnalysisResult] = useState<AudioAnalysisResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('upload');

  const handleAnalysisComplete = (result: AudioAnalysisResult) => {
    setAnalysisResult(result);
    setIsProcessing(false);
    setError(null);
  };

  const handleAnalysisStart = () => {
    setIsProcessing(true);
    setAnalysisResult(null);
    setError(null);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    setIsProcessing(false);
  };

  const handleReset = () => {
    setAnalysisResult(null);
    setIsProcessing(false);
    setError(null);
  };

  const switchMode = (mode: ViewMode) => {
    setViewMode(mode);
    handleReset();
  };

  const renderContent = () => {
    if (viewMode === 'streaming') {
      return <StreamingInterface onBack={() => switchMode('upload')} />;
    }

    if (viewMode === 'speakers') {
      return <SpeakerManagement onBack={() => switchMode('upload')} />;
    }

    if (viewMode === 'review') {
      return <ReviewQueue onBack={() => switchMode('upload')} />;
    }

    if (viewMode === 'history') {
      return <RecordingHistory onRecordingSelect={(recording) => console.log(recording)} />;
    }

    return (
      <div className="dashboard-content animate-fade-in">
        <header className="dashboard-header">
          <div>
            <h1>Audio Analysis</h1>
            <p className="subtitle">Upload and analyze audio with AI-powered insights</p>
          </div>
        </header>

        {error && (
          <div className="error-banner glass-panel">
            <span className="error-icon">❌</span>
            <span className="error-text">{error}</span>
            <button className="error-close" onClick={() => setError(null)}>×</button>
          </div>
        )}

        {!analysisResult && !isProcessing && (
          <div className="upload-section glass-panel">
            <AudioUploader
              onAnalysisStart={handleAnalysisStart}
              onAnalysisComplete={handleAnalysisComplete}
              onError={handleError}
              isProcessing={isProcessing}
            />
          </div>
        )}

        {isProcessing && (
          <div className="processing-section glass-panel">
            <div className="processing-container">
              <div className="spinner-ring"></div>
              <h3>Processing Audio</h3>
              <p>Analyzing with MERaLiON transcription, emotion recognition, and speaker diarization.</p>
            </div>
            <div className="action-buttons">
              <button className="btn-secondary" onClick={handleReset}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {analysisResult && (
          <div className="results-section animate-fade-in">
            <div className="results-header">
              <h2>Analysis Complete</h2>
              <button className="btn-primary" onClick={handleReset}>
                Analyze New File
              </button>
            </div>
            <TranscriptViewer result={analysisResult} />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="app-layout">
      <aside className="sidebar glass-panel">
        <div className="sidebar-header">
          <div className="logo">Hidear</div>
          <div className="version">v1.0.0</div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${viewMode === 'upload' ? 'active' : ''}`}
            onClick={() => switchMode('upload')}
          >
            <span className="icon">📁</span>
            Upload File
          </button>
          <button
            className={`nav-item ${viewMode === 'streaming' ? 'active' : ''}`}
            onClick={() => switchMode('streaming')}
          >
            <span className="icon">🎤</span>
            Auto Recording
          </button>
          <button
            className={`nav-item ${viewMode === 'speakers' ? 'active' : ''}`}
            onClick={() => switchMode('speakers')}
          >
            <span className="icon">👥</span>
            Speakers
          </button>
          <button
            className={`nav-item ${viewMode === 'history' ? 'active' : ''}`}
            onClick={() => switchMode('history')}
          >
            <span className="icon">📜</span>
            History
          </button>
          <button
            className={`nav-item ${viewMode === 'review' ? 'active' : ''}`}
            onClick={() => switchMode('review')}
          >
            <span className="icon">🔍</span>
            Review Queue
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <div className="status-dot online"></div>
            <span>System Online</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {renderContent()}
      </main>
    </div>
  );
}

export default App;

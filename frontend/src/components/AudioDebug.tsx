import React, { useState, useRef, useCallback } from 'react';
import './AudioDebug.css';

const AudioDebug: React.FC = () => {
  const [status, setStatus] = useState<string>('Ready');
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [chunkCount, setChunkCount] = useState<number>(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startTest = useCallback(async () => {
    try {
      setStatus('Requesting microphone permission...');

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      setStatus('Got microphone access, setting up audio context...');
      streamRef.current = stream;

      // Create audio context
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000,
      });

      // Create source and analyser
      const source = audioContextRef.current.createMediaStreamSource(stream);
      const analyser = audioContextRef.current.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);

      setStatus('Setting up Safari audio capture...');

      // Use ScriptProcessorNode for Safari
      const bufferSize = 4096;
      const processor = audioContextRef.current.createScriptProcessor(bufferSize, 1, 1);

      source.connect(processor);
      processor.connect(audioContextRef.current.destination);

      let chunks = 0;
      processor.onaudioprocess = (event) => {
        chunks++;
        setChunkCount(chunks);

        const inputBuffer = event.inputBuffer;
        const audioData = inputBuffer.getChannelData(0);

        // Calculate audio level
        let sum = 0;
        for (let i = 0; i < audioData.length; i++) {
          sum += audioData[i] * audioData[i];
        }
        const rms = Math.sqrt(sum / audioData.length);
        setAudioLevel(rms);

        if (chunks <= 5) {
          console.log(`Audio chunk ${chunks}:`, audioData.length, 'samples, RMS:', rms.toFixed(4));
        }
      };

      setStatus('Audio capture started! Speak into microphone...');

    } catch (error) {
      setStatus(`Error: ${error}`);
      console.error('Audio test error:', error);
    }
  }, []);

  const stopTest = useCallback(() => {
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setStatus('Stopped');
    setAudioLevel(0);
    setChunkCount(0);
  }, []);



  return (
    <div className="audio-debug">
      <h3>🔧 Safari Audio Debug Test</h3>
      <div className="debug-stat">
        <strong>Status:</strong> {status}
      </div>
      <div className="debug-stat">
        <strong>Audio Level:</strong> {(audioLevel * 100).toFixed(1)}%
      </div>
      <div className="debug-stat">
        <strong>Chunks Received:</strong> {chunkCount}
      </div>
      <div className="debug-controls">
        <button onClick={startTest} className="debug-button start">
          🎤 Start Audio Test
        </button>
        <button onClick={stopTest} className="debug-button stop">
          ⏹️ Stop Test
        </button>
      </div>
      <div className="debug-hint">
        Open Safari Console (Develop → Show Web Inspector) to see detailed logs
      </div>
    </div>
  );
};

export default AudioDebug;
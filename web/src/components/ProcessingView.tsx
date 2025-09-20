import React from 'react';

type ProcessingViewProps = {
  apiBaseUrl: string;
  taskId: string | null;
  fileId: string | null;
  fileName: string | null;
  progress: number;
  onStop: () => void;
  processingDetails: any;
  processingPreviewMode: 'video' | 'audio';
  setProcessingPreviewMode: (v: 'video' | 'audio') => void;
  videoRef: React.RefObject<HTMLVideoElement>;
  audioRef: React.RefObject<HTMLAudioElement>;
  formatStepNameWithLanguages: (step: string, vl: string, sl?: string) => string;
};

const ProcessingView: React.FC<ProcessingViewProps> = ({
  apiBaseUrl,
  taskId,
  fileId,
  fileName,
  progress,
  onStop,
  processingDetails,
  processingPreviewMode,
  setProcessingPreviewMode,
  videoRef,
  audioRef,
  formatStepNameWithLanguages,
}) => {
  const pd = processingDetails || {};
  const steps = (pd.steps || {}) as Record<string, any>;
  const taskType = String(pd.task_type || '').toLowerCase();

  const hasVideoReady = Boolean(steps['compose_video']?.status === 'completed');
  const hasPodcastReady = Boolean(steps['compose_podcast']?.status === 'completed');
  const mode = hasVideoReady ? (processingPreviewMode || 'video') as 'video' | 'audio' : 'audio';

  return (
    <div className="processing-view">
      <div className="spinner"></div>
      <h3>Crafting Your Masterpiece</h3>

      <div className="processing-meta" role="group" aria-label="Task Meta">
        <div className="meta-card file" title={fileName || fileId || ''}>
          <div className="meta-title">
            <span className="meta-icon">📄</span>
            <span className="meta-text">{fileName || 'Untitled'}</span>
          </div>
          <div className="meta-badge">
            {String(fileName || '').toLowerCase().endsWith('.pdf')
              ? <span className="file-type-badge pdf">PDF</span>
              : <span className="file-type-badge ppt">PPT</span>}
          </div>
        </div>
        <div className="meta-card task" title={taskId || fileId || ''}>
          <div className="meta-title">
            <span className="meta-icon">🆔</span>
          </div>
          <div className="meta-actions">
            <code className={`meta-code ${taskId ? 'clickable' : ''}`}>{taskId || '(locating…)'}
            </code>
            {!taskId && (
              <span className="meta-hint">from file {fileId?.slice(0, 8) || '…'}</span>
            )}
          </div>
        </div>
      </div>

      <div className="progress-container">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <button onClick={onStop} className="cancel-btn">STOP</button>

      <div className="steps-container">
        <h4>
          <span className="steps-title">🌟 Crafting Your Masterpiece</span>
          <span className="output-badges">
            {(["video","both"].includes(taskType)) && (
              <span className="output-pill video" title="Video generation enabled">🎬 Video</span>
            )}
            {(["podcast","both"].includes(taskType)) && (
              <span className="output-pill podcast" title="Podcast generation enabled">🎧 Podcast</span>
            )}
          </span>
        </h4>

        <div className="steps-grid">
          {Object.keys(steps).map((stepName) => {
            const stepData = steps[stepName];
            if (!stepData || stepData.status === 'skipped') return null;
            const vl = String(pd.voice_language || 'english');
            const sl = String(pd.subtitle_language || vl);
            return (
              <div key={stepName} className={`step ${stepData.status}`}>
                <span className="step-icon">
                  {stepData.status === 'completed' ? '✓'
                    : (stepData.status === 'processing' || stepData.status === 'in_progress') ? '⏳'
                    : stepData.status === 'failed' ? '✗' : '○'}
                </span>
                <span className="step-name">{formatStepNameWithLanguages(stepName, vl, sl)}</span>
              </div>
            );
          }).filter(Boolean)}
        </div>

        {(hasVideoReady || hasPodcastReady) && (
          <div className="preview-block">
            {hasVideoReady && mode !== 'video' && (
              <div className="preview-toggle">
                <button type="button" className="toggle-btn" onClick={() => setProcessingPreviewMode('video')}>▶️ Watch</button>
              </div>
            )}
            {mode === 'video' && hasVideoReady && (
              <div className="video-preview-block" style={{ marginBottom: 12 }}>
                <video
                  ref={videoRef}
                  controls
                  playsInline
                  preload="metadata"
                  crossOrigin="anonymous"
                  src={`${apiBaseUrl}/api/tasks/${taskId}/video`}
                  style={{ width: '100%', borderRadius: 8 }}
                  aria-label={`Video preview for task ${taskId}`}
                />
              </div>
            )}
            {mode === 'audio' && (
              <div className="audio-preview-block">
                <audio
                  ref={audioRef}
                  controls
                  preload="auto"
                  src={`${apiBaseUrl}/api/tasks/${taskId}/${(() => { const p = ["podcast","both"].includes(taskType); return p ? 'podcast' : 'audio'; })()}`}
                  crossOrigin="anonymous"
                  aria-label="Audio narration preview"
                />
              </div>
            )}
          </div>
        )}

        {Array.isArray(pd.errors) && pd.errors.length > 0 && (
          <div className="error-section">
            <h4>Errors Encountered</h4>
            <div className="error-list">
              {pd.errors.map((error: any, index: number) => {
                const vl = String(pd.voice_language || 'english');
                const sl = String(pd.subtitle_language || vl);
                return (
                  <div key={index} className="error-item">
                    <strong>{formatStepNameWithLanguages(String(error.step), vl, sl)}:</strong> {String(error.error)}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProcessingView;


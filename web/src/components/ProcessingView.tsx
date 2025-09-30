import React from 'react';
import { useI18n } from '@/i18n/hooks';
import { STEP_STATUS_ICONS, StepStatusVariant, normalizeStepStatus } from '@/utils/stepLabels';

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
  const { t } = useI18n();
  const pd = processingDetails || {};
  const steps = (pd.steps || {}) as Record<string, any>;
  const taskType = String(pd.task_type || '').toLowerCase();
  const clampedProgress = Number.isFinite(progress)
    ? Math.max(0, Math.min(100, Math.round(progress)))
    : 0;

  const hasVideoReady = Boolean(steps['compose_video']?.status === 'completed');
  const hasPodcastReady = Boolean(steps['compose_podcast']?.status === 'completed');
  const mode = hasVideoReady ? (processingPreviewMode || 'video') as 'video' | 'audio' : 'audio';
  const shortFileId = fileId ? fileId.slice(0, 8) : '…';
  const locatingLabel = t('processing.meta.locating', undefined, '(locating…)');
  const describeStepStatus = (variant: StepStatusVariant) => {
    switch (variant) {
      case 'completed':
        return t('task.status.completed');
      case 'processing':
        return t('task.status.processing');
      case 'failed':
        return t('task.status.failed');
      case 'cancelled':
        return t('task.status.cancelled');
      case 'skipped':
        return t('task.status.skipped', undefined, 'Skipped');
      default:
        return t('task.status.pending', undefined, 'Pending');
    }
  };

  return (
    <div className="processing-view">
      <div className="spinner"></div>
      <h3>{t('processing.title')}</h3>

      <div className="processing-meta" role="group" aria-label={t('processing.meta.aria', undefined, 'Task details')}>
        <div className="meta-card file" title={fileName || fileId || ''}>
          <div className="meta-title">
            <span className="meta-icon">📄</span>
            <span className="meta-text">{fileName || t('processing.file.untitled', undefined, 'Untitled')}</span>
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
            <code className={`meta-code ${taskId ? 'clickable' : ''}`}>{taskId || locatingLabel}
            </code>
            {!taskId && (
              <span className="meta-hint">{t('processing.meta.locatingHint', { id: shortFileId }, `from file ${shortFileId}`)}</span>
            )}
          </div>
        </div>
      </div>

      <div
        className="progress-container"
        role="group"
        aria-label={t('processing.progressLabel', undefined, 'Overall progress')}
      >
        <div className="progress-header">
          <span className="progress-label">
            {t('processing.progressLabel', undefined, 'Overall progress')}
          </span>
          <span className="progress-value">
            {clampedProgress}
            <span className="progress-value__suffix">%</span>
          </span>
        </div>
        <div
          className="progress-bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={clampedProgress}
        >
          <div className="progress-fill" style={{ width: `${clampedProgress}%` }} />
        </div>
        <p className="progress-status" aria-live="polite">
          {t('processing.progressStatus', undefined, 'We are bringing your presentation to life…')}
        </p>
      </div>

      <button onClick={onStop} className="cancel-btn">{t('processing.stop')}</button>

      <div className="steps-container">
        <h4>
          <span className="steps-title">🌟 {t('processing.stepsHeading', undefined, 'Processing steps')}</span>
          <span className="output-badges">
            {(["video","both"].includes(taskType)) && (
              <span className="output-pill video" title={t('processing.preview.videoEnabled', undefined, 'Video generation enabled')}>🎬 {t('task.list.videoLabel')}</span>
            )}
            {(["podcast","both"].includes(taskType)) && (
              <span className="output-pill podcast" title={t('processing.preview.podcastEnabled', undefined, 'Podcast generation enabled')}>🎧 {t('task.list.podcastLabel')}</span>
            )}
          </span>
        </h4>

        <div className="steps-grid" role="list">
          {Object.keys(steps).map((stepName) => {
            const stepData = steps[stepName];
            if (!stepData) return null;
            const vl = String(pd.voice_language || 'english');
            const sl = String(pd.subtitle_language || vl);
            const statusVariant = normalizeStepStatus(stepData.status);
            return (
              <div
                key={stepName}
                role="listitem"
                className={`progress-step progress-step--${statusVariant}`}
              >
                <span className="progress-step__icon" aria-hidden>
                  {STEP_STATUS_ICONS[statusVariant]}
                </span>
                <div className="progress-step__body">
                  <span className="progress-step__title">
                    {formatStepNameWithLanguages(stepName, vl, sl)}
                  </span>
                  <span className="progress-step__meta">
                    {describeStepStatus(statusVariant)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {(hasVideoReady || hasPodcastReady) && (
          <div className="preview-block">
            {hasVideoReady && mode !== 'video' && (
              <div className="preview-toggle">
                <button type="button" className="toggle-btn" onClick={() => setProcessingPreviewMode('video')}>
                  {`▶️ ${t('task.preview.watch')}`}
                </button>
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
                  aria-label={t('task.preview.videoAria', { taskId: taskId ?? '' }, `Video preview for task ${taskId}`)}
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
                  aria-label={t('task.preview.audioAria')}
                />
              </div>
            )}
          </div>
        )}

        {Array.isArray(pd.errors) && pd.errors.length > 0 && (
          <div className="error-section">
            <h4>{t('processing.errorsHeading')}</h4>
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

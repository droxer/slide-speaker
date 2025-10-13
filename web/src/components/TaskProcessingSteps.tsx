'use client';

import React from 'react';
import { useI18n } from '@/i18n/hooks';
import { STEP_STATUS_ICONS, StepStatusVariant, normalizeStepStatus } from '@/utils/stepLabels';
import { getTaskStatusLabel } from '@/utils/taskStatus';
import { sortSteps } from '@/utils/stepOrdering';

type TaskProcessingStepsProps = {
  taskId: string | null;
  uploadId: string | null;
  fileName: string | null;
  progress: number;
  onStop: () => void;
  processingDetails: any;
  formatStepNameWithLanguages: (step: string, vl: string, sl?: string) => string;
};

const TaskProcessingSteps: React.FC<TaskProcessingStepsProps> = ({
  taskId,
  uploadId,
  fileName,
  progress,
  onStop,
  processingDetails,
  formatStepNameWithLanguages,
}) => {
  const { t } = useI18n();
  const pd = processingDetails || {};
  const steps = (pd.steps || {}) as Record<string, any>;
  const taskType = String(pd.task_type || '').toLowerCase();

  // Function to get appropriate file icon based on file extension with enhanced styling
  const getFileIcon = (filename: string | null) => {
    if (!filename) return {
      emoji: '📄',
      gradient: 'linear-gradient(135deg, #94a3b8, #cbd5e1)',
      color: '#64748b',
      name: 'Document'
    };

    const lowerFilename = filename.toLowerCase();

    // PDF files - Professional red gradient
    if (lowerFilename.endsWith('.pdf')) {
      return {
        emoji: '📑',
        gradient: 'linear-gradient(135deg, #ef4444, #dc2626)',
        color: '#dc2626',
        name: 'PDF Document'
      };
    }

    // PowerPoint files - Professional blue gradient
    if (lowerFilename.endsWith('.ppt') || lowerFilename.endsWith('.pptx')) {
      return {
        emoji: '📊',
        gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
        color: '#2563eb',
        name: 'Presentation'
      };
    }

    // Word files - Professional blue gradient
    if (lowerFilename.endsWith('.doc') || lowerFilename.endsWith('.docx')) {
      return {
        emoji: '📝',
        gradient: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
        color: '#0284c7',
        name: 'Document'
      };
    }

    // Excel files - Professional green gradient
    if (lowerFilename.endsWith('.xls') || lowerFilename.endsWith('.xlsx')) {
      return {
        emoji: '📈',
        gradient: 'linear-gradient(135deg, #22c55e, #16a34a)',
        color: '#16a34a',
        name: 'Spreadsheet'
      };
    }

    // Image files - Vibrant purple gradient
    if (lowerFilename.endsWith('.jpg') || lowerFilename.endsWith('.jpeg') ||
        lowerFilename.endsWith('.png') || lowerFilename.endsWith('.gif') ||
        lowerFilename.endsWith('.bmp') || lowerFilename.endsWith('.svg')) {
      return {
        emoji: '🖼️',
        gradient: 'linear-gradient(135deg, #a855f7, #9333ea)',
        color: '#9333ea',
        name: 'Image'
      };
    }

    // Video files - Cinematic purple gradient
    if (lowerFilename.endsWith('.mp4') || lowerFilename.endsWith('.avi') ||
        lowerFilename.endsWith('.mov') || lowerFilename.endsWith('.wmv')) {
      return {
        emoji: '🎬',
        gradient: 'linear-gradient(135deg, #7c3aed, #6d28d9)',
        color: '#6d28d9',
        name: 'Video'
      };
    }

    // Audio files - Musical gradient
    if (lowerFilename.endsWith('.mp3') || lowerFilename.endsWith('.wav') ||
        lowerFilename.endsWith('.ogg') || lowerFilename.endsWith('.flac')) {
      return {
        emoji: '🎵',
        gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
        color: '#d97706',
        name: 'Audio'
      };
    }

    // Text files - Clean gray gradient
    if (lowerFilename.endsWith('.txt') || lowerFilename.endsWith('.md')) {
      return {
        emoji: '📄',
        gradient: 'linear-gradient(135deg, #6b7280, #4b5563)',
        color: '#4b5563',
        name: 'Text Document'
      };
    }

    // Default fallback - Elegant gray gradient
    return {
      emoji: '📄',
      gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
      color: '#7c3aed',
      name: 'Document'
    };
  };

  const fileIcon = getFileIcon(fileName);
  const clampedProgress = Number.isFinite(progress)
    ? Math.max(0, Math.min(100, Math.round(progress)))
    : 0;

  const shortUploadId = uploadId ? uploadId.slice(0, 8) : '…';
  const locatingLabel = t('processing.meta.locating', undefined, '(locating…)');
  const describeStepStatus = (variant: StepStatusVariant) => getTaskStatusLabel(variant, t);

  // Get task configuration details
  const voiceLanguage = pd.voice_language || 'english';
  const subtitleLanguage = pd.subtitle_language || voiceLanguage;
  const transcriptLanguage = pd.transcript_language || subtitleLanguage;
  const videoResolution = pd.video_resolution || 'hd';
  const generateSubtitles = pd.generate_subtitles !== false;
  const generateAvatar = pd.generate_avatar === true;

  return (
    <div className="processing-view">
      <div className="spinner"></div>
      <h3>{t('processing.title')}</h3>

      <div className="processing-meta" role="group" aria-label={t('processing.meta.aria', undefined, 'Task details')}>
        <div className="meta-card file" title={fileName || uploadId || ''}>
          <div className="meta-card-header">
            <div
              className="meta-icon-large file-icon-enhanced"
              style={{ background: fileIcon.gradient, color: 'white' }}
              title={fileIcon.name}
            >
              <span className="file-icon-emoji">{fileIcon.emoji}</span>
            </div>
            <div className="meta-content">
              <div className="meta-title-modern">
                {fileName || t('processing.file.untitled', undefined, 'Untitled')}
              </div>
              <div className="meta-subtitle">
                {fileIcon.name}
              </div>
            </div>
            <div className="meta-badge-modern">
              {String(fileName || '').toLowerCase().endsWith('.pdf')
                ? <span className="file-type-badge pdf">PDF</span>
                : <span className="file-type-badge ppt">PPT</span>}
            </div>
          </div>
        </div>

        <div className="meta-card task-modern" title={taskId || uploadId || ''}>
          <div className="meta-card-header">
            <div className="meta-icon-large">⚙️</div>
            <div className="meta-content">
              <div className="meta-title-modern">
                {t('processing.meta.taskId', undefined, 'Task ID')}
              </div>
              <div className="meta-subtitle">
                {taskId ? `${taskId.slice(0, 8)}...${taskId.slice(-4)}` : locatingLabel}
              </div>
            </div>
            <div className="meta-actions-modern">
              {taskId && (
                <button
                  className="copy-task-id-btn"
                  onClick={() => navigator.clipboard.writeText(taskId)}
                  title={t('processing.meta.copyTaskId', undefined, 'Copy task ID')}
                >
                  📋
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="meta-card config" title={t('processing.meta.configuration', undefined, 'Configuration')}>
          <div className="meta-card-header">
            <div className="meta-icon-large">🎯</div>
            <div className="meta-content">
              <div className="meta-title-modern">
                {t('processing.meta.configuration', undefined, 'Configuration')}
              </div>
              <div className="meta-subtitle">
                {taskType === 'video' ? '🎬 Video' : taskType === 'podcast' ? '🎧 Podcast' : '🎬🎧 Both'}
              </div>
            </div>
            <div className="meta-config-badges">
              {generateAvatar && <span className="config-badge avatar">👤</span>}
              {generateSubtitles && <span className="config-badge subtitles">📝</span>}
            </div>
          </div>
        </div>

        <div className="meta-card languages" title={t('processing.meta.languages', undefined, 'Languages')}>
          <div className="meta-card-header">
            <div className="meta-icon-large">🌍</div>
            <div className="meta-content">
              <div className="meta-title-modern">
                {t('processing.meta.languages', undefined, 'Languages')}
              </div>
              <div className="meta-subtitle">
                {voiceLanguage !== subtitleLanguage
                  ? `🎤 ${voiceLanguage} • 📝 ${subtitleLanguage}`
                  : `🎤📝 ${voiceLanguage}`
                }
              </div>
            </div>
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

      <button type="button" onClick={onStop} className="cancel-btn">{t('processing.stop')}</button>

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
          {sortSteps(steps).map(([stepName, stepData]) => {
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

export default TaskProcessingSteps;
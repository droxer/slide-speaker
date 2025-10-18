'use client';

import React from 'react';
import { useI18n } from '@/i18n/hooks';
import {
  STEP_STATUS_ICONS,
  StepStatusVariant,
  normalizeStepStatus,
} from '@/utils/stepLabels';
import { getTaskStatusLabel } from '@/utils/taskStatus';
import { sortSteps } from '@/utils/stepOrdering';
import { resolveTaskType } from '@/utils/taskType';

type TaskProcessingStepsProps = {
  taskId: string | null;
  uploadId: string | null;
  fileName: string | null;
  progress: number;
  onStop: () => void;
  processingDetails: any;
  formatStepNameWithLanguages: (
    step: string,
    vl: string,
    sl?: string,
  ) => string;
};

const RESOLUTION_LABELS: Record<string, string> = {
  sd: 'runTask.resolution.sd',
  hd: 'runTask.resolution.hd',
  fullhd: 'runTask.resolution.fullhd',
};

const TaskProcessingSteps = ({
  taskId,
  uploadId,
  fileName,
  progress,
  onStop,
  processingDetails,
  formatStepNameWithLanguages,
}: TaskProcessingStepsProps) => {
  const { t } = useI18n();
  const pd = processingDetails || {};
  const steps = (pd.steps || {}) as Record<string, any>;

  const typeInfo = resolveTaskType(
    { task_type: pd.task_type, kwargs: (pd as any)?.kwargs || {} } as any,
    pd as any,
  );
  const taskTypeKey = typeInfo.key || 'unknown';
  const taskTypeLabel = t(
    `task.list.type.${taskTypeKey}`,
    undefined,
    typeInfo.fallbackLabel,
  );

  const voiceLanguage = String(pd.voice_language || 'english');
  const subtitleLanguage = String(pd.subtitle_language || voiceLanguage);
  const transcriptLanguage =
    pd.transcript_language ??
    (pd as any)?.kwargs?.transcript_language ??
    pd.podcast_transcript_language ??
    null;

  const voiceDisplay = t(
    `language.display.${voiceLanguage.toLowerCase()}`,
    undefined,
    voiceLanguage,
  );
  const subtitleDisplay = t(
    `language.display.${subtitleLanguage.toLowerCase()}`,
    undefined,
    subtitleLanguage,
  );
  const transcriptDisplay = transcriptLanguage
    ? t(
        `language.display.${String(transcriptLanguage).toLowerCase()}`,
        undefined,
        String(transcriptLanguage),
      )
    : null;

  const resolutionKey = String(pd.video_resolution || '').toLowerCase();
  const resolutionLabel = RESOLUTION_LABELS[resolutionKey]
    ? t(
        RESOLUTION_LABELS[resolutionKey],
        undefined,
        String(pd.video_resolution || '').toUpperCase(),
      )
    : null;

  const featureLabels: string[] = [];
  if (pd.generate_avatar === true) {
    featureLabels.push(
      t('processing.meta.featuresList.avatar', undefined, 'Avatar'),
    );
  }

  const taskIdShort = taskId
    ? `${taskId.slice(0, 8)}…${taskId.slice(-4)}`
    : null;
  const uploadIdShort = uploadId
    ? `${uploadId.slice(0, 6)}…${uploadId.slice(-4)}`
    : null;

  const fileHint =
    !fileName && uploadIdShort
      ? t(
          'processing.meta.locatingHint',
          { id: uploadIdShort },
          `from file ${uploadIdShort}`,
        )
      : undefined;

  const metaRows = [
    {
      key: 'task-id',
      label: t('processing.meta.taskId', undefined, 'Task ID'),
      value:
        taskIdShort ||
        t('processing.meta.locating', undefined, '(locating…)'),
      copyValue: taskId ?? undefined,
    },
    {
      key: 'type',
      label: t('processing.meta.configuration', undefined, 'Configuration'),
      value: taskTypeLabel,
    },
    {
      key: 'voice-lang',
      label: t('task.detail.voice', undefined, 'Voice'),
      value: voiceDisplay,
    },
    {
      key: 'subtitle-lang',
      label: t('task.detail.subtitles', undefined, 'Subtitles'),
      value: subtitleDisplay,
    },
  ] as Array<{
    key: string;
    label: string;
    value: React.ReactNode;
    hint?: React.ReactNode;
    copyValue?: string;
  }>;

  if (transcriptDisplay) {
    metaRows.push({
      key: 'transcript-lang',
      label: t('task.detail.transcript', undefined, 'Transcript'),
      value: transcriptDisplay,
    });
  }

  if (resolutionLabel) {
    metaRows.push({
      key: 'resolution',
      label: t('processing.meta.resolution', undefined, 'Resolution'),
      value: resolutionLabel,
    });
  }

  if (featureLabels.length > 0) {
    metaRows.push({
      key: 'features',
      label: t('processing.meta.features', undefined, 'Extras'),
      value: featureLabels.join(' · '),
    });
  }

  const clampedProgress = Number.isFinite(progress)
    ? Math.max(0, Math.min(100, Math.round(progress)))
    : 0;

  const describeStepStatus = (variant: StepStatusVariant) =>
    getTaskStatusLabel(variant, t);

  const handleCopy = (value: string | undefined) => {
    if (!value) return;
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(value).catch(() => {
        // Silently ignore clipboard failures
      });
    }
  };

  return (
    <div className="processing-view">
      <div className="spinner"></div>
      <h3>{t('processing.title')}</h3>

      <div
        className="processing-summary"
        role="group"
        aria-label={t('processing.meta.aria', undefined, 'Task details')}
      >
        <div className="processing-summary__title">
          <span className="processing-summary__file">
            {fileName ||
              t('processing.file.untitled', undefined, 'Untitled')}
          </span>
          <span className={`file-task-type-badge type-${taskTypeKey}`}>
            {taskTypeLabel}
          </span>
        </div>
        {fileHint && (
          <div className="processing-summary__caption" aria-hidden="true">
            {fileHint}
          </div>
        )}
        <dl className="processing-summary__list">
          {metaRows.map(({ key, label, value, hint, copyValue }) => (
            <div key={key} className="processing-summary__row">
              <dt>{label}</dt>
              <dd>
                <div className="processing-summary__value">
                  <span>{value}</span>
                  {copyValue && (
                    <button
                      type="button"
                      className="processing-summary__copy"
                      onClick={() => handleCopy(copyValue)}
                    >
                      {t('actions.copy', undefined, 'Copy')}
                    </button>
                  )}
                </div>
                {hint && (
                  <div className="processing-summary__hint" aria-hidden="true">
                    {hint}
                  </div>
                )}
              </dd>
            </div>
          ))}
        </dl>
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
          {t(
            'processing.progressStatus',
            undefined,
            'We are bringing your presentation to life…',
          )}
        </p>
      </div>

      <button type="button" onClick={onStop} className="cancel-btn">
        {t('processing.stop')}
      </button>

      <div className="steps-container">
        <h4>
          <span className="steps-title">
            🌟 {t('processing.stepsHeading', undefined, 'Processing steps')}
          </span>
          <span className="output-badges">
            {['video', 'both'].includes(taskTypeKey) && (
              <span
                className="output-pill video"
                title={t(
                  'processing.preview.videoEnabled',
                  undefined,
                  'Video generation enabled',
                )}
              >
                🎬 {t('task.list.videoLabel')}
              </span>
            )}
            {['podcast', 'both'].includes(taskTypeKey) && (
              <span
                className="output-pill podcast"
                title={t(
                  'processing.preview.podcastEnabled',
                  undefined,
                  'Podcast generation enabled',
                )}
              >
                🎧 {t('task.list.podcastLabel')}
              </span>
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
                <span className="progress-step__icon" aria-hidden="true">
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
                    <strong>
                      {formatStepNameWithLanguages(
                        String(error.step),
                        vl,
                        sl,
                      )}
                      :
                    </strong>{' '}
                    {String(error.error)}
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

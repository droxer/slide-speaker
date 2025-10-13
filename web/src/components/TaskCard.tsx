import React from 'react';
import { Link } from '@/navigation';
import { STEP_STATUS_ICONS, getStepLabel, normalizeStepStatus, StepStatusVariant } from '@/utils/stepLabels';
import { resolveLanguages, getLanguageDisplayName } from '@/utils/language';
import { getTaskStatusClass, getTaskStatusIcon, getTaskStatusLabel } from '@/utils/taskStatus';
import { getFileTypeIcon } from '@/utils/fileIcons';
import type { Task, DownloadItem } from '@/types';
import { useDownloadsQuery, useTranscriptQuery, hasCachedVtt, prefetchTaskPreview } from '@/services/queries';
import { useI18n } from '@/i18n/hooks';
import { useQueryClient } from '@tanstack/react-query';

type Outputs = { video: boolean; podcast: boolean };

type Props = {
  task: Task;
  apiBaseUrl: string;
  isRemoving: boolean;
  isExpanded: boolean;
  onCancel: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  onShowProcessingDetails: (task: Task) => void;
  deriveTaskOutputs: (task: Task) => Outputs;
  getLanguageDisplayName: (code: string) => string;
  getVideoResolutionDisplayName: (res: string) => string;
};

// File type badge removed per new design

const formatStepNameWithLanguages = (
  step: string,
  voiceLang: string,
  subtitleLang: string | undefined,
  t: (key: string, vars?: Record<string, string | number>, fallback?: string) => string,
): string => {
  const vl = (voiceLang || 'english').toLowerCase();
  const sl = (subtitleLang || vl).toLowerCase();
  const same = vl === sl;
  if (same && (step === 'translate_voice_transcripts' || step === 'translate_subtitle_transcripts')) {
    return t('processing.step.translatingTranscripts', undefined, 'Translating Transcripts');
  }
  return getStepLabel(step, t);
};

const TaskCard: React.FC<Props> = ({
  task,
  apiBaseUrl,
  isRemoving,
  isExpanded,
  onCancel,
  onDelete,
  onShowProcessingDetails,
  deriveTaskOutputs,
  getLanguageDisplayName,
  getVideoResolutionDisplayName,
}) => {
  const { t } = useI18n();
  const { voiceLanguage: voiceLang, transcriptLanguage } = resolveLanguages(task);
  const videoRes = task.kwargs?.video_resolution || task.state?.video_resolution || 'hd';
  const { video: isVideoTask, podcast: isPodcastTask } = deriveTaskOutputs(task);
  const transcriptLang = transcriptLanguage;
  const isUploadOnly = task.status === 'upload_only' || Boolean(task._uploadOnly);
  const uploadMeta = task.upload;
  const extractFilename = (): string => {
    // Prefer upload metadata first when available
    if (uploadMeta?.filename && typeof uploadMeta.filename === 'string' && uploadMeta.filename.trim()) {
      return uploadMeta.filename.trim();
    }
    // Try to get actual filename first
    if (task.filename && typeof task.filename === 'string' && task.filename.trim()) {
      return task.filename.trim();
    }

    // Try kwargs filename
    if (task.kwargs?.filename && typeof task.kwargs.filename === 'string' && task.kwargs.filename.trim()) {
      return task.kwargs.filename.trim();
    }

    // Try state filename
    if (task.state?.filename && typeof task.state.filename === 'string' && task.state.filename.trim()) {
      return task.state.filename.trim();
    }

    // Try to construct filename from file_path if available
    const filePath = (task.kwargs as any)?.file_path || (task.state as any)?.file_path;
    if (filePath && typeof filePath === 'string') {
      const filename = filePath.split('/').pop()?.split('\\').pop();
      if (filename && filename.trim()) {
        return filename.trim();
      }
    }

    // Construct filename from upload_id and extension if both are available
    const fileId = task.upload_id || task.kwargs?.upload_id || uploadMeta?.id;
    const fileExt = task.file_ext || task.kwargs?.file_ext || task.state?.file_ext || uploadMeta?.file_ext;

    if (fileId && typeof fileId === 'string' && fileId.trim()) {
      if (fileExt && typeof fileExt === 'string' && fileExt.trim()) {
        // Ensure extension starts with a dot
        const ext = fileExt.trim().startsWith('.') ? fileExt.trim() : `.${fileExt.trim()}`;
        return `${fileId.trim()}${ext}`;
      }
      // Return upload_id if no extension is available
      return fileId.trim();
    }

    // Try task_id as fallback
    if (task.task_id && typeof task.task_id === 'string' && task.task_id.trim()) {
      const taskId = task.task_id.trim();
      if (fileExt && typeof fileExt === 'string' && fileExt.trim()) {
        const ext = fileExt.trim().startsWith('.') ? fileExt.trim() : `.${fileExt.trim()}`;
        return `${taskId}${ext}`;
      }
      return taskId;
    }

    // Last resort - generic name
    return 'Untitled File';
  };

  const filename = extractFilename();
  const rawExt =
    task.file_ext ||
    task.kwargs?.file_ext ||
    (task.state && typeof task.state.file_ext === 'string' ? task.state.file_ext : '') ||
    (uploadMeta && typeof uploadMeta.file_ext === 'string' ? uploadMeta.file_ext : '') ||
    filename.split('.').pop()?.toLowerCase() ||
    '';
  const fileExt = typeof rawExt === 'string' ? rawExt.replace(/^\./, '') : '';
  // Prefer cache-driven downloads when the card is expanded
  const queryClient = useQueryClient();
  const downloadsTaskId = isUploadOnly ? null : task.task_id;
  const { data: dlData } = useDownloadsQuery(downloadsTaskId, !isUploadOnly && isExpanded);
  const dlItems: DownloadItem[] | undefined = dlData?.items;
  const transcriptQuery = useTranscriptQuery(downloadsTaskId, !isUploadOnly && isExpanded);
  void transcriptQuery;
  const hasVtt = !isPodcastTask && !isUploadOnly && hasCachedVtt(queryClient, task.task_id, transcriptLang);
  const progressPercent = Number.isFinite(task.completion_percentage)
    ? Math.max(0, Math.min(100, Math.round(task.completion_percentage ?? 0)))
    : null;
  const describeStepStatus = React.useCallback(
    (variant: StepStatusVariant) => getTaskStatusLabel(variant, t),
    [t],
  );
  const overallStatusVariant = normalizeStepStatus(task.status);
  const overallStatusLabel = describeStepStatus(overallStatusVariant);

  // Prefetch preview assets when expanded to improve responsiveness
  React.useEffect(() => {
    if (!isExpanded || isUploadOnly) return;
    (async () => {
      try {
        await prefetchTaskPreview(queryClient, task.task_id, { language: transcriptLang, podcast: isPodcastTask });
      } catch { /* ignore */ }
    })();
  }, [isExpanded, isPodcastTask, isUploadOnly, queryClient, task.task_id, transcriptLang]);

  const statusClass = getTaskStatusClass(task.status);
  const statusLabel = getTaskStatusLabel(task.status, t);
  const statusIcon = getTaskStatusIcon(task.status);
  const statusContent = `${statusIcon} ${statusLabel}`;
  const displayId = isUploadOnly
    ? task.upload_id || uploadMeta?.id || filename || task.task_id
    : task.task_id;
  const idLabel = isUploadOnly
    ? t('creations.file.idChip', { id: displayId ?? '-' }, `Upload ${displayId}`)
    : t('task.list.idPrefix', { id: displayId ?? '-' }, `Task: ${displayId}`);

  const languageLabel = (code: string) => {
    const normalized = (code || '').toLowerCase();
    return t(`language.display.${normalized}`, undefined, getLanguageDisplayName(code));
  };

  // Use unified file icon utility for consistency

  return (
    <div className={`task-item ${statusClass} ${isRemoving ? 'removing' : ''}`}>
      <div className="task-header">
        <div className="task-id">
          {/* Output badges inline before task id (one line) */}
          {!isUploadOnly && (isVideoTask || (dlItems?.some((d) => d.type === 'video') ?? false)) && (
            <span className="output-inline"><span className="output-dot video" aria-hidden></span>{t('task.list.videoLabel')}</span>
          )}
          {!isUploadOnly && (isPodcastTask || (dlItems?.some((d) => d.type === 'podcast') ?? false)) && (
            <span className="output-inline"><span className="output-dot podcast" aria-hidden></span>{t('task.list.podcastLabel')}</span>
          )}
          {!task.task_id && !isUploadOnly ? (
            <span className="task-id-link disabled" aria-disabled="true">
              {t('task.list.idPrefix', { id: 'unknown' }, `Task: Unknown`)}
            </span>
          ) : !isUploadOnly && task.status === 'completed' ? (
            <Link
              href={`/tasks/${task.task_id}`}
              className="task-id-link"
              title={t('task.list.openTaskTitle', { id: task.task_id }, `Open task ${task.task_id}`)}
              target="_blank"
              rel="noopener noreferrer"
            >
              {idLabel}
            </Link>
          ) : (
            <span
              className="task-id-link disabled"
              aria-disabled="true"
              title={displayId ? idLabel : undefined}
            >
              {idLabel}
            </span>
          )}
          {task.task_id && !isUploadOnly && (
            <button
              type="button"
              className="copy-task-id"
              aria-label={t('task.list.copyId')}
              title={t('task.list.copyId')}
              onClick={() => {
                try {
                  navigator.clipboard.writeText(task.task_id);
                } catch (error) {
                  console.warn('Failed to copy task ID to clipboard:', error);
                }
              }}
            >
              {t('actions.copy')}
            </button>
          )}
        </div>
        {task.status === 'processing' ? (
          <button
            type="button"
            className={`task-status ${statusClass}`}
            aria-label={t('task.list.statusAria', { status: statusLabel }, `Status: ${statusLabel}`)}
            title={t('processing.modal.openDetails', undefined, 'View processing details')}
            onClick={() => onShowProcessingDetails(task)}
          >
            {statusContent}
          </button>
        ) : (
          <div
            className={`task-status ${statusClass}`}
            tabIndex={0}
            aria-label={t('task.list.statusAria', { status: statusLabel }, `Status: ${statusLabel}`)}
          >
            {statusContent}
          </div>
        )}
      </div>

      <div className="task-details simple-details">
        <>
          {/* Queued note (lightweight, no pill) */}
          {task.status === 'queued' && (
            <div className="queued-note" role="status" aria-live="polite">{t('task.list.queuedMessage')}</div>
          )}
          <div className="task-filename" title={filename}>
            <span className="task-filename__icon" aria-hidden>{getFileTypeIcon(fileExt)}</span>
            <span className="task-filename__text">{filename}</span>
          </div>

          {/* Meta chips */}
          <div className="meta-row">
            <span className="chip">{t('task.list.voice', { language: languageLabel(voiceLang) }, `Voice: ${languageLabel(voiceLang)}`)}</span>
            {isPodcastTask ? (
              <span className="chip">{t('task.list.transcript', { language: languageLabel(transcriptLang) }, `Transcript: ${languageLabel(transcriptLang)}`)}</span>
            ) : (
              <span className="chip">{t('task.list.subtitles', { language: languageLabel(transcriptLang) }, `Subs: ${languageLabel(transcriptLang)}`)}</span>
            )}
            <span className="chip">{getVideoResolutionDisplayName(videoRes)}</span>
          </div>

          {isUploadOnly && (
            <div className="queued-note" role="status" aria-live="polite">
              {t('creations.upload.placeholder', undefined, 'Upload is ready. Run a new creation to get started.')}
            </div>
          )}

          {/* Progress shown only while processing */}
          {task.status === 'processing' && task.state && (
            <div className="step-progress">
              <div className="step-progress__meta">
                <span className={`step-progress__status step-progress__status--${overallStatusVariant}`}>
                  {overallStatusLabel}
                </span>
                {progressPercent !== null && (
                  <span className="step-progress__value">{progressPercent}%</span>
                )}
              </div>
              <div className="step-line" role="status" aria-live="polite">
                {formatStepNameWithLanguages(task.state.current_step, voiceLang, transcriptLang, t)}
              </div>
              {progressPercent !== null && (
                <div
                  className="progress-rail"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={progressPercent}
                  role="progressbar"
                >
                  <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
                </div>
              )}
            </div>
          )}

          {/* Exact steps timeline (shown while processing) */}
          {task.status === 'processing' && (task.state as any)?.steps && (
            <ul className="progress-steps" aria-label={t('processing.stepsHeading', undefined, 'Processing steps')}>
              {Object.entries((task.state as any).steps).map(([name, info]: any) => {
                const variant = normalizeStepStatus(info?.status);
                return (
                  <li key={name} className={`progress-step progress-step--${variant}`}>
                    <span className="progress-step__icon" aria-hidden>{STEP_STATUS_ICONS[variant]}</span>
                    <div className="progress-step__body">
                      <span className="progress-step__title">{getStepLabel(name, t)}</span>
                      <span className="progress-step__meta">{describeStepStatus(variant)}</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {/* Timestamps */}
         <div className="timestamps-row">
            <span className="timestamp">{t('task.list.createdStamp', { timestamp: new Date(task.created_at).toLocaleString() }, `Created: ${new Date(task.created_at).toLocaleString()}`)}</span>
            {task.status === 'completed' && (
              <span className="timestamp">{t('task.list.completedStamp', { timestamp: new Date(task.updated_at).toLocaleString() }, `Completed: ${new Date(task.updated_at).toLocaleString()}`)}</span>
            )}
          </div>

          {/* Downloads section removed from TaskCard as per new design - all download links should be found in task detail page */}
        </>
      </div>

      {isUploadOnly ? (
        <div className="task-actions placeholder-actions" />
      ) : (
        <div className="task-actions">
          {(task.status === 'queued' || task.status === 'processing') && (
            <button onClick={() => onCancel(task.task_id)} className="cancel-button">Cancel</button>
          )}
          {(task.status === 'completed' || task.status === 'cancelled' || task.status === 'failed') && (
            <button onClick={() => onDelete(task.task_id)} className="delete-button" title="Delete task" type="button" aria-label="Delete task">
              <svg className="icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.343.052.682.106 1.018.162m-1.018-.162L19.5 19.5A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 19.5L5.77 5.79m13.458 0a48.108 48.108 0 0 0-3.478-.397m-12 .559c.336-.056.675-.11 1.018-.162m0 0A48.11 48.11 0 0 1 9.25 5.25m5.5 0a48.11 48.11 0 0 1 3.482.342m-8.982-.342V4.5A1.5 1.5 0 0 1 10.25 3h3.5A1.5 1.5 0 0 1 15.25 4.5v.75m-8.982 0a48.667 48.667 0 0 0-3.538.397" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default TaskCard;

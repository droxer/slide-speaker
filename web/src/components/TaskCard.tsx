import React from 'react';
import { Link } from '@/navigation';
import { STEP_STATUS_ICONS, getStepLabel, normalizeStepStatus, StepStatusVariant } from '@/utils/stepLabels';
import { resolveLanguages, getLanguageDisplayName as displayName } from '@/utils/language';
import type { Task, DownloadItem } from '@/types';
import { useDownloadsQuery, useTranscriptQuery, hasCachedVtt, prefetchTaskPreview } from '@/services/queries';
import { useI18n } from '@/i18n/hooks';
import { useQueryClient } from '@tanstack/react-query';
import DownloadLinks, { DownloadLinkItem } from '@/components/DownloadLinks';

type Outputs = { video: boolean; podcast: boolean };

type Props = {
  task: Task;
  apiBaseUrl: string;
  isRemoving: boolean;
  isExpanded: boolean;
  onToggleDownloads: (task: Task) => void;
  onPreview: (task: Task, mode: 'video'|'audio') => void;
  onCancel: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  deriveTaskOutputs: (task: Task) => Outputs;
  getLanguageDisplayName: (code: string) => string;
  getVideoResolutionDisplayName: (res: string) => string;
};

// File type badge removed per new design

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'status-completed';
    case 'processing':
      return 'status-processing';
    case 'queued':
      return 'status-queued';
    case 'failed':
      return 'status-failed';
    case 'cancelled':
      return 'status-cancelled';
    default:
      return 'status-default';
  }
};

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
  onToggleDownloads,
  onPreview,
  onCancel,
  onDelete,
  deriveTaskOutputs,
  getLanguageDisplayName,
  getVideoResolutionDisplayName,
}) => {
  const { t } = useI18n();
  const { voiceLanguage: voiceLang, transcriptLanguage } = resolveLanguages(task);
  const videoRes = task.kwargs?.video_resolution || task.state?.video_resolution || 'hd';
  const { video: isVideoTask, podcast: isPodcastTask } = deriveTaskOutputs(task);
  const transcriptLang = transcriptLanguage;
  const filename = task.kwargs?.filename || task.state?.filename || 'Unknown file';
  // Prefer cache-driven downloads when the card is expanded
  const queryClient = useQueryClient();
  const { data: dlData } = useDownloadsQuery(task.task_id, isExpanded);
  const dlItems: DownloadItem[] | undefined = dlData?.items;
  const transcriptQuery = useTranscriptQuery(task.task_id, isExpanded);
  const hasVtt = !isPodcastTask && hasCachedVtt(queryClient, task.task_id, transcriptLang);
  const progressPercent = Number.isFinite(task.completion_percentage)
    ? Math.max(0, Math.min(100, Math.round(task.completion_percentage ?? 0)))
    : null;
  const describeStepStatus = React.useCallback((variant: StepStatusVariant) => {
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
  }, [t]);
  const overallStatusVariant = normalizeStepStatus(task.status);
  const overallStatusLabel = describeStepStatus(overallStatusVariant);

  const downloadLinks = React.useMemo(() => {
    const links: DownloadLinkItem[] = [];
    const hasVideoLink = isVideoTask || (dlItems?.some((d) => d.type === 'video') ?? false);
    const hasPodcastLink = dlItems?.some((d) => d.type === 'podcast') ?? isPodcastTask;

    if (hasVideoLink) {
      links.push({
        key: `video-${task.task_id}`,
        label: t('task.list.videoLabel'),
        url: `${apiBaseUrl}/api/tasks/${task.task_id}/video`,
        copyMessage: t('notifications.videoCopied'),
      });
    }

    links.push({
      key: `audio-${task.task_id}`,
      label: hasPodcastLink ? t('task.list.podcastLabel') : t('task.list.audioLabel'),
      url: `${apiBaseUrl}/api/tasks/${task.task_id}/${hasPodcastLink ? 'podcast' : 'audio'}`,
      copyMessage: hasPodcastLink ? t('notifications.podcastCopied') : t('notifications.audioCopied'),
    });

    if (transcriptQuery.isSuccess) {
      links.push({
        key: `transcript-${task.task_id}`,
        label: t('task.list.transcriptLabel'),
        url: `${apiBaseUrl}/api/tasks/${task.task_id}/transcripts/markdown`,
        copyMessage: t('notifications.transcriptCopied'),
      });
    }

    if (!isPodcastTask && hasVtt) {
      links.push({
        key: `vtt-${task.task_id}`,
        label: t('task.list.vttLabel'),
        url: `${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/vtt`,
        copyMessage: t('notifications.vttCopied'),
      });
      links.push({
        key: `srt-${task.task_id}`,
        label: t('task.list.srtLabel'),
        url: `${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/srt`,
        copyMessage: t('notifications.srtCopied'),
      });
    }

    return links;
  }, [
    apiBaseUrl,
    dlItems,
    hasVtt,
    isPodcastTask,
    isVideoTask,
    t,
    task.task_id,
    transcriptQuery.isSuccess,
  ]);

  // Prefetch preview assets when expanded to improve responsiveness
  React.useEffect(() => {
    if (!isExpanded) return;
    (async () => {
      try {
        await prefetchTaskPreview(queryClient, task.task_id, { language: transcriptLang, podcast: isPodcastTask });
      } catch { /* ignore */ }
    })();
  }, [isExpanded, isPodcastTask, queryClient, task.task_id, transcriptLang]);

  const humanStatus = (status: string) => t(`task.status.${status}`, undefined, status);
  const statusLabel = humanStatus(task.status);
  const statusIcon = task.status === 'processing'
    ? '⏳'
    : task.status === 'queued'
      ? '⏸️'
      : task.status === 'failed'
        ? '❌'
        : task.status === 'cancelled'
          ? '🚫'
          : '•';
  const statusContent = `${statusIcon} ${humanStatus(task.status)}`;

  return (
    <div className={`task-item ${getStatusColor(task.status)} ${isRemoving ? 'removing' : ''}`}>
      <div className="task-header">
        <div className="task-id">
          {/* Output badges inline before task id (one line) */}
          {(isVideoTask || (dlItems?.some((d) => d.type === 'video') ?? false)) && (
            <span className="output-inline"><span className="output-dot video" aria-hidden></span>{t('task.list.videoLabel')}</span>
          )}
          {(isPodcastTask || (dlItems?.some((d) => d.type === 'podcast') ?? false)) && (
            <span className="output-inline"><span className="output-dot podcast" aria-hidden></span>{t('task.list.podcastLabel')}</span>
          )}
          <Link
            href={`/tasks/${task.task_id}`}
            className="task-id-link"
            title={t('task.list.openTaskTitle', { id: task.task_id }, `Open task ${task.task_id}`)}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t('task.list.idPrefix', { id: task.task_id }, `Task: ${task.task_id}`)}
          </Link>
          <button
            type="button"
            className="copy-task-id"
            aria-label={t('task.list.copyId')}
            title={t('task.list.copyId')}
            onClick={() => {
              try {
                navigator.clipboard.writeText(task.task_id);
              } catch {}
            }}
          >
            {t('actions.copy')}
          </button>
        </div>
        {task.status !== 'completed' && task.status !== 'queued' && (
          <div
            className={`task-status ${getStatusColor(task.status)}`}
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
            <span className="task-filename__icon" aria-hidden>📄</span>
            <span className="task-filename__text">{filename}</span>
          </div>

          {/* Meta chips */}
          <div className="meta-row">
            <span className="chip">{t('task.list.voice', { language: displayName(voiceLang) }, `Voice: ${displayName(voiceLang)}`)}</span>
            {isPodcastTask ? (
              <span className="chip">{t('task.list.transcript', { language: displayName(transcriptLang) }, `Transcript: ${displayName(transcriptLang)}`)}</span>
            ) : (
              <span className="chip">{t('task.list.subtitles', { language: displayName(transcriptLang) }, `Subs: ${displayName(transcriptLang)}`)}</span>
            )}
            <span className="chip">{getVideoResolutionDisplayName(videoRes)}</span>
          </div>

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

          {/* Downloads toggle + block (native disclosure) */}
          <details
            className="downloads-panel"
            open={isExpanded}
            onToggle={() => onToggleDownloads(task)}
          >
            <summary className="toggle-summary" aria-controls={`downloads-${task.task_id}`} aria-expanded={isExpanded}>
              <span className="dl-icon" aria-hidden>⤓</span>
              <span className="toggle-text">
                {(() => {
                  const count = Array.isArray(dlItems) ? dlItems.length : undefined;
                  const base = t('task.list.downloads');
                  return `${base}${!isExpanded && count ? ` (${count})` : ''}`;
                })()}
              </span>
              <span className="chev" aria-hidden>▾</span>
            </summary>
            <DownloadLinks links={downloadLinks} id={`downloads-${task.task_id}`} />
          </details>
        </>
      </div>

      <div className="task-actions">
        {task.status === 'completed' && isVideoTask && (
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onPreview(task, 'video'); }}
            className="preview-button"
            title={t('actions.openPreview')}
            type="button"
          >
            {`▶️ ${t('task.preview.watch')}`}
          </button>
        )}
        {task.status === 'completed' && (isPodcastTask || isVideoTask) && (
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onPreview(task, 'audio'); }}
            className="preview-button"
            title={t('actions.openPreview')}
            type="button"
          >
            {`🎧 ${t('task.preview.listen')}`}
          </button>
        )}
        {(task.status === 'queued' || task.status === 'processing') && (
          <button onClick={() => onCancel(task.task_id)} className="cancel-button">Cancel</button>
        )}
        <button onClick={() => onDelete(task.task_id)} className="delete-button" title="Delete task" type="button" aria-label="Delete task">
          <svg className="icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.343.052.682.106 1.018.162m-1.018-.162L19.5 19.5A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 19.5L5.77 5.79m13.458 0a48.108 48.108 0 0 0-3.478-.397m-12 .559c.336-.056.675-.11 1.018-.162m0 0A48.11 48.11 0 0 1 9.25 5.25m5.5 0a48.11 48.11 0 0 1 3.482.342m-8.982-.342V4.5A1.5 1.5 0 0 1 10.25 3h3.5A1.5 1.5 0 0 1 15.25 4.5v.75m-8.982 0a48.667 48.667 0 0 0-3.538.397" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  );
};

export default TaskCard;

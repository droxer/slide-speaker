import React, { useMemo } from 'react';
import Link from 'next/link';
import VideoPlayer from '@/components/VideoPlayer';
import AudioPlayer from '@/components/AudioPlayer';
import type { Cue } from '@/components/TranscriptList';
import { getStepLabel } from '@/utils/stepLabels';
import { resolveLanguages, getLanguageDisplayName } from '@/utils/language';
import { buildCuesFromMarkdown } from '@/utils/transcript';
import { useTranscriptQuery } from '@/services/queries';
import type { Task, DownloadItem } from '@/types';

const formatDateTime = (value?: string) => {
  if (!value) return 'Unknown';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const buildAssetUrl = (baseUrl: string, path: string) => {
  if (!path) return '#';
  if (!baseUrl) return path;
  if (path.startsWith('http')) return path;
  return `${baseUrl}${path}`;
};

const statusLabel = (status: string) => {
  switch (status) {
    case 'completed':
      return 'Completed';
    case 'processing':
      return 'Processing';
    case 'queued':
      return 'Queued';
    case 'failed':
      return 'Failed';
    case 'cancelled':
      return 'Cancelled';
    default:
      return status.length ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
  }
};

const formatTaskType = (type?: string) => {
  if (!type) return 'Unknown';
  return type
    .split(/[_-]/)
    .map((word) => (word ? word.charAt(0).toUpperCase() + word.slice(1) : ''))
    .join(' ');
};

const downloadLabel = (type: string) => {
  const normalized = type?.toLowerCase?.() ?? '';
  switch (normalized) {
    case 'video':
      return 'Video';
    case 'audio':
      return 'Audio';
    case 'podcast':
      return 'Podcast';
    case 'transcript':
      return 'Transcript';
    case 'vtt':
      return 'VTT';
    case 'srt':
      return 'SRT';
    default:
      return normalized ? normalized.toUpperCase() : 'File';
  }
};

type TaskDetailProps = {
  task: Task;
  downloads?: DownloadItem[];
  apiBaseUrl: string;
  onCancel?: (taskId: string) => Promise<void>;
  isCancelling?: boolean;
  downloadsLoading?: boolean;
};

const TaskDetail: React.FC<TaskDetailProps> = ({
  task,
  downloads,
  apiBaseUrl,
  onCancel,
  isCancelling,
  downloadsLoading,
}) => {
  const { voiceLanguage, subtitleLanguage, transcriptLanguage } = resolveLanguages(task);
  const canCancel = typeof onCancel === 'function' && (task.status === 'processing' || task.status === 'queued');
  const captionLang = transcriptLanguage ?? subtitleLanguage;

  const taskType = String(task.task_type || '').toLowerCase();
  const filename = task.kwargs?.filename || task.state?.filename || 'Unknown file';
  const displayTaskType = formatTaskType(task.task_type);
  const hasVideoAsset = downloads?.some((item) => item.type === 'video') ?? false;
  const hasPodcastAsset = downloads?.some((item) => item.type === 'podcast') ?? false;
  const mediaType: 'video' | 'audio' = taskType === 'podcast' && !hasVideoAsset ? 'audio' : 'video';
  
  const videoUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/video`;
  const podcastUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/podcast`;
  const audioUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/audio`;
  const audioPreviewUrl = (taskType === 'podcast' || hasPodcastAsset) ? podcastUrl : audioUrl;
  const subtitleUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/vtt${captionLang ? `?language=${encodeURIComponent(captionLang)}` : ''}`;
  const transcriptQuery = useTranscriptQuery(task.task_id, mediaType === 'audio');
  const fallbackCues = useMemo(() => {
    if (mediaType !== 'audio' || !transcriptQuery.data) return undefined;
    return buildCuesFromMarkdown(transcriptQuery.data);
  }, [mediaType, transcriptQuery.data]);

  const steps = task.state?.steps ? Object.entries(task.state.steps) : [];

  return (
    <div className="task-detail-page">
      <div className="content-card wide task-detail-card">
        <header className="task-detail-card__header">
          <div className="task-detail-card__heading">
            <p className="task-detail-card__breadcrumb">
              <Link href="/creations">Creations</Link>
              <span aria-hidden> / </span>
              <span>Task</span>
            </p>
            <div className="task-detail-card__title-row">
              <h1>{filename}</h1>
              <span className="task-detail-card__type-pill">{displayTaskType}</span>
              <span className={`task-detail-card__status task-detail-card__status--${task.status}`}>
                {statusLabel(task.status)}
              </span>
            </div>
            <p className="task-detail-card__meta">
              <span>Task ID: {task.task_id}</span>
              <span aria-hidden>•</span>
              <span>{displayTaskType}</span>
            </p>
          </div>

          <div className="task-detail-card__actions">
            {canCancel && (
              <button
                type="button"
                className="task-detail-card__btn task-detail-card__btn--secondary"
                disabled={isCancelling}
                onClick={() => onCancel?.(task.task_id)}
              >
                {isCancelling ? 'Cancelling…' : 'Cancel Task'}
              </button>
            )}
          </div>
        </header>

        {task.status === 'processing' && task.state && (
          <section className="task-detail-card__section">
            <h2>Current Progress</h2>
            <p className="task-detail-card__progress-step">
              {getStepLabel(task.state.current_step)}
            </p>
            {typeof task.completion_percentage === 'number' && (
              <div
                className="task-detail-card__progressbar"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={task.completion_percentage}
              >
                <div style={{ width: `${Math.max(0, Math.min(100, task.completion_percentage))}%` }} />
              </div>
            )}
          </section>
        )}

        {steps.length > 0 && (
          <section className="task-detail-card__section">
            <h2>Steps</h2>
            <ol className="task-detail-card__steps">
              {steps.map(([name, info]) => {
                const stepStatus = String(info?.status || 'pending').toLowerCase();
                return (
                  <li key={name} className={`task-detail-card__step task-detail-card__step--${stepStatus}`}>
                    <span>{getStepLabel(name)}</span>
                    <span>{statusLabel(stepStatus)}</span>
                  </li>
                );
              })}
            </ol>
          </section>
        )}

        <section className="task-detail-card__section">
          <h2>{mediaType === 'video' ? 'Video Preview' : 'Podcast Preview'}</h2>
          <div className="task-detail-card__media">
            {mediaType === 'video' ? (
              <VideoPlayer
                className="task-detail-card__video"
                src={videoUrl}
                trackUrl={subtitleUrl}
                trackLang={captionLang || 'en'}
                trackLabel={`${getLanguageDisplayName(captionLang)} subtitles`}
                autoPlay={false}
              />
            ) : (
              <AudioPlayer
                className="task-detail-card__audio"
                src={audioPreviewUrl}
                initialCues={fallbackCues}
                showTranscript
              />
            )}
          </div>
        </section>

        <section className="task-detail-card__section task-detail-card__section--subtle">
          <div className="task-detail-card__facts" aria-label="Task Metadata">
            <div className="task-detail-card__fact-group">
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">Created</span>
                <span className="task-detail-card__fact-value">{formatDateTime(task.created_at)}</span>
              </div>
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">Updated</span>
                <span className="task-detail-card__fact-value">{formatDateTime(task.updated_at)}</span>
              </div>
            </div>
            <div className="task-detail-card__fact-group">
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">Voice</span>
                <span className="task-detail-card__fact-value">{getLanguageDisplayName(voiceLanguage)}</span>
              </div>
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">{taskType === 'podcast' ? 'Transcript' : 'Subtitles'}</span>
                <span className="task-detail-card__fact-value">{getLanguageDisplayName(transcriptLanguage ?? subtitleLanguage)}</span>
              </div>
            </div>
          </div>
        </section>

        <section className="task-detail-card__section">
          <h2>Downloads</h2>
          {downloadsLoading ? (
            <p className="task-detail-card__empty">Loading downloads…</p>
          ) : downloads && downloads.length > 0 ? (
            <div className="resource-links">
              {downloads.map((item) => {
                const href = buildAssetUrl(apiBaseUrl, item.download_url || item.url);
                const label = downloadLabel(item.type);
                return (
                  <div className="url-copy-row" key={`${item.type}-${href}`}>
                    <span className="resource-label-inline">{label}</span>
                    <input className="url-input-enhanced" type="text" value={href} readOnly />
                    <button
                      type="button"
                      className="copy-btn-enhanced"
                      onClick={() => {
                        try {
                          void navigator.clipboard.writeText(href);
                        } catch {}
                      }}
                    >
                      Copy
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="task-detail-card__empty">No downloads available yet.</p>
          )}
        </section>
      </div>
    </div>
  );
};

export default TaskDetail;

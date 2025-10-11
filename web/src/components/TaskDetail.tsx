'use client';

import React, { useMemo, useState, useEffect } from 'react';
import { Link } from '@/navigation';
import VideoPlayer from '@/components/VideoPlayer';
import AudioPlayer from '@/components/AudioPlayer';
import DownloadLinks, { DownloadLinkItem } from '@/components/DownloadLinks';
import type { Cue } from '@/components/TranscriptList';
import { STEP_STATUS_ICONS, normalizeStepStatus, getStepLabel } from '@/utils/stepLabels';
import { getTaskStatusClass, getTaskStatusIcon, getTaskStatusLabel } from '@/utils/taskStatus';
import { resolveLanguages, getLanguageDisplayName } from '@/utils/language';
import { buildCuesFromMarkdown } from '@/utils/transcript';
import { useTranscriptQuery } from '@/services/queries';
import { useI18n } from '@/i18n/hooks';
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

const formatTaskType = (type?: string) => {
  if (!type) return 'Unknown';
  return type
    .split(/[_-]/)
    .map((word) => (word ? word.charAt(0).toUpperCase() + word.slice(1) : ''))
    .join(' ');
};

const downloadLabel = (
  type: string,
  t: (key: string, vars?: Record<string, string | number>, fallback?: string) => string,
) => {
  const normalized = type?.toLowerCase?.() ?? '';
  switch (normalized) {
    case 'video':
      return t('task.list.videoLabel');
    case 'audio':
      return t('task.list.audioLabel');
    case 'podcast':
      return t('task.list.podcastLabel');
    case 'transcript':
      return t('task.list.transcriptLabel');
    case 'vtt':
      return t('task.list.vttLabel');
    case 'srt':
      return t('task.list.srtLabel');
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
  const { t, locale } = useI18n();
  const { voiceLanguage, subtitleLanguage, transcriptLanguage } = resolveLanguages(task);
  const languageLabel = React.useCallback((code: string) => {
    const normalized = (code || '').toLowerCase();
    return t(`language.display.${normalized}`, undefined, getLanguageDisplayName(code));
  }, [t]);
  const canCancel = typeof onCancel === 'function' && (task.status === 'processing' || task.status === 'queued');
  const captionLang = transcriptLanguage ?? subtitleLanguage;

  const taskType = String(task.task_type || '').toLowerCase();
  const filename = task.kwargs?.filename || task.state?.filename || 'Unknown file';
  const taskTypeKey = (task.task_type ?? '').toString().toLowerCase();
  const displayTaskType = t(
    `task.detail.type.${taskTypeKey || 'unknown'}`,
    undefined,
    formatTaskType(task.task_type),
  );
  const [previewTab, setPreviewTab] = useState<'video' | 'audio'>('video');
  const hasVideoAsset = downloads?.some((item) => item.type === 'video') ?? false;
  const hasPodcastAsset = downloads?.some((item) => item.type === 'podcast') ?? false;
  const hasAudioAsset = hasPodcastAsset || (downloads?.some((item) => item.type === 'audio') ?? false);
  const mediaType: 'video' | 'audio' = taskType === 'podcast' && !hasVideoAsset ? 'audio' : 'video';
  const availableTabs = useMemo<Array<'video' | 'audio'>>(() => {
    const tabs: Array<'video' | 'audio'> = [];
    if (mediaType === 'video' || hasVideoAsset) tabs.push('video');
    if (mediaType === 'audio' || hasAudioAsset || hasPodcastAsset || taskType !== 'podcast') tabs.push('audio');
    return tabs;
  }, [mediaType, hasVideoAsset, hasAudioAsset, hasPodcastAsset, taskType]);
  
  const videoUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/video`;
  const podcastUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/podcast`;
  const audioUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/audio`;
  const audioPreviewUrl = (taskType === 'podcast' || hasPodcastAsset) ? podcastUrl : audioUrl;
  const subtitleUrl = `${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/vtt${captionLang ? `?language=${encodeURIComponent(captionLang)}` : ''}`;
  const transcriptQuery = useTranscriptQuery(task.task_id, availableTabs.includes('audio'));
  const fallbackCues = useMemo(() => {
    if (!availableTabs.includes('audio') || !transcriptQuery.data) return undefined;
    return buildCuesFromMarkdown(transcriptQuery.data);
  }, [availableTabs, transcriptQuery.data]);

  useEffect(() => {
    if (!availableTabs.includes(previewTab) && availableTabs.length > 0) {
      setPreviewTab(availableTabs[0]);
    }
  }, [availableTabs, previewTab]);

  const steps = task.state?.steps ? Object.entries(task.state.steps) : [];

  return (
    <div className="task-detail-page">
      <div className="content-card wide task-detail-card">
        <header className="task-detail-card__header">
          <div className="task-detail-card__heading">
            <p className="task-detail-card__breadcrumb">
              <Link href="/creations" locale={locale}>{t('header.view.creations')}</Link>
              <span aria-hidden> / </span>
              <span>{t('task.detail.breadcrumb.task')}</span>
            </p>
            <div className="task-detail-card__title-row">
              <h1>{filename}</h1>
              <span className="task-detail-card__type-pill">{displayTaskType}</span>
              <div className={`task-status ${getTaskStatusClass(task.status)}`}>
                {getTaskStatusIcon(task.status)} {getTaskStatusLabel(task.status, t)}
              </div>
            </div>
            <p className="task-detail-card__meta">
              <span>Task ID: {task.task_id}</span>
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
                {isCancelling ? t('task.detail.cancelling') : t('task.detail.cancel')}
              </button>
            )}
          </div>
        </header>

        {task.status === 'processing' && task.state && (
          <section className="task-detail-card__section">
            <h2>{t('task.detail.currentProgress')}</h2>
            {(() => {
              const currentStepName = task.state.current_step;
              const currentStepStatus = normalizeStepStatus(task.state?.steps?.[currentStepName]?.status ?? 'processing');
              return (
                <div className="task-detail-card__progress-step">
                  <div className={`progress-step progress-step--${currentStepStatus}`}>
                    <span className="progress-step__icon" aria-hidden>{STEP_STATUS_ICONS[currentStepStatus]}</span>
                    <div className="progress-step__body">
                      <span className="progress-step__title">{getStepLabel(currentStepName, t)}</span>
                      <span className="progress-step__meta">{getTaskStatusLabel(currentStepStatus, t)}</span>
                    </div>
                  </div>
                </div>
              );
            })()}
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
            <h2>{t('task.detail.steps')}</h2>
            <ol className="task-detail-card__steps">
              {steps.map(([name, info]) => {
                const stepStatus = normalizeStepStatus(info?.status);
                return (
                  <li key={name} className={`progress-step progress-step--${stepStatus}`}>
                    <span className="progress-step__icon" aria-hidden>{STEP_STATUS_ICONS[stepStatus]}</span>
                    <div className="progress-step__body">
                      <span className="progress-step__title">{getStepLabel(name, t)}</span>
                      <span className="progress-step__meta">{getTaskStatusLabel(stepStatus, t)}</span>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        )}

        <section className="task-detail-card__section">
          <div className="mode-toggle compact" role="tablist" aria-label={t('task.detail.previewTabs', undefined, 'Preview')}>
            {availableTabs.includes('video') && (
              <button
                type="button"
                className={`toggle-btn ${previewTab === 'video' ? 'active' : ''}`}
                role="tab"
                aria-selected={previewTab === 'video'}
                onClick={() => setPreviewTab('video')}
              >
                🎬 {t('task.detail.videoPreview')}
              </button>
            )}
            {availableTabs.includes('audio') && (
              <button
                type="button"
                className={`toggle-btn ${previewTab === 'audio' ? 'active' : ''}`}
                role="tab"
                aria-selected={previewTab === 'audio'}
                onClick={() => setPreviewTab('audio')}
              >
                🎧 {(taskType === 'podcast' || hasPodcastAsset) ? t('task.detail.podcastPreview') : t('task.detail.audioPreview', undefined, 'Audio Preview')}
              </button>
            )}
          </div>

          <div className="task-detail-card__media" role="tabpanel" aria-label={previewTab === 'video' ? t('task.detail.videoPreview') : (taskType === 'podcast' || hasPodcastAsset) ? t('task.detail.podcastPreview') : t('task.detail.audioPreview', undefined, 'Audio Preview')}>
            {previewTab === 'video' && availableTabs.includes('video') && (
              <VideoPlayer
                className="task-detail-card__video"
                src={videoUrl}
                trackUrl={subtitleUrl}
                trackLang={captionLang || 'en'}
                trackLabel={`${languageLabel(captionLang || 'english')} ${t('task.detail.subtitles', undefined, 'Subtitles')}`}
                autoPlay={false}
              />
            )}
            {previewTab === 'audio' && availableTabs.includes('audio') && (
              <AudioPlayer
                className="task-detail-card__video task-detail-card__audio"
                src={audioPreviewUrl}
                vttUrl={!hasPodcastAsset ? subtitleUrl : undefined}
                initialCues={fallbackCues}
                showTranscript
              />
            )}
          </div>
        </section>

        <section className="task-detail-card__section task-detail-card__section--subtle">
          <div className="task-detail-card__facts" aria-label={t('task.detail.metadataAria', undefined, 'Task metadata')}>
            <div className="task-detail-card__fact-group">
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">{t('task.detail.voice')}</span>
                <span className="task-detail-card__fact-value">{getLanguageDisplayName(voiceLanguage, t)}</span>
              </div>
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">{taskType === 'podcast' ? t('task.detail.transcript') : t('task.detail.subtitlesFormats')}</span>
                <span className="task-detail-card__fact-value">{getLanguageDisplayName(transcriptLanguage ?? subtitleLanguage, t)}</span>
              </div>
            </div>
            <div className="task-detail-card__fact-group subtle-meta">
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">{t('task.detail.created')}</span>
                <span className="task-detail-card__fact-value subtle-meta__value">{formatDateTime(task.created_at)}</span>
              </div>
              <div className="task-detail-card__fact">
                <span className="task-detail-card__fact-label">{t('task.detail.updated')}</span>
                <span className="task-detail-card__fact-value subtle-meta__value">{formatDateTime(task.updated_at)}</span>
              </div>
            </div>
          </div>
        </section>

        <section className="task-detail-card__section">
          <h2>{t('task.detail.downloads')}</h2>
          {task.status === 'cancelled' ? (
            <p className="task-detail-card__empty">{t('task.detail.noDownloadsCancelled')}</p>
          ) : downloadsLoading ? (
            <p className="task-detail-card__empty">{t('task.detail.loadingDownloads')}</p>
          ) : downloads && downloads.length > 0 ? (
            <DownloadLinks
              links={downloads.map((item) => {
                const href = buildAssetUrl(apiBaseUrl, item.download_url || item.url);
                const label = downloadLabel(item.type, t);
                const typeKey = String(item.type || '').toLowerCase();
                const copyMessageKey = typeKey === 'podcast'
                  ? 'notifications.podcastCopied'
                  : typeKey === 'video'
                    ? 'notifications.videoCopied'
                    : typeKey === 'audio'
                      ? 'notifications.audioCopied'
                      : typeKey === 'transcript'
                        ? 'notifications.transcriptCopied'
                        : typeKey === 'vtt'
                          ? 'notifications.vttCopied'
                          : typeKey === 'srt'
                            ? 'notifications.srtCopied'
                            : undefined;
                return {
                  key: `${item.type}-${href}`,
                  label,
                  url: href,
                  copyLabel: t('actions.copy'),
                  copyMessage: copyMessageKey ? t(copyMessageKey) : undefined,
                } satisfies DownloadLinkItem;
              })}
            />
          ) : (
            <p className="task-detail-card__empty">{t('task.detail.noDownloads')}</p>
          )}
        </section>
      </div>
    </div>
  );
};

export default TaskDetail;

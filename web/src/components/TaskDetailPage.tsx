'use client';

import React, { useMemo, useState, useEffect } from 'react';
import { Link } from '@/navigation';
import VideoPlayer from '@/components/VideoPlayer';
import AudioPlayer from '@/components/AudioPlayer';
import PodcastPlayer from '@/components/PodcastPlayer';
import DownloadSection, { DownloadLinkItem } from '@/components/DownloadSection';
import { resolveLanguages, getLanguageDisplayName } from '@/utils/language';
import { usePodcastScriptQuery, prefetchTaskDetail } from '@/services/queries';
import { useI18n } from '@/i18n/hooks';
import { getTaskStatusClass, getTaskStatusIcon, getTaskStatusLabel } from '@/utils/taskStatus';
import type { Task, DownloadItem } from '@/types';
import { api as apiClient } from '@/services/client';

const formatDateTime = (value?: string) => {
  if (!value) return 'Unknown';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

// This function is no longer used since download URLs from the API are already complete paths

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
    case 'vtt_subtitles':
      return t('task.list.vttLabel');
    case 'srt_subtitles':
      return t('task.list.srtLabel');
    case 'subtitles':
    case 'subtitle':
      return t('task.list.subtitlesLabel', undefined, 'Subtitles');
    default:
      return normalized ? normalized.toUpperCase() : 'File';
  }
};

type TaskDetailPageProps = {
  task: Task;
  downloads?: DownloadItem[];
  apiBaseUrl: string;
};

const TaskDetailPage = ({
  task,
  downloads,
  apiBaseUrl,
}: TaskDetailPageProps) => {
  const { t, locale } = useI18n();
  const { voiceLanguage, subtitleLanguage, transcriptLanguage } = resolveLanguages(task);
  const languageLabel = React.useCallback((code: string) => {
    const normalized = (code || '').toLowerCase();
    return t(`language.display.${normalized}`, undefined, getLanguageDisplayName(code));
  }, [t]);
  const captionLang = transcriptLanguage ?? subtitleLanguage;

  // Prefetch related task data for better navigation experience
  React.useEffect(() => {
    // In a real implementation, you might want to prefetch data for related tasks
    // or adjacent tasks in the list for smoother navigation
  }, [task.task_id]);

  const taskType = String(task.task_type || '').toLowerCase();
  const filename =
    task.filename ||
    task.kwargs?.filename ||
    task.state?.filename ||
    task.kwargs?.upload_id ||
    task.upload_id;
  const taskTypeKey = (task.task_type ?? '').toString().toLowerCase();
  const displayTaskType = t(
    `task.detail.type.${taskTypeKey || 'unknown'}`,
    undefined,
    formatTaskType(task.task_type),
  );

  // Get consistent status styling using utility functions
  const statusClass = getTaskStatusClass(task.status);
  const statusIcon = getTaskStatusIcon(task.status);
  const statusLabel = getTaskStatusLabel(task.status, t);
  const statusContent = `${statusIcon} ${statusLabel}`;
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
  
  const pathFor = (path: string) => {
    try {
      const base = apiClient.defaults.baseURL || apiBaseUrl;
      // If we have a base URL, construct the full URL properly
      if (base) {
        // Ensure path starts with '/'
        const normalizedPath = path.startsWith('/') ? path : `/${path}`;
        return new URL(normalizedPath, base).toString();
      }
      // If no base URL, return path directly but ensure it starts with '/'
      return path.startsWith('/') ? path : `/${path}`;
    } catch {
      // Fallback: ensure path starts with '/' and concatenate with apiBaseUrl
      const normalizedPath = path.startsWith('/') ? path : `/${path}`;
      if (!apiBaseUrl || apiBaseUrl === '/') return normalizedPath;
      const normalizedBaseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
      return `${normalizedBaseUrl}${normalizedPath}`;
    }
  };

  const videoUrl = pathFor(`/api/tasks/${task.task_id}/video`);
  const podcastUrl = pathFor(`/api/tasks/${task.task_id}/podcast`);
  const audioUrl = pathFor(`/api/tasks/${task.task_id}/audio`);
  const audioPreviewUrl = (taskType === 'podcast' || hasPodcastAsset) ? podcastUrl : audioUrl;
  const subtitleUrl = pathFor(`/api/tasks/${task.task_id}/subtitles/vtt${captionLang ? `?language=${encodeURIComponent(captionLang)}` : ''}`);
  const podcastScriptQuery = usePodcastScriptQuery(task.task_id, availableTabs.includes('audio') && hasPodcastAsset);

  useEffect(() => {
    if (!availableTabs.includes(previewTab) && availableTabs.length > 0) {
      setPreviewTab(availableTabs[0]);
    }
  }, [availableTabs, previewTab]);

  const filteredDownloads = React.useMemo(() => {
    if (!downloads) return [];
    return downloads.filter((item) => {
      if (String(item.type || '').toLowerCase() !== 'transcript') return true;
      return taskType === 'podcast';
    });
  }, [downloads, taskType]);

  return (
    <div className="task-detail-page">
      <div className="content-card wide task-detail-card">
        <header className="task-detail-card__header">
          <div className="task-detail-card__heading">
            <p className="task-detail-card__breadcrumb">
              <Link href="/creations" locale={locale}>{t('header.view.creations')}</Link>
              <span aria-hidden="true"> / </span>
              <span>{t('task.detail.breadcrumb.task')}</span>
            </p>
            <div className="task-detail-card__title-row">
              <h1>{filename}</h1>
              <span className="task-detail-card__type-pill">{displayTaskType}</span>
              <div className={`task-status ${statusClass}`}>
                {statusContent}
              </div>
            </div>
            <p className="task-detail-card__meta">
              <span>Task ID: {task.task_id}</span>
            </p>
          </div>
        </header>

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
              hasPodcastAsset ? (
                <PodcastPlayer
                  className="task-detail-card__audio"
                  src={audioPreviewUrl}
                  script={podcastScriptQuery.data}
                />
              ) : (
                <AudioPlayer
                  className="task-detail-card__audio"
                  src={audioPreviewUrl}
                  vttUrl={taskType === 'podcast' ? undefined : subtitleUrl}
                  showTranscript
                />
              )
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
          {filteredDownloads.length > 0 ? (
            <DownloadSection
              links={filteredDownloads.map((item) => {
                // Construct full URLs by combining the API base URL with the relative paths from the API
                const baseUrl = apiClient.defaults.baseURL || apiBaseUrl || '';
                const path = item.download_url || item.url;
                // Ensure path starts with '/' and construct full URL
                const normalizedPath = path.startsWith('/') ? path : `/${path}`;
                const fullUrl = baseUrl ? `${baseUrl.replace(/\/+$/, '')}${normalizedPath}` : normalizedPath;

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
                  key: `${item.type}-${fullUrl}`,
                  label,
                  url: fullUrl,
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

export default TaskDetailPage;

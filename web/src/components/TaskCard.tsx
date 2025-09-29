import React from 'react';
import Link from 'next/link';
import { getStepLabel } from '@/utils/stepLabels';
import { resolveLanguages, getLanguageDisplayName as displayName } from '@/utils/language';
import type { Task, DownloadItem } from '@/types';
import { useDownloadsQuery, useTranscriptQuery, hasCachedVtt, prefetchTaskPreview } from '@/services/queries';
import { useQueryClient } from '@tanstack/react-query';

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

const formatStepNameWithLanguages = (step: string, voiceLang: string, subtitleLang?: string): string => {
  const vl = (voiceLang || 'english').toLowerCase();
  const sl = (subtitleLang || vl).toLowerCase();
  const same = vl === sl;
  if (same && (step === 'translate_voice_transcripts' || step === 'translate_subtitle_transcripts')) {
    return 'Translating Transcripts';
  }
  return getStepLabel(step);
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

  // Prefetch preview assets when expanded to improve responsiveness
  React.useEffect(() => {
    if (!isExpanded) return;
    (async () => {
      try {
        await prefetchTaskPreview(queryClient, task.task_id, { language: transcriptLang, podcast: isPodcastTask });
      } catch { /* ignore */ }
    })();
  }, [isExpanded, isPodcastTask, queryClient, task.task_id, transcriptLang]);

  const statusLabel = (
    task.status === 'completed' ? 'Completed' :
    task.status === 'processing' ? 'Processing' :
    task.status === 'queued' ? 'Queued' :
    task.status === 'failed' ? 'Failed' :
    task.status === 'cancelled' ? 'Cancelled' : String(task.status)
  );
  const statusContent = (
    task.status === 'processing' ? '⏳ Processing' :
    task.status === 'queued' ? '⏸️ Queued' :
    task.status === 'failed' ? '❌ Failed' :
    task.status === 'cancelled' ? '🚫 Cancelled' : String(task.status)
  );

  return (
    <div className={`task-item ${getStatusColor(task.status)} ${isRemoving ? 'removing' : ''}`}>
      <div className="task-header">
        <div className="task-id">
          {/* Output badges inline before task id (one line) */}
          {(isVideoTask || (dlItems?.some((d) => d.type === 'video') ?? false)) && (
            <span className="output-inline"><span className="output-dot video" aria-hidden></span>Video</span>
          )}
          {(isPodcastTask || (dlItems?.some((d) => d.type === 'podcast') ?? false)) && (
            <span className="output-inline"><span className="output-dot podcast" aria-hidden></span>Podcast</span>
          )}
          <Link
            href={`/tasks/${task.task_id}`}
            className="task-id-link"
            title={`Open task ${task.task_id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Task: {task.task_id}
          </Link>
          <button
            type="button"
            className="copy-task-id"
            aria-label="Copy task ID"
            title="Copy task ID"
            onClick={() => {
              try {
                navigator.clipboard.writeText(task.task_id);
              } catch {}
            }}
          >
            Copy
          </button>
        </div>
        {task.status !== 'completed' && task.status !== 'queued' && (
          <div
            className={`task-status ${getStatusColor(task.status)}`}
            tabIndex={0}
            aria-label={`Status: ${statusLabel}`}
          >
            {statusContent}
          </div>
        )}
      </div>

      <div className="task-details simple-details">
        <>
          {/* Queued note (lightweight, no pill) */}
          {task.status === 'queued' && (
            <div className="queued-note" role="status" aria-live="polite">Queued • Waiting to start</div>
          )}
          <div className="task-filename" title={filename}>
            <span className="task-filename__icon" aria-hidden>📄</span>
            <span className="task-filename__text">{filename}</span>
          </div>

          {/* Meta chips */}
          <div className="meta-row">
            <span className="chip">Voice: {displayName(voiceLang)}</span>
            {isPodcastTask ? (
              <span className="chip">Transcript: {displayName(transcriptLang)}</span>
            ) : (
              <span className="chip">Subs: {displayName(transcriptLang)}</span>
            )}
            <span className="chip">{getVideoResolutionDisplayName(videoRes)}</span>
          </div>

          {/* Progress shown only while processing */}
          {task.status === 'processing' && task.state && (
            <div className="step-progress">
              <div className="step-line" role="status" aria-live="polite">
                {formatStepNameWithLanguages(task.state.current_step, voiceLang, transcriptLang)}
              </div>
              {typeof task.completion_percentage === 'number' && (
                <div className="progress-rail" aria-valuemin={0} aria-valuemax={100} aria-valuenow={task.completion_percentage} role="progressbar">
                  <div className="progress-fill" style={{ width: `${Math.max(0, Math.min(100, task.completion_percentage))}%` }} />
                </div>
              )}
            </div>
          )}

          {/* Exact steps timeline (shown while processing) */}
          {task.status === 'processing' && (task.state as any)?.steps && (
            <ul className="steps-timeline" aria-label="Processing steps">
              {Object.entries((task.state as any).steps).map(([name, info]: any) => {
                const s = (info?.status || 'pending').toLowerCase();
                const icon = s === 'completed' ? '✓' : s === 'processing' ? '⏳' : s === 'failed' ? '❌' : s === 'cancelled' ? '⛔' : s === 'skipped' ? '⤼' : '•';
                return (
                  <li key={name} className={`step-item s-${s}`}><span className="step-icon" aria-hidden>{icon}</span><span className="step-name">{getStepLabel(name)}</span></li>
                );
              })}
            </ul>
          )}

          {/* Timestamps */}
          <div className="timestamps-row">
            <span className="timestamp">Created: {new Date(task.created_at).toLocaleString()}</span>
            {task.status === 'completed' && (
              <span className="timestamp">Completed: {new Date(task.updated_at).toLocaleString()}</span>
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
                  return `Downloads${!isExpanded && count ? ` (${count})` : ''}`;
                })()}
              </span>
              <span className="chev" aria-hidden>▾</span>
            </summary>
            <div className="resource-links" id={`downloads-${task.task_id}`}>
                {(dlItems?.some((d) => d.type === 'video') ?? isVideoTask) && (
                  <div className="url-copy-row">
                    <span className="resource-label-inline">Video</span>
                    <input type="text" value={`${apiBaseUrl}/api/tasks/${task.task_id}/video`} readOnly className="url-input-enhanced" />
                    <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/video`); alert('Video URL copied!'); }} className="copy-btn-enhanced">Copy</button>
                  </div>
                )}

                <div className="url-copy-row">
                  <span className="resource-label-inline">{(dlItems?.some((d) => d.type === 'podcast') ?? isPodcastTask) ? 'Podcast' : 'Audio'}</span>
                  <input type="text" value={`${apiBaseUrl}/api/tasks/${task.task_id}/${(dlItems?.some((d) => d.type === 'podcast') ?? isPodcastTask) ? 'podcast' : 'audio'}`} readOnly className="url-input-enhanced" />
                  <button onClick={() => { const isPod = (dlItems?.some((d) => d.type === 'podcast') ?? isPodcastTask); navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/${isPod ? 'podcast' : 'audio'}`); alert(`${isPod ? 'Podcast' : 'Audio'} URL copied!`); }} className="copy-btn-enhanced">Copy</button>
                </div>

                {transcriptQuery.isSuccess && (
                  <div className="url-copy-row">
                    <span className="resource-label-inline">Transcript</span>
                    <input type="text" value={`${apiBaseUrl}/api/tasks/${task.task_id}/transcripts/markdown`} readOnly className="url-input-enhanced" />
                    <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/transcripts/markdown`); alert('Transcript URL copied!'); }} className="copy-btn-enhanced">Copy</button>
                  </div>
                )}

                {!isPodcastTask && hasVtt && (
                  <>
                    <div className="url-copy-row">
                      <span className="resource-label-inline">VTT</span>
                      <input type="text" value={`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/vtt`} readOnly className="url-input-enhanced" />
                      <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/vtt`); alert('VTT URL copied!'); }} className="copy-btn-enhanced">Copy</button>
                    </div>
                    <div className="url-copy-row">
                      <span className="resource-label-inline">SRT</span>
                      <input type="text" value={`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/srt`} readOnly className="url-input-enhanced" />
                      <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/srt`); alert('SRT URL copied!'); }} className="copy-btn-enhanced">Copy</button>
                    </div>
                  </>
                )}
            </div>
          </details>
        </>
      </div>

      <div className="task-actions">
        {task.status === 'completed' && isVideoTask && (
          <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); onPreview(task, 'video'); }} className="preview-button" title="Open preview" type="button">▶️ Watch</button>
        )}
        {task.status === 'completed' && (isPodcastTask || isVideoTask) && (
          <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); onPreview(task, 'audio'); }} className="preview-button" title="Open preview" type="button">🎧 Listen</button>
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

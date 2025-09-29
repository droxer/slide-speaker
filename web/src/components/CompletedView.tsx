import React from 'react';
import VideoPlayer from './VideoPlayer';
import AudioPlayer from './AudioPlayer';
import PodcastPlayer from './PodcastPlayer';
import { getLanguageDisplayName } from '../utils/language';

type CompletedViewProps = {
  apiBaseUrl: string;
  taskId: string;
  processingDetails: any;
  hasVideoAsset: boolean;
  completedTranscriptMd: string | null;
  subtitleLanguageCode: string;
  subtitleLocale: string;
  vttUrl: string;
  completedMedia: 'video' | 'audio';
  setCompletedMedia: (m: 'video' | 'audio') => void;
  completedMediaPinnedRef: React.MutableRefObject<boolean>;
  showCompletedBanner: boolean;
  setShowCompletedBanner: (v: boolean) => void;
  onResetForm: () => void;
};

const CompletedView: React.FC<CompletedViewProps> = ({
  apiBaseUrl,
  taskId,
  processingDetails,
  hasVideoAsset,
  completedTranscriptMd,
  subtitleLanguageCode,
  subtitleLocale,
  vttUrl,
  completedMedia,
  setCompletedMedia,
  completedMediaPinnedRef,
  showCompletedBanner,
  setShowCompletedBanner,
  onResetForm,
}) => {
  const [completedVideoLoading, setCompletedVideoLoading] = React.useState<boolean>(false);

  const taskType = String((processingDetails as any)?.task_type || '').toLowerCase();
  const filename =
    (processingDetails as any)?.filename ||
    (processingDetails as any)?.kwargs?.filename ||
    (processingDetails as any)?.state?.filename ||
    null;

  return (
    <div className="completed-view">
      {showCompletedBanner && (
        <div className="completed-banner">
          <div className="success-icon">✓</div>
          <h3>
            Your Masterpiece is Ready!
            <span style={{ marginLeft: 8 }} className="output-badges" aria-label="Outputs included">
              {["video","both"].includes(taskType) && (
                <span className="output-pill video" title="Includes video">🎬 Video</span>
              )}
              {["podcast","both"].includes(taskType) && (
                <span className="output-pill podcast" title="Includes podcast">🎧 Podcast</span>
              )}
            </span>
          </h3>
          <p className="success-message">Congratulations! Your presentation has been transformed into an engaging AI-powered video.</p>
          <button
            type="button"
            className="banner-dismiss"
            aria-label="Dismiss banner"
            onClick={() => {
              setShowCompletedBanner(false);
              try { localStorage.setItem('ss_show_completed_banner', '0'); } catch {}
            }}
          >
            ✕
          </button>
        </div>
      )}

      {filename && (
        <div className="completed-filename" title={filename}>
          <span className="completed-filename__icon" aria-hidden>📄</span>
          <span className="completed-filename__text">{filename}</span>
        </div>
      )}

      <div className="mode-toggle-container">
        <div className="mode-toggle-header" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }} />
        <div className="mode-toggle compact">
          {(["video","both"].includes(taskType) || hasVideoAsset) && (
            <button
              type="button"
              className={`toggle-btn ${completedMedia === 'video' ? 'active' : ''}`}
              onClick={() => { completedMediaPinnedRef.current = true; setCompletedMedia('video'); }}
            >
              🎬 Video
            </button>
          )}
          <button
            type="button"
            className={`toggle-btn ${completedMedia === 'audio' ? 'active' : ''}`}
            onClick={() => { completedMediaPinnedRef.current = true; setCompletedMedia('audio'); }}
          >
            {["podcast","both"].includes(taskType) ? '🎧 Podcast' : '🎧 Audio'}
          </button>
        </div>
      </div>

      {completedMedia === 'video' && ((["video","both"].includes(taskType) || hasVideoAsset)) && (
        <div className="media-section video-active">
          <div className="video-wrapper">
            <VideoPlayer
              className="preview-video-large"
              src={`${apiBaseUrl}/api/tasks/${taskId}/video`}
              trackUrl={vttUrl}
              trackLang={subtitleLocale}
              trackLabel={getLanguageDisplayName(subtitleLanguageCode)}
              onReady={() => setCompletedVideoLoading(false)}
              onError={() => setCompletedVideoLoading(false)}
            />
            {completedVideoLoading && (
              <div className="video-status-overlay loading" role="status" aria-live="polite">
                <div className="spinner" aria-hidden></div>
                <span className="loading-text">Loading video…</span>
              </div>
            )}
          </div>
        </div>
      )}

      {completedMedia === 'audio' && (
        <div className="media-section audio-active">
          <div className="audio-section" style={{ position: 'relative' }}>
            <div className="audio-player-inline">
              {(() => {
                const isPodcast = ["podcast","both"].includes(taskType);
                const audioUrl = `${apiBaseUrl}/api/tasks/${taskId}/${isPodcast ? 'podcast' : 'audio'}`;
                const vttUrlLocal = `${apiBaseUrl}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguageCode)}`;
                return isPodcast ? (
                  <PodcastPlayer src={audioUrl} transcriptMarkdown={completedTranscriptMd ?? ''} />
                ) : (
                  <AudioPlayer src={audioUrl} vttUrl={vttUrlLocal} />
                );
              })()}
            </div>
          </div>
        </div>
      )}

      <div className="resource-links">
        {/* Video */}
        {(["video","both"].includes(taskType) || hasVideoAsset) && (
          <div className="url-copy-row">
            <span className="resource-label-inline">Video</span>
            <input type="text" value={`${apiBaseUrl}/api/tasks/${taskId}/video`} readOnly className="url-input-enhanced" />
            <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${taskId}/video`); alert('Video URL copied!'); }} className="copy-btn-enhanced">Copy</button>
          </div>
        )}
        {/* Audio/Podcast */}
        <div className="url-copy-row">
          <span className="resource-label-inline">{["podcast","both"].includes(taskType) ? 'Podcast' : 'Audio'}</span>
          <input type="text" value={`${apiBaseUrl}/api/tasks/${taskId}/${["podcast","both"].includes(taskType) ? 'podcast' : 'audio'}`} readOnly className="url-input-enhanced" />
          <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${taskId}/${["podcast","both"].includes(taskType) ? 'podcast' : 'audio'}`); alert(`${["podcast","both"].includes(taskType) ? 'Podcast' : 'Audio'} URL copied!`); }} className="copy-btn-enhanced">Copy</button>
        </div>
        {/* Transcript */}
        <div className="url-copy-row">
          <span className="resource-label-inline">Transcript</span>
          <input type="text" value={`${apiBaseUrl}/api/tasks/${taskId}/transcripts/markdown`} readOnly className="url-input-enhanced" />
          <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${taskId}/transcripts/markdown`); alert('Transcript URL copied!'); }} className="copy-btn-enhanced">Copy</button>
        </div>
        {/* VTT (hide for podcast-only) */}
        {!(["podcast","both"].includes(taskType)) && (
          <div className="url-copy-row">
            <span className="resource-label-inline">VTT</span>
            <input type="text" value={`${apiBaseUrl}/api/tasks/${taskId}/subtitles/vtt`} readOnly className="url-input-enhanced" />
            <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${taskId}/subtitles/vtt`); alert('VTT URL copied!'); }} className="copy-btn-enhanced">Copy</button>
          </div>
        )}
        {/* SRT (hide for podcast-only) */}
        {!(["podcast","both"].includes(taskType)) && (
          <div className="url-copy-row">
            <span className="resource-label-inline">SRT</span>
            <input type="text" value={`${apiBaseUrl}/api/tasks/${taskId}/subtitles/srt`} readOnly className="url-input-enhanced" />
            <button onClick={() => { navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${taskId}/subtitles/srt`); alert('SRT URL copied!'); }} className="copy-btn-enhanced">Copy</button>
          </div>
        )}
      </div>

      <div className="completed-cta-bottom">
        <button onClick={onResetForm} className="primary-btn" type="button">Create Another Project</button>
      </div>
    </div>
  );
};

export default CompletedView;

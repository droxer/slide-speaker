import React, { useMemo } from 'react';
import { useI18n } from '@/i18n/hooks';
import { getLanguageDisplayName } from '../utils/language';
import { getFileTypeIcon } from '@/utils/fileIcons';

type UploadPanelProps = {
  uploadMode: 'slides' | 'pdf';
  setUploadMode: (v: 'slides' | 'pdf') => void;
  pdfOutputMode: 'video' | 'podcast';
  setPdfOutputMode: (v: 'video' | 'podcast') => void;
  file: File | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  voiceLanguage: string;
  setVoiceLanguage: (v: string) => void;
  subtitleLanguage: string;
  setSubtitleLanguage: (v: string) => void;
  transcriptLanguage: string;
  setTranscriptLanguage: (v: string) => void;
  setTranscriptLangTouched: (v: boolean) => void;
  videoResolution: string;
  setVideoResolution: (v: string) => void;
  uploading: boolean;
  onCreate: () => void;
  getFileTypeHint: (filename: string) => React.JSX.Element;
};

const LANGS = [
  'english',
  'simplified_chinese',
  'traditional_chinese',
  'japanese',
  'korean',
  'thai',
];

const UploadPanel = ({
  uploadMode,
  setUploadMode,
  pdfOutputMode,
  setPdfOutputMode,
  file,
  onFileChange,
  voiceLanguage,
  setVoiceLanguage,
  subtitleLanguage,
  setSubtitleLanguage,
  transcriptLanguage,
  setTranscriptLanguage,
  setTranscriptLangTouched,
  videoResolution,
  setVideoResolution,
  uploading,
  onCreate,
  getFileTypeHint,
}: UploadPanelProps) => {
  const { t } = useI18n();
  const subtitleTitle = uploadMode === 'pdf' && pdfOutputMode === 'podcast'
    ? t('runTask.transcriptLanguage')
    : t('runTask.subtitleLanguage');

  const displayLanguage = (code: string) => {
    const normalized = (code || '').toLowerCase();
    const fallback = getLanguageDisplayName(code);
    return t(`language.display.${normalized}`, undefined, fallback || t('common.unknown', undefined, 'Unknown'));
  };

  const fileLabel = useMemo(() => {
    if (file) return file.name;
    return uploadMode === 'pdf'
      ? t('upload.file.choosePdf', undefined, 'Choose a PDF file')
      : t('upload.file.chooseSlides', undefined, 'Choose a PPTX/PPT file');
  }, [file, t, uploadMode]);

  const fileHint = useMemo(() => {
    if (file) return getFileTypeHint(file.name);
    return uploadMode === 'pdf'
      ? t('upload.file.hintPdf', undefined, 'PDF will be processed into a video or podcast')
      : t('upload.file.hintSlides', undefined, 'Slides will be processed into a narrated video');
  }, [file, getFileTypeHint, t, uploadMode]);

  const pdfCreateLabel = pdfOutputMode === 'podcast'
    ? t('upload.createPodcast', undefined, 'Create Podcast')
    : t('upload.createVideo', undefined, 'Create Video');

  return (
    <>
      <div className="upload-view">
        <div className="mode-toggle" role="tablist" aria-label={t('upload.modeToggle.aria', undefined, 'Entry Mode')}>
          <button
            type="button"
            className={`toggle-btn ${uploadMode === 'slides' ? 'active' : ''}`}
            onClick={() => setUploadMode('slides')}
            role="tab"
            aria-selected={uploadMode === 'slides'}
            aria-controls="slides-mode-panel"
          >
            🖼️ {t('upload.mode.slides', undefined, 'Slides')}
          </button>
          <button
            type="button"
            className={`toggle-btn ${uploadMode === 'pdf' ? 'active' : ''}`}
            onClick={() => setUploadMode('pdf')}
            role="tab"
            aria-selected={uploadMode === 'pdf'}
            aria-controls="pdf-mode-panel"
          >
            📄 {t('upload.mode.pdf', undefined, 'PDF')}
          </button>
        </div>
        <div className="mode-explainer" aria-live="polite">
          {uploadMode === 'slides' ? (
            <>
              <strong>{t('upload.mode.slidesHeading', undefined, 'Slides Mode:')}</strong> {t('upload.mode.slidesDescription', undefined, 'Processes each slide individually for transcripts, audio, subtitles, and composes a final video.')}
            </>
          ) : (
            <>
              <strong>{t('upload.mode.pdfHeading', undefined, 'PDF Mode:')}</strong> {t('upload.mode.pdfDescription', undefined, 'Segments the document into chapters; generate a video (audio + subtitles) or a two-speaker podcast (MP3).')}
            </>
          )}
        </div>
        {uploadMode === 'pdf' && (
          <div className="mode-toggle" role="tablist" aria-label={t('upload.pdfOutput.aria', undefined, 'PDF Output')}>
            <button
              type="button"
              className={`toggle-btn ${pdfOutputMode === 'video' ? 'active' : ''}`}
              onClick={() => setPdfOutputMode('video')}
              role="tab"
              aria-selected={pdfOutputMode === 'video'}
              aria-controls="pdf-output-video"
            >
              🎬 {t('task.list.videoLabel')}
            </button>
            <button
              type="button"
              className={`toggle-btn ${pdfOutputMode === 'podcast' ? 'active' : ''}`}
              onClick={() => setPdfOutputMode('podcast')}
              role="tab"
              aria-selected={pdfOutputMode === 'podcast'}
              aria-controls="pdf-output-podcast"
            >
              🎧 {t('task.list.podcastLabel')}
            </button>
          </div>
        )}
        <div className="file-upload-area">
          <input
            type="file"
            id="file-upload"
            accept={uploadMode === 'pdf' ? '.pdf' : '.pptx,.ppt'}
            onChange={onFileChange}
            className="file-input"
          />
          <label htmlFor="file-upload" className="file-upload-label">
            <div className="upload-section-header">
              <span className="upload-section-icon">📁</span>
              <span className="upload-section-title">{uploadMode === 'pdf' ? 'PDF Document' : 'Presentation Slides'}</span>
            </div>
            <div className="upload-icon">
              {getFileTypeIcon(file?.name || '')}
            </div>
            <div className="upload-text">{fileLabel}</div>
            <div className="upload-hint">{fileHint}</div>
          </label>
        </div>

        <div className="options-panel">
          <div className="video-option-card">
            <div className="video-option-header">
              <span className="video-option-icon">🌐</span>
              <span className="video-option-title">{t('runTask.voiceLanguage')}</span>
            </div>
            <select id="voice-language-select" value={voiceLanguage} onChange={(e) => setVoiceLanguage(e.target.value)} className="video-option-select">
              {LANGS.map((code) => (
                <option key={code} value={code}>{getLanguageDisplayName(code, t)}</option>
              ))}
            </select>
          </div>

          <div className="video-option-card">
            <div className="video-option-header">
              <span className="video-option-icon">📝</span>
              <span className="video-option-title">{subtitleTitle}</span>
            </div>
            <select
              id="subtitle-language-select"
              value={uploadMode === 'pdf' && pdfOutputMode === 'podcast' ? transcriptLanguage : subtitleLanguage}
              onChange={(e) => {
                const v = e.target.value;
                if (uploadMode === 'pdf' && pdfOutputMode === 'podcast') {
                  setTranscriptLanguage(v);
                  setTranscriptLangTouched(true);
                } else {
                  setSubtitleLanguage(v);
                }
              }}
              className="video-option-select"
            >
              {LANGS.map((code) => (
                <option key={code} value={code}>{getLanguageDisplayName(code, t)}</option>
              ))}
            </select>
          </div>

          {(uploadMode !== 'pdf' || pdfOutputMode === 'video') && (
            <div className="video-option-card">
              <div className="video-option-header">
                <span className="video-option-icon">📺</span>
                <span className="video-option-title">{t('runTask.videoResolution')}</span>
              </div>
              <select id="video-resolution-select" value={videoResolution} onChange={(e) => setVideoResolution(e.target.value)} className="video-option-select">
                <option value="sd">{t('runTask.resolution.sd')}</option>
                <option value="hd">{t('runTask.resolution.hd')}</option>
                <option value="fullhd">{t('runTask.resolution.fullhd')}</option>
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="ai-notice-subtle">{t('upload.notice', undefined, 'AI-generated content may contain inaccuracies. Review carefully.')}</div>

      {file && (
        <button onClick={onCreate} className="primary-btn" disabled={uploading}>
          {uploadMode === 'pdf' ? pdfCreateLabel : t('upload.createVideo', undefined, 'Create Video')}
        </button>
      )}
    </>
  );
};

export default UploadPanel;

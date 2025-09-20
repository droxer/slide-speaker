import React from 'react';

type UploadPanelProps = {
  uploadMode: 'slides' | 'pdf';
  setUploadMode: (v: 'slides' | 'pdf') => void;
  pdfOutputMode: 'video' | 'podcast';
  setPdfOutputMode: (v: 'video' | 'podcast') => void;
  isResumingTask: boolean;
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
  getFileTypeHint: (filename: string) => JSX.Element;
};

const UploadPanel: React.FC<UploadPanelProps> = ({
  uploadMode,
  setUploadMode,
  pdfOutputMode,
  setPdfOutputMode,
  isResumingTask,
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
}) => {
  return (
    <>
      <div className="upload-view">
        <div className="mode-toggle" role="tablist" aria-label="Entry Mode">
          <button
            type="button"
            className={`toggle-btn ${uploadMode === 'slides' ? 'active' : ''}`}
            onClick={() => setUploadMode('slides')}
            role="tab"
            aria-selected={uploadMode === 'slides'}
            aria-controls="slides-mode-panel"
          >
            🖼️ Slides
          </button>
          <button
            type="button"
            className={`toggle-btn ${uploadMode === 'pdf' ? 'active' : ''}`}
            onClick={() => setUploadMode('pdf')}
            role="tab"
            aria-selected={uploadMode === 'pdf'}
            aria-controls="pdf-mode-panel"
          >
            📄 PDF
          </button>
        </div>
        <div className="mode-explainer" aria-live="polite">
          {uploadMode === 'slides' ? (
            <>
              <strong>Slides Mode:</strong> Processes each slide individually for transcripts, audio, subtitles, and composes a final video.
            </>
          ) : (
            <>
              <strong>PDF Mode:</strong> Segments the document into chapters, then you can generate either a video (with audio + subtitles) or a 2‑person podcast (MP3).
            </>
          )}
        </div>
        {uploadMode === 'pdf' && (
          <div className="mode-toggle" role="tablist" aria-label="PDF Output">
            <button
              type="button"
              className={`toggle-btn ${pdfOutputMode === 'video' ? 'active' : ''}`}
              onClick={() => setPdfOutputMode('video')}
              role="tab"
              aria-selected={pdfOutputMode === 'video'}
              aria-controls="pdf-output-video"
            >
              🎬 Video
            </button>
            <button
              type="button"
              className={`toggle-btn ${pdfOutputMode === 'podcast' ? 'active' : ''}`}
              onClick={() => setPdfOutputMode('podcast')}
              role="tab"
              aria-selected={pdfOutputMode === 'podcast'}
              aria-controls="pdf-output-podcast"
            >
              🎧 Podcast
            </button>
          </div>
        )}
        {isResumingTask && (
          <div className="resume-indicator">
            <div className="spinner"></div>
            <p>Resuming your last task...</p>
          </div>
        )}

        <div className="file-upload-area">
          <input
            type="file"
            id="file-upload"
            accept={uploadMode === 'pdf' ? '.pdf' : '.pptx,.ppt'}
            onChange={onFileChange}
            className="file-input"
            disabled={isResumingTask}
          />
          <label htmlFor="file-upload" className={`file-upload-label ${isResumingTask ? 'disabled' : ''}`}>
            <div className="upload-icon">📄</div>
            <div className="upload-text">
              {file ? file.name : uploadMode === 'pdf' ? 'Choose a PDF file' : 'Choose a PPTX/PPT file'}
            </div>
            <div className="upload-hint">
              {file ? getFileTypeHint(file.name) : uploadMode === 'pdf' ? 'PDF will be processed into a video or podcast' : 'Slides will be processed into a narrated video'}
            </div>
          </label>
        </div>

        <div className="options-panel">
          <div className="video-option-card">
            <div className="video-option-header">
              <span className="video-option-icon">🌐</span>
              <span className="video-option-title">AUDIO LANGUAGE</span>
            </div>
            <select id="voice-language-select" value={voiceLanguage} onChange={(e) => setVoiceLanguage(e.target.value)} className="video-option-select">
              <option value="english">English</option>
              <option value="simplified_chinese">简体中文</option>
              <option value="traditional_chinese">繁體中文</option>
              <option value="japanese">日本語</option>
              <option value="korean">한국어</option>
              <option value="thai">ไทย</option>
            </select>
          </div>

          <div className="video-option-card">
            <div className="video-option-header">
              <span className="video-option-icon">📝</span>
              <span className="video-option-title">{uploadMode === 'pdf' && pdfOutputMode === 'podcast' ? 'Transcript Language' : 'Subtitles Language'}</span>
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
              <option value="english">English</option>
              <option value="simplified_chinese">简体中文</option>
              <option value="traditional_chinese">繁體中文</option>
              <option value="japanese">日本語</option>
              <option value="korean">한국어</option>
              <option value="thai">ไทย</option>
            </select>
          </div>

          {(uploadMode !== 'pdf' || pdfOutputMode === 'video') && (
            <div className="video-option-card">
              <div className="video-option-header">
                <span className="video-option-icon">📺</span>
                <span className="video-option-title">Quality</span>
              </div>
              <select id="video-resolution-select" value={videoResolution} onChange={(e) => setVideoResolution(e.target.value)} className="video-option-select">
                <option value="sd">SD (640×480)</option>
                <option value="hd">HD (1280×720)</option>
                <option value="fullhd">Full HD (1920×1080)</option>
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="ai-notice-subtle">AI-generated content may contain inaccuracies. Review carefully.</div>

      {file && (
        <button onClick={onCreate} className="primary-btn" disabled={uploading}>
          {uploadMode === 'pdf' ? (pdfOutputMode === 'podcast' ? 'Create Podcast' : 'Create Video') : 'Create Video'}
        </button>
      )}
    </>
  );
};

export default UploadPanel;


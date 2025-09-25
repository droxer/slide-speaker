import React, { useEffect, useState } from 'react';
import { getLanguageDisplayName } from '../utils/language';

type RunTaskPayload = {
  task_type: 'video' | 'podcast';
  voice_language: string;
  subtitle_language?: string | null;
  transcript_language?: string | null;
  video_resolution?: string;
  generate_video?: boolean;
  generate_podcast?: boolean;
};

type Props = {
  open: boolean;
  isPdf: boolean;
  defaults: Partial<RunTaskPayload>;
  onClose: () => void;
  onSubmit: (payload: RunTaskPayload) => void;
  filename?: string;
  submitting?: boolean;
};

const LANGS = [
  'english',
  'simplified_chinese',
  'traditional_chinese',
  'japanese',
  'korean',
  'thai',
];

const shortenFileName = (name?: string, max = 48): string => {
  if (!name) return 'Selected file';
  const base = name.replace(/\.(pdf|pptx?|PPTX?|PDF)$/,'');
  if (base.length <= max) return base;
  const head = Math.max(12, Math.floor((max - 1) / 2));
  const tail = max - head - 1;
  return base.slice(0, head) + '…' + base.slice(-tail);
};

const RunTaskModal: React.FC<Props> = ({ open, isPdf, defaults, onClose, onSubmit, filename, submitting }) => {
  const [taskType, setTaskType] = useState<'video'|'podcast'>(defaults.task_type as any || 'video');
  const [voiceLang, setVoiceLang] = useState<string>(defaults.voice_language || 'english');
  const [subLang, setSubLang] = useState<string | null>((defaults.subtitle_language as any) ?? null);
  const [transcriptLang, setTranscriptLang] = useState<string | null>((defaults.transcript_language as any) ?? null);
  const [resolution, setResolution] = useState<string>(defaults.video_resolution || 'hd');

  useEffect(() => {
    if (!open) return;
    setTaskType(isPdf ? ((defaults.task_type as any) || 'video') : 'video');
    setVoiceLang(defaults.voice_language || 'english');
    setSubLang((defaults.subtitle_language as any) ?? null);
    setTranscriptLang((defaults.transcript_language as any) ?? null);
    setResolution(defaults.video_resolution || 'hd');
    // no avatar config in upload view; keep defaults as-is (not exposed)
  }, [open, isPdf, defaults.task_type, defaults.voice_language, defaults.subtitle_language, defaults.transcript_language, defaults.video_resolution]);

  // Close on ESC and lock body scroll while open
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || (e as any).keyCode === 27) {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  const run = () => {
    // Upload view parity:
    // - PDF supports either video or podcast
    // - Slides support video only
    const chosenType: 'video'|'podcast' = isPdf ? taskType : 'video';
    const payload: RunTaskPayload = {
      task_type: chosenType,
      voice_language: voiceLang,
      subtitle_language: (chosenType === 'podcast') ? null : (subLang ?? null),
      transcript_language: (chosenType === 'podcast') ? (transcriptLang ?? null) : null,
      video_resolution: resolution,
      generate_video: chosenType !== 'podcast',
      generate_podcast: chosenType !== 'video',
    } as RunTaskPayload;
    onSubmit(payload);
  };

  return (
    <div className="run-task-modal" onClick={onClose} role="dialog" aria-modal="true">
      <div className="run-task-content" onClick={(e) => e.stopPropagation()} role="document">
        <div className="modal-header-bar" data-kind={taskType}>
          <div className="header-left">
            <span className="header-icon" aria-hidden>{taskType === 'podcast' ? '🎧' : '🎬'}</span>
            <span>{taskType === 'podcast' ? 'Create Podcast' : 'Create Video'}</span>
          </div>
          <div className="header-right">
            <button type="button" className="modal-close-btn" aria-label="Close" title="Close" onClick={onClose}>
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>

        <div className="video-player-container" style={{ padding: 16 }}>
          <div className="run-config">
            <div className="run-left">
              <div className="run-summary">
                <div className="file-name" title={filename || ''}>{shortenFileName(filename)}</div>
                {/* Mode is selected by which button opened the modal (Video/Podcast). No toggle here. */}
                <div className="hint">Mode is set by your choice above. Configure options, then press Run.</div>
              </div>
            </div>
            <div className="run-right">
              <div className="config-grid">
                <label className="cfg-field">
                  <span className="cfg-label">Voice Language</span>
                  <select className="video-option-select" value={voiceLang} onChange={(e)=>setVoiceLang(e.target.value)} disabled={submitting}>
                    {LANGS.map(l => <option key={l} value={l}>{getLanguageDisplayName(l)}</option>)}
                  </select>
                </label>

                {taskType !== 'podcast' && (
                  <label className="cfg-field">
                    <span className="cfg-label">Subtitle Language</span>
                    <select className="video-option-select" value={subLang ?? ''} onChange={(e)=>setSubLang(e.target.value || null)} disabled={submitting}>
                      <option value="">Same as voice</option>
                      {LANGS.map(l => <option key={l} value={l}>{getLanguageDisplayName(l)}</option>)}
                    </select>
                  </label>
                )}

                {isPdf && taskType === 'podcast' && (
                  <label className="cfg-field">
                    <span className="cfg-label">Transcript Language</span>
                    <select className="video-option-select" value={transcriptLang ?? ''} onChange={(e)=>setTranscriptLang(e.target.value || null)} disabled={submitting}>
                      <option value="">Same as voice</option>
                      {LANGS.map(l => <option key={l} value={l}>{getLanguageDisplayName(l)}</option>)}
                    </select>
                  </label>
                )}

                <label className="cfg-field">
                  <span className="cfg-label">Video Resolution</span>
                  <select className="video-option-select" value={resolution} onChange={(e)=>setResolution(e.target.value)} disabled={submitting}>
                    <option value="sd">SD (640×480)</option>
                    <option value="hd">HD (1280×720)</option>
                    <option value="fullhd">Full HD (1920×1080)</option>
                  </select>
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
                <button className="secondary-btn" onClick={onClose} disabled={submitting}>Cancel</button>
                <button className="primary-btn" onClick={run} disabled={submitting}>
                  {submitting ? 'Creating…' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RunTaskModal;

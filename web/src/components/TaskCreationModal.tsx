import React, { useEffect, useRef, useState } from 'react';
import { getLanguageDisplayName } from '../utils/language';
import { useI18n } from '@/i18n/hooks';
import { useFocusTrap } from '@/hooks/useFocusTrap';

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

const shortenFileName = (name?: string, fallback = 'Selected file', max = 48): string => {
  if (!name) return fallback;
  const base = name.replace(/\.(pdf|pptx?|PPTX?|PDF)$/,'');
  if (base.length <= max) return base;
  const head = Math.max(12, Math.floor((max - 1) / 2));
  const tail = max - head - 1;
  return base.slice(0, head) + '…' + base.slice(-tail);
};

const TaskCreationModal = ({ open, isPdf, defaults, onClose, onSubmit, filename, submitting }: Props) => {
  const { t } = useI18n();
  const [taskType, setTaskType] = useState<'video'|'podcast'>(defaults.task_type as any || 'video');
  const [voiceLang, setVoiceLang] = useState<string>(defaults.voice_language || 'english');
  const [subLang, setSubLang] = useState<string | null>((defaults.subtitle_language as any) ?? null);
  const [transcriptLang, setTranscriptLang] = useState<string | null>((defaults.transcript_language as any) ?? null);
  const [resolution, setResolution] = useState<string>(defaults.video_resolution || 'hd');

  // Use focus trap for the modal
  const modalRef = useFocusTrap(open);

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

  const fileDisplayName = shortenFileName(filename, t('runTask.noFileSelected', undefined, 'Selected file'));

  const displayLanguage = (code: string) => {
    const normalized = (code || '').toLowerCase();
    const fallback = getLanguageDisplayName(code);
    return t(`language.display.${normalized}`, undefined, fallback || t('common.unknown', undefined, 'Unknown'));
  };

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
      <div ref={modalRef} className="run-task-content" onClick={(e) => e.stopPropagation()} role="document">
        <div className="modal-header-bar" data-kind={taskType}>
          <div className="header-left">
            <span className="header-icon" aria-hidden="true">{taskType === 'podcast' ? '🎧' : '🎬'}</span>
            <span>{taskType === 'podcast' ? t('actions.generatePodcast') : t('actions.generateVideo')}</span>
          </div>
          <div className="header-right">
            <button type="button" className="modal-close-btn" aria-label={t('actions.close')} title={t('actions.close')} onClick={onClose}>
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
                <div className="run-tag" data-kind={taskType}>{`${taskType === 'podcast' ? t('task.list.podcastLabel') : t('task.list.videoLabel')} ${t('runTask.tagSuffix')}`}</div>
                <dl className="summary-fields">
                  <div>
                    <dt>{t('runTask.source')}</dt>
                    <dd title={filename || ''}>{fileDisplayName}</dd>
                  </div>
                  <div>
                    <dt>{t('runTask.output.label')}</dt>
                    <dd>{taskType === 'podcast' ? t('runTask.output.podcast') : t('runTask.output.video')}</dd>
                  </div>
                </dl>
                <div className="hint">{t('runTask.adjustHint')}</div>
              </div>
            </div>
            <div className="run-right">
              <div className="config-grid">
                <label className="cfg-field">
                  <span className="cfg-label">{t('runTask.voiceLanguage')}</span>
                  <select className="video-option-select" value={voiceLang} onChange={(e)=>setVoiceLang(e.target.value)} disabled={submitting}>
                    {LANGS.map(l => <option key={l} value={l}>{displayLanguage(l)}</option>)}
                  </select>
                </label>

                {taskType !== 'podcast' && (
                  <label className="cfg-field">
                    <span className="cfg-label">{t('runTask.subtitleLanguage')}</span>
                    <select className="video-option-select" value={subLang ?? ''} onChange={(e)=>setSubLang(e.target.value || null)} disabled={submitting}>
                      <option value="">{t('runTask.sameAsVoice')}</option>
                      {LANGS.map(l => <option key={l} value={l}>{displayLanguage(l)}</option>)}
                    </select>
                  </label>
                )}

                {isPdf && taskType === 'podcast' && (
                  <label className="cfg-field">
                    <span className="cfg-label">{t('runTask.transcriptLanguage')}</span>
                    <select className="video-option-select" value={transcriptLang ?? ''} onChange={(e)=>setTranscriptLang(e.target.value || null)} disabled={submitting}>
                      <option value="">{t('runTask.sameAsVoice')}</option>
                      {LANGS.map(l => <option key={l} value={l}>{displayLanguage(l)}</option>)}
                    </select>
                  </label>
                )}

                <label className="cfg-field">
                  <span className="cfg-label">{t('runTask.videoResolution')}</span>
                  <select className="video-option-select" value={resolution} onChange={(e)=>setResolution(e.target.value)} disabled={submitting}>
                    <option value="sd">{t('runTask.resolution.sd')}</option>
                    <option value="hd">{t('runTask.resolution.hd')}</option>
                    <option value="fullhd">{t('runTask.resolution.fullhd')}</option>
                  </select>
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
                <button type="button" className="secondary-btn" onClick={onClose} disabled={submitting}>{t('actions.cancel')}</button>
                <button type="button" className="primary-btn" onClick={run} disabled={submitting}>
                  {submitting ? t('actions.generating') : t('actions.generate')}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskCreationModal;

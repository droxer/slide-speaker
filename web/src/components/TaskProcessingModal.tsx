'use client';

import React, { useEffect, useMemo } from 'react';
import TaskProcessingSteps from './TaskProcessingSteps';
import type { Task } from '@/types';
import type { ProcessingDetails } from './types';
import { getStepLabel } from '@/utils/stepLabels';
import { useI18n } from '@/i18n/hooks';

type TaskProcessingModalProps = {
  open: boolean;
  task: Task | null;
  onClose: () => void;
  onCancel: (taskId: string) => void | Promise<void>;
};

const formatStepName = (
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

const normalizeErrors = (
  errors: unknown,
  fallbackStep: string,
  fallbackTimestamp: string,
): Array<{ step: string; error: string; timestamp: string }> => {
  if (!Array.isArray(errors)) return [];
  return errors.map((entry) => {
    if (typeof entry === 'string') {
      return {
        step: fallbackStep || 'unknown_step',
        error: entry,
        timestamp: fallbackTimestamp,
      };
    }
    if (entry && typeof entry === 'object') {
      const step = String((entry as any).step || fallbackStep || 'unknown_step');
      const error = String((entry as any).error || (entry as any).message || '');
      const timestamp = String((entry as any).timestamp || fallbackTimestamp);
      return { step, error, timestamp };
    }
    return {
      step: fallbackStep || 'unknown_step',
      error: String(entry ?? ''),
      timestamp: fallbackTimestamp,
    };
  }).filter((item) => item.error.length > 0);
};

const TaskProcessingModal: React.FC<TaskProcessingModalProps> = ({
  open,
  task,
  onClose,
  onCancel,
}) => {
  const { t } = useI18n();

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' || (event as any).keyCode === 27) {
        event.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = previous;
    };
  }, [open, onClose]);

  const details = useMemo(() => {
    if (!task) return null;
    const state = (task.detailed_state as any) || task.state || {};
    const progress = Number.isFinite(task.completion_percentage)
      ? Math.max(0, Math.min(100, Math.round(task.completion_percentage ?? 0)))
      : 0;
    const createdAt = String(state.created_at || task.created_at || '');
    const updatedAt = String(state.updated_at || task.updated_at || '');
    const stepErrors = normalizeErrors(state.errors, state.current_step, updatedAt || createdAt || new Date().toISOString());

    // More robust steps extraction - try multiple possible locations
    let stepsData = state.steps || {};

    // If stepsData is still empty, check if it might be in a nested structure
    if ((!stepsData || Object.keys(stepsData).length === 0) && task.state && typeof task.state === 'object') {
      stepsData = (task.state as any).steps || {};
    }

    // If still empty, check detailed_state
    if ((!stepsData || Object.keys(stepsData).length === 0) && task.detailed_state && typeof task.detailed_state === 'object') {
      stepsData = (task.detailed_state as any).steps || {};
    }

    const computed: ProcessingDetails & {
      task_type?: string;
      generate_avatar?: boolean;
      generate_subtitles?: boolean;
    } = {
      status: task.status,
      progress,
      current_step: state.current_step || '',
      steps: stepsData,
      errors: stepErrors,
      filename: state.filename || task.kwargs?.filename || undefined,
      file_ext: task.kwargs?.file_ext || state.file_ext,
      voice_language: state.voice_language || task.kwargs?.voice_language || task.voice_language,
      subtitle_language: state.subtitle_language
        || state.podcast_transcript_language
        || task.kwargs?.subtitle_language
        || task.kwargs?.transcript_language
        || task.subtitle_language
        || undefined,
      created_at: createdAt || new Date().toISOString(),
      updated_at: updatedAt || createdAt || new Date().toISOString(),
    };

    if (!computed.steps || typeof computed.steps !== 'object') {
      computed.steps = {};
    }

    if (state.task_type || task.task_type) {
      computed.task_type = String(state.task_type || task.task_type || '').toLowerCase();
    }

    if (typeof state.generate_avatar === 'boolean') {
      computed.generate_avatar = state.generate_avatar;
    }
    if (typeof state.generate_subtitles === 'boolean') {
      computed.generate_subtitles = state.generate_subtitles;
    }

    return computed;
  }, [task]);

  if (!open || !task || !details) return null;

  const handleStop = () => {
    if (!task.task_id) return;
    onCancel(task.task_id);
  };

  const modalTitle = t('processing.modal.title', undefined, 'Processing details');
  const closeLabel = t('processing.modal.close', undefined, 'Close processing details');

  return (
    <div className="processing-modal" role="dialog" aria-modal="true" aria-labelledby="processing-modal-title" onClick={onClose}>
      <div className="processing-modal__content" role="document" onClick={(event) => event.stopPropagation()}>
        <header className="processing-modal__header">
          <div className="processing-modal__title">
            <span aria-hidden>⚙️</span>
            <span id="processing-modal-title">{modalTitle}</span>
          </div>
          <button
            type="button"
            className="processing-modal__close"
            aria-label={closeLabel}
            title={closeLabel}
            onClick={onClose}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="processing-modal__body">
          <TaskProcessingSteps
            taskId={task.task_id}
            fileId={task.file_id}
            fileName={details.filename || null}
            progress={details.progress}
            onStop={handleStop}
            processingDetails={details}
            formatStepNameWithLanguages={(step, vl, sl) => formatStepName(step, vl, sl, t)}
          />
        </div>
      </div>
    </div>
  );
};

export default TaskProcessingModal;

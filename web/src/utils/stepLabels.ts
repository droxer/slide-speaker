type TranslateFn = (key: string, vars?: Record<string, string | number>, fallback?: string) => string;

export type StepStatusVariant =
  | 'completed'
  | 'processing'
  | 'pending'
  | 'failed'
  | 'cancelled'
  | 'skipped';

type StepEntry = {
  defaultLabel: string;
  translationKey: string;
};

const STEP_LABELS: Record<string, StepEntry> = {
  extract_slides: { defaultLabel: 'Extracting Slides', translationKey: 'processing.steps.extract_slides' },
  analyze_slide_images: { defaultLabel: 'Analyzing Content', translationKey: 'processing.steps.analyze_slide_images' },
  generate_transcripts: { defaultLabel: 'Generating Transcripts', translationKey: 'processing.steps.generate_transcripts' },
  revise_transcripts: { defaultLabel: 'Revising Transcripts', translationKey: 'processing.steps.revise_transcripts' },
  translate_voice_transcripts: { defaultLabel: 'Translating Voice Transcripts', translationKey: 'processing.steps.translate_voice_transcripts' },
  translate_subtitle_transcripts: { defaultLabel: 'Translating Subtitle Transcripts', translationKey: 'processing.steps.translate_subtitle_transcripts' },
  generate_subtitle_transcripts: { defaultLabel: 'Generating Subtitle Transcripts', translationKey: 'processing.steps.generate_subtitle_transcripts' },
  generate_audio: { defaultLabel: 'Generating Audio', translationKey: 'processing.steps.generate_audio' },
  generate_avatar_videos: { defaultLabel: 'Creating Avatar', translationKey: 'processing.steps.generate_avatar_videos' },
  convert_slides_to_images: { defaultLabel: 'Converting Slides', translationKey: 'processing.steps.convert_slides_to_images' },
  generate_subtitles: { defaultLabel: 'Creating Subtitles', translationKey: 'processing.steps.generate_subtitles' },
  compose_video: { defaultLabel: 'Composing Video', translationKey: 'processing.steps.compose_video' },
  segment_pdf_content: { defaultLabel: 'Segmenting Content', translationKey: 'processing.steps.segment_pdf_content' },
  revise_pdf_transcripts: { defaultLabel: 'Revising Transcripts', translationKey: 'processing.steps.revise_pdf_transcripts' },
  generate_pdf_chapter_images: { defaultLabel: 'Creating Video Frames', translationKey: 'processing.steps.generate_pdf_chapter_images' },
  generate_pdf_audio: { defaultLabel: 'Generating Audio', translationKey: 'processing.steps.generate_pdf_audio' },
  generate_pdf_subtitles: { defaultLabel: 'Creating Subtitles', translationKey: 'processing.steps.generate_pdf_subtitles' },
  generate_podcast_script: { defaultLabel: 'Generating Podcast Script', translationKey: 'processing.steps.generate_podcast_script' },
  translate_podcast_script: { defaultLabel: 'Translating Podcast Script', translationKey: 'processing.steps.translate_podcast_script' },
  generate_podcast_audio: { defaultLabel: 'Generating Podcast Audio', translationKey: 'processing.steps.generate_podcast_audio' },
  compose_podcast: { defaultLabel: 'Composing Podcast', translationKey: 'processing.steps.compose_podcast' },
  unknown: { defaultLabel: 'Initializing', translationKey: 'processing.steps.unknown' },
};

const prettifyStep = (step: string): string =>
  step
    .split(/[_-]/)
    .map((part) => (part ? part.charAt(0).toUpperCase() + part.slice(1) : ''))
    .join(' ');

export function getStepLabel(step: string, translate?: TranslateFn): string {
  const entry = STEP_LABELS[step];
  if (entry) {
    if (translate) {
      return translate(entry.translationKey, undefined, entry.defaultLabel);
    }
    return entry.defaultLabel;
  }
  if (translate) {
    return translate(`processing.steps.${step}`, undefined, prettifyStep(step));
  }
  return prettifyStep(step);
}

export const normalizeStepStatus = (status?: string | null): StepStatusVariant => {
  const normalized = String(status ?? '').toLowerCase();
  switch (normalized) {
    case 'completed':
      return 'completed';
    case 'processing':
    case 'in_progress':
    case 'running':
      return 'processing';
    case 'failed':
    case 'error':
      return 'failed';
    case 'cancelled':
    case 'canceled':
      return 'cancelled';
    case 'skipped':
      return 'skipped';
    case 'queued':
    case 'waiting':
    case 'pending':
      return 'pending';
    default:
      return 'pending';
  }
};

export const STEP_STATUS_ICONS: Record<StepStatusVariant, string> = {
  completed: '✓',
  processing: '⏳',
  pending: '•',
  failed: '⚠',
  cancelled: '✕',
  skipped: '⤼',
};

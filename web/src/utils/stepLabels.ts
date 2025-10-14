type TranslateFn = (key: string, vars?: Record<string, string | number>, fallback?: string) => string;

export type StepStatusVariant =
  | 'completed'
  | 'processing'
  | 'pending'
  | 'failed'
  | 'cancelled'
  | 'skipped';

const STEP_LABELS: Record<string, { label: string; key: string }> = {
  extract_slides: { label: 'Extracting Slides', key: 'processing.steps.extract_slides' },
  analyze_slide_images: { label: 'Analyzing Content', key: 'processing.steps.analyze_slide_images' },
  generate_transcripts: { label: 'Generating Transcripts', key: 'processing.steps.generate_transcripts' },
  revise_transcripts: { label: 'Revising Transcripts', key: 'processing.steps.revise_transcripts' },
  translate_voice_transcripts: { label: 'Translating Voice Transcripts', key: 'processing.steps.translate_voice_transcripts' },
  translate_subtitle_transcripts: { label: 'Translating Subtitle Transcripts', key: 'processing.steps.translate_subtitle_transcripts' },
  generate_subtitle_transcripts: { label: 'Generating Subtitle Transcripts', key: 'processing.steps.generate_subtitle_transcripts' },
  generate_audio: { label: 'Generating Audio', key: 'processing.steps.generate_audio' },
  generate_avatar_videos: { label: 'Creating Avatar', key: 'processing.steps.generate_avatar_videos' },
  convert_slides_to_images: { label: 'Converting Slides', key: 'processing.steps.convert_slides_to_images' },
  generate_subtitles: { label: 'Creating Subtitles', key: 'processing.steps.generate_subtitles' },
  compose_video: { label: 'Composing Video', key: 'processing.steps.compose_video' },
  segment_pdf_content: { label: 'Segmenting Content', key: 'processing.steps.segment_pdf_content' },
  revise_pdf_transcripts: { label: 'Revising Transcripts', key: 'processing.steps.revise_pdf_transcripts' },
  generate_pdf_chapter_images: { label: 'Creating Video Frames', key: 'processing.steps.generate_pdf_chapter_images' },
  generate_pdf_audio: { label: 'Generating Audio', key: 'processing.steps.generate_pdf_audio' },
  generate_pdf_subtitles: { label: 'Creating Subtitles', key: 'processing.steps.generate_pdf_subtitles' },
  generate_podcast_script: { label: 'Generating Podcast Script', key: 'processing.steps.generate_podcast_script' },
  translate_podcast_script: { label: 'Translating Podcast Script', key: 'processing.steps.translate_podcast_script' },
  generate_podcast_audio: { label: 'Generating Podcast Audio', key: 'processing.steps.generate_podcast_audio' },
  compose_podcast: { label: 'Composing Podcast', key: 'processing.steps.compose_podcast' },
  unknown: { label: 'Initializing', key: 'processing.steps.unknown' },
};

const formatStepName = (step: string): string => 
  step.split(/[_-]/).map(part => part ? part.charAt(0).toUpperCase() + part.slice(1) : '').join(' ');

export function getStepLabel(step: string, translate?: TranslateFn): string {
  const entry = STEP_LABELS[step];
  
  if (entry) {
    return translate ? translate(entry.key, undefined, entry.label) : entry.label;
  }
  
  return translate ? translate(`processing.steps.${step}`, undefined, formatStepName(step)) : formatStepName(step);
}

export const normalizeStepStatus = (status?: string | null): StepStatusVariant => {
  const normalized = String(status ?? '').toLowerCase();
  
  switch (normalized) {
    case 'completed': return 'completed';
    case 'processing': case 'in_progress': case 'running': return 'processing';
    case 'failed': case 'error': return 'failed';
    case 'cancelled': case 'canceled': return 'cancelled';
    case 'skipped': return 'skipped';
    case 'queued': case 'waiting': case 'pending': return 'pending';
    default: return 'pending';
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

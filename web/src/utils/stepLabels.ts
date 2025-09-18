export const STEP_LABELS: Record<string, string> = {
  // Common
  extract_slides: 'Extracting Slides',
  analyze_slide_images: 'Analyzing Content',
  generate_transcripts: 'Generating Transcripts',
  revise_transcripts: 'Revising Transcripts',
  translate_voice_transcripts: 'Translating Voice Transcripts',
  translate_subtitle_transcripts: 'Translating Subtitle Transcripts',
  generate_subtitle_transcripts: 'Generating Subtitle Transcripts',
  generate_audio: 'Generating Audio',
  generate_avatar_videos: 'Creating Avatar',
  convert_slides_to_images: 'Converting Slides',
  generate_subtitles: 'Creating Subtitles',
  compose_video: 'Composing Video',

  // PDF video
  segment_pdf_content: 'Segmenting Content',
  revise_pdf_transcripts: 'Revising Transcripts',
  generate_pdf_chapter_images: 'Creating Video Frames',
  generate_pdf_audio: 'Generating Audio',
  generate_pdf_subtitles: 'Creating Subtitles',

  // Podcast
  generate_podcast_script: 'Generating Podcast Script',
  translate_podcast_script: 'Translating Podcast Script',
  generate_podcast_audio: 'Generating Podcast Audio',
  compose_podcast: 'Composing Podcast',

  unknown: 'Initializing',
};

export function getStepLabel(step: string): string {
  return STEP_LABELS[step] ?? step;
}


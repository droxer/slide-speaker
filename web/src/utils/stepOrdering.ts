export const STEP_ORDER = [
  // Slide ingestion
  'extract_slides',
  'convert_slides_to_images',
  'analyze_slide_images',

  // PDF ingestion
  'segment_pdf_content',

  // Script generation & refinement
  'generate_transcripts',
  'revise_transcripts',
  'revise_pdf_transcripts',
  'generate_subtitle_transcripts',
  'generate_podcast_script',

  // Translation
  'translate_voice_transcripts',
  'translate_subtitle_transcripts',
  'translate_podcast_script',

  // Visual preparation
  'generate_pdf_chapter_images',

  // Audio generation
  'generate_audio',
  'generate_pdf_audio',
  'generate_podcast_audio',
  'generate_avatar_videos',

  // Subtitle assets
  'generate_subtitles',
  'generate_pdf_subtitles',

  // Final assembly
  'compose_video',
  'compose_podcast',

  // Fallback for unknown steps
  'unknown',
] as const;

export type StepType = typeof STEP_ORDER[number];

export const getStepPriority = (stepName: string): number => {
  const index = STEP_ORDER.indexOf(stepName as StepType);
  return index !== -1 ? index : STEP_ORDER.length; // Unknown steps go to the end
};

export const sortSteps = <T extends Record<string, any>>(steps: T | null | undefined) => {
  if (!steps) return [];

  return Object.entries(steps).sort(([stepA], [stepB]) => {
    return getStepPriority(stepA) - getStepPriority(stepB);
  }) as Array<[string, T[keyof T]]>;
};

/**
 * Defines the correct ordering for processing steps.
 * This ensures steps are displayed in the logical sequence they occur in the processing pipeline.
 */

export const stepOrdering = [
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

export type StepType = typeof stepOrdering[number];

/**
 * Gets the priority (position) of a step in the logical processing order.
 * Steps with lower priority numbers appear first.
 * Unknown steps get a high priority (appear at the end).
 */
export const getStepPriority = (stepName: string): number => {
  const index = stepOrdering.indexOf(stepName as StepType);
  return index !== -1 ? index : stepOrdering.length; // Unknown steps go to the end
};

/**
 * Sorts processing steps into the correct logical order.
 */
export const sortSteps = <T extends Record<string, any>>(steps: T | null | undefined) => {
  if (!steps) return [] as Array<[string, T[keyof T]]>;

  return Object.entries(steps).sort(([stepA], [stepB]) => {
    const priorityA = getStepPriority(stepA);
    const priorityB = getStepPriority(stepB);
    return priorityA - priorityB;
  }) as Array<[string, T[keyof T]]>;
};

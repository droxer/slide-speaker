// Simple test to verify step ordering works correctly
console.log('Testing step ordering...');

// Mock implementation for Node.js testing
const stepOrdering = [
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
];

const getStepPriority = (stepName) => {
  const index = stepOrdering.indexOf(stepName);
  return index !== -1 ? index : stepOrdering.length; // Unknown steps go to the end
};

const sortSteps = (steps) => {
  if (!steps) return [];

  return Object.entries(steps).sort(([stepA], [stepB]) => {
    const priorityA = getStepPriority(stepA);
    const priorityB = getStepPriority(stepB);
    return priorityA - priorityB;
  });
};

const scenarios = {
  slidesVideo: {
    steps: {
      compose_video: {},
      generate_audio: {},
      extract_slides: {},
      analyze_slide_images: {},
      generate_subtitle_transcripts: {},
    },
    expected: [
      'extract_slides',
      'analyze_slide_images',
      'generate_subtitle_transcripts',
      'generate_audio',
      'compose_video',
    ],
  },
  pdfVideo: {
    steps: {
      compose_video: {},
      translate_voice_transcripts: {},
      generate_pdf_chapter_images: {},
      segment_pdf_content: {},
      revise_pdf_transcripts: {},
    },
    expected: [
      'segment_pdf_content',
      'revise_pdf_transcripts',
      'translate_voice_transcripts',
      'generate_pdf_chapter_images',
      'compose_video',
    ],
  },
  pdfPodcast: {
    steps: {
      compose_podcast: {},
      generate_podcast_audio: {},
      translate_podcast_script: {},
      generate_podcast_script: {},
      segment_pdf_content: {},
    },
    expected: [
      'segment_pdf_content',
      'generate_podcast_script',
      'translate_podcast_script',
      'generate_podcast_audio',
      'compose_podcast',
    ],
  },
};

for (const [label, { steps, expected }] of Object.entries(scenarios)) {
  const sorted = sortSteps(steps).map(([key]) => key);
  const ok = JSON.stringify(sorted) === JSON.stringify(expected);
  console.log(`Scenario "${label}" -> ${ok ? '✅' : '❌'}`);
  if (!ok) {
    console.log('  Expected:', expected);
    console.log('  Actual  :', sorted);
  }
}
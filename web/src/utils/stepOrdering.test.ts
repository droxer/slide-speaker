import { sortSteps } from './stepOrdering';

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

describe('stepOrdering', () => {
  for (const [label, { steps, expected }] of Object.entries(scenarios)) {
    test(`Scenario "${label}" sorts correctly`, () => {
      const sorted = sortSteps(steps).map(([key]) => key);
      expect(sorted).toEqual(expected);
    });
  }
});
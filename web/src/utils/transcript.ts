export type TranscriptCue = {
  start: number;
  end: number;
  text: string;
};

const STRIP_INLINE = /[*_`\->]/g;
const GENERIC_TRANSCRIPT_HEADERS = new Set([
  'podcast conversation',
  'podcast conversation:',
]);

const normalizeParagraphs = (markdown: string): string[] => {
  const paragraphs = markdown
    .split(/\n\s*\n/)
    .map((block) => block.replace(/^#+\s*/, '').trim());

  const filtered = paragraphs.filter((text) => {
    if (!text.length) return false;
    const normalized = text.replace(STRIP_INLINE, '').trim().toLowerCase();
    if (!normalized.length) return false;
    return !GENERIC_TRANSCRIPT_HEADERS.has(normalized);
  });

  return filtered;
};

export const buildCuesFromMarkdown = (markdown: string, segmentSeconds = 5): TranscriptCue[] => {
  const paragraphs = normalizeParagraphs(markdown);
  if (paragraphs.length === 0) return [];

  const cues = paragraphs.map((raw, index) => {
    const text = raw.replace(STRIP_INLINE, '').replace(/^\*\*(.+?):\*\*\s*/, '$1: ');
    const start = index * segmentSeconds;
    const end = start + segmentSeconds;
    return { start, end, text };
  });

  return cues;
};

export const buildCuesFromPodcastDialogue = (
  dialogue: Array<{ speaker: string; text: string }>,
  segmentSeconds = 5,
): TranscriptCue[] => {
  if (!Array.isArray(dialogue) || dialogue.length === 0) {
    return [];
  }

  return dialogue
    .map((item, index) => {
      const speaker = String(item.speaker || '').trim() || 'Speaker';
      const text = String(item.text || '').trim();
      if (!text) return null;
      const start = index * segmentSeconds;
      const end = start + segmentSeconds;
      return { start, end, text: `${speaker}: ${text}` };
    })
    .filter((cue): cue is TranscriptCue => cue !== null);
};

export default buildCuesFromMarkdown;

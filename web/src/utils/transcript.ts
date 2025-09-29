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
  return markdown
    .split(/\n\s*\n/)
    .map((block) => block.replace(/^#+\s*/, '').trim())
    .filter((text) => {
      if (!text.length) return false;
      const normalized = text.replace(STRIP_INLINE, '').trim().toLowerCase();
      if (!normalized.length) return false;
      return !GENERIC_TRANSCRIPT_HEADERS.has(normalized);
    });
};

export const buildCuesFromMarkdown = (markdown: string, segmentSeconds = 5): TranscriptCue[] => {
  const paragraphs = normalizeParagraphs(markdown);
  if (paragraphs.length === 0) {
    return [];
  }

  return paragraphs.map((raw, index) => {
    const text = raw.replace(STRIP_INLINE, '').replace(/^\*\*(.+?):\*\*\s*/, '$1: ');
    const start = index * segmentSeconds;
    const end = start + segmentSeconds;
    return { start, end, text };
  });
};

export default buildCuesFromMarkdown;

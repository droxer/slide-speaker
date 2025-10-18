export type TranscriptCue = {
  start: number;
  end: number;
  text: string;
};

const STRIP_INLINE = /[*_`\->]/g;
const IGNORE_HEADERS = new Set(['podcast conversation', 'podcast conversation:']);

const cleanText = (text: string): string => text.replace(STRIP_INLINE, '').trim();

const normalizeParagraphs = (markdown: string): string[] => {
  return markdown
    .split(/\n\s*\n/)
    .map(block => block.replace(/^#+\s*/, '').trim())
    .filter(text => {
      const normalized = cleanText(text).toLowerCase();
      return normalized.length > 0 && !IGNORE_HEADERS.has(normalized);
    });
};

export const buildCuesFromMarkdown = (markdown: string, segmentSeconds = 5): TranscriptCue[] => {
  const paragraphs = normalizeParagraphs(markdown);
  
  return paragraphs.map((raw, index) => ({
    start: index * segmentSeconds,
    end: (index + 1) * segmentSeconds,
    text: cleanText(raw).replace(/^\*\*(.+?):\*\*\s*/, '$1: ')
  }));
};

export const buildCuesFromPodcastDialogue = (
  dialogue: Array<{ speaker: string; text: string }>,
  segmentSeconds = 5,
  hostVoice?: string | null,
  guestVoice?: string | null,
): TranscriptCue[] => {
  if (!Array.isArray(dialogue) || dialogue.length === 0) return [];

  return dialogue
    .map((item, index) => {
      let speaker = item.speaker?.trim() || 'Speaker';
      const text = item.text?.trim();

      // Format speaker name with voice information if available
      const rawSpeaker = speaker.toLowerCase();
      if (rawSpeaker.startsWith('host')) {
        speaker = hostVoice ? `${hostVoice} (Host)` : 'Host';
      } else if (rawSpeaker.startsWith('guest')) {
        speaker = guestVoice ? `${guestVoice} (Guest)` : 'Guest';
      }

      if (!text) return null;

      return {
        start: index * segmentSeconds,
        end: (index + 1) * segmentSeconds,
        text: `${speaker}: ${text}`
      };
    })
    .filter((cue): cue is TranscriptCue => cue !== null);
};

export default buildCuesFromMarkdown;

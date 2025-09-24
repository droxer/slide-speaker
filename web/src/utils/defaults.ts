export type GlobalRunDefaults = {
  voice_language: string;
  subtitle_language?: string | null;
  transcript_language?: string | null;
  video_resolution?: string;
};

const KEY = 'slidespeaker_run_defaults_v1';

export const getGlobalRunDefaults = (): GlobalRunDefaults => {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const obj = JSON.parse(raw);
      if (obj && typeof obj === 'object') return obj as GlobalRunDefaults;
    }
  } catch {}
  return { voice_language: 'english', subtitle_language: null, transcript_language: null, video_resolution: 'hd' };
};

export const saveGlobalRunDefaults = (d: Partial<GlobalRunDefaults>) => {
  const base = getGlobalRunDefaults();
  const next = { ...base, ...d };
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
};


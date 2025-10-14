export type GlobalRunDefaults = {
  voice_language: string;
  subtitle_language?: string | null;
  transcript_language?: string | null;
  video_resolution?: string;
};

const STORAGE_KEY = 'slidespeaker_run_defaults_v1';
const DEFAULT_VALUES = { 
  voice_language: 'english', 
  subtitle_language: null, 
  transcript_language: null, 
  video_resolution: 'hd' 
} as const;

export const getGlobalRunDefaults = (): GlobalRunDefaults => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && typeof parsed === 'object' 
      ? { ...DEFAULT_VALUES, ...parsed } 
      : DEFAULT_VALUES;
  } catch {
    return DEFAULT_VALUES;
  }
};

export const saveGlobalRunDefaults = (updates: Partial<GlobalRunDefaults>) => {
  try {
    const current = getGlobalRunDefaults();
    const updated = { ...current, ...updates };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // Silently fail to avoid breaking the application
  }
};


export type LanguageCode = string;

const LANGUAGE_NAMES: Record<string, string> = {
  english: 'English',
  simplified_chinese: '简体中文',
  traditional_chinese: '繁體中文',
  japanese: '日本語',
  korean: '한국어',
  thai: 'ไทย',
};

export const getLanguageDisplayName = (
  languageCode: LanguageCode,
  translate?: (key: string, vars?: Record<string, string | number>, fallback?: string) => string,
): string => {
  const normalized = (languageCode || '').toLowerCase();
  
  // Try translation first if provided
  if (translate) {
    const translated = translate(`language.display.${normalized}`, undefined, '');
    if (translated) return translated;
  }
  
  return LANGUAGE_NAMES[normalized] || languageCode || 'Unknown';
};

export const resolveLanguages = (task: any) => {
  const voice = task?.voice_language || task?.kwargs?.voice_language || task?.state?.voice_language || 'english';
  const subtitle = task?.subtitle_language || task?.kwargs?.subtitle_language || task?.state?.subtitle_language || voice;
  const taskType = String(task?.task_type || task?.state?.task_type || '').toLowerCase();
  
  const transcript = (taskType === 'podcast' || taskType === 'both')
    ? task?.kwargs?.transcript_language || task?.state?.podcast_transcript_language || task?.subtitle_language || subtitle
    : subtitle;
    
  return { voiceLanguage: voice, subtitleLanguage: subtitle, transcriptLanguage: transcript };
};

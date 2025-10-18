export const locales = ['en', 'zh-CN', 'zh-TW', 'ja', 'ko', 'th'] as const;
export type Locale = typeof locales[number];
export const defaultLocale: Locale = 'en';

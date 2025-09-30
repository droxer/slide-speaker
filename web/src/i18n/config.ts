export const locales = ['en', 'zh-CN', 'zh-TW'] as const;
export type Locale = typeof locales[number];
export const defaultLocale: Locale = 'en';

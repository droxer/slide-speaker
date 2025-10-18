import {locales, type Locale} from '@/i18n/config';

export const SUPPORTED_LANGUAGES = ['english', 'simplified_chinese', 'traditional_chinese', 'japanese', 'korean', 'thai'] as const;
export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];

export const DEFAULT_LANGUAGE: SupportedLanguage = 'english';

export const LANGUAGE_TO_LOCALE: Record<SupportedLanguage, Locale> = {
  english: 'en',
  simplified_chinese: 'zh-CN',
  traditional_chinese: 'zh-TW',
  japanese: 'ja',
  korean: 'ko',
  thai: 'th',
};

const LOCALE_TO_LANGUAGE: Record<Locale, SupportedLanguage> = {
  en: 'english',
  'zh-CN': 'simplified_chinese',
  'zh-TW': 'traditional_chinese',
  ja: 'japanese',
  ko: 'korean',
  th: 'thai',
};

const LANGUAGE_ALIASES: Record<string, SupportedLanguage> = {
  // English
  english: 'english',
  en: 'english',
  'en-us': 'english',
  'en_gb': 'english',
  'en-gb': 'english',
  
  // Simplified Chinese
  'simplified_chinese': 'simplified_chinese',
  'simplified-chinese': 'simplified_chinese',
  'zh-cn': 'simplified_chinese',
  'zh_cn': 'simplified_chinese',
  'zh-hans': 'simplified_chinese',
  
  // Traditional Chinese
  'traditional_chinese': 'traditional_chinese',
  'traditional-chinese': 'traditional_chinese',
  'zh-tw': 'traditional_chinese',
  'zh_tw': 'traditional_chinese',
  'zh-hant': 'traditional_chinese',
  
  // Japanese
  japanese: 'japanese',
  ja: 'japanese',
  'ja-jp': 'japanese',
  'ja_jp': 'japanese',
  
  // Korean
  korean: 'korean',
  ko: 'korean',
  'ko-kr': 'korean',
  'ko_kr': 'korean',
  
  // Thai
  thai: 'thai',
  th: 'thai',
  'th-th': 'thai',
  'th_th': 'thai',
};

const LOCALE_ALIASES: Record<string, Locale> = {
  'en': 'en',
  'en-us': 'en',
  'en_gb': 'en',
  'en-gb': 'en',
  'zh-cn': 'zh-CN',
  'zh_cn': 'zh-CN',
  'zh-hans': 'zh-CN',
  'zh-tw': 'zh-TW',
  'zh_tw': 'zh-TW',
  'zh-hant': 'zh-TW',
  'ja': 'ja',
  'ja-jp': 'ja',
  'ja_jp': 'ja',
  'ko': 'ko',
  'ko-kr': 'ko',
  'ko_kr': 'ko',
  'th': 'th',
  'th-th': 'th',
  'th_th': 'th',
};

const SUPPORTED_LOCALES = new Set<Locale>(locales);

const normalizeString = (value: string | null | undefined): string => (value ?? '').trim().toLowerCase();

export const normalizeSupportedLanguage = (value: string | null | undefined): SupportedLanguage => {
  const normalized = normalizeString(value);
  return SUPPORTED_LANGUAGES.includes(normalized as SupportedLanguage)
    ? (normalized as SupportedLanguage)
    : LANGUAGE_ALIASES[normalized] ?? DEFAULT_LANGUAGE;
};

export const coerceSupportedLanguage = (value: string | null | undefined): SupportedLanguage | null => {
  const normalized = normalizeString(value);
  if (!normalized) return null;
  
  return SUPPORTED_LANGUAGES.includes(normalized as SupportedLanguage)
    ? (normalized as SupportedLanguage)
    : LANGUAGE_ALIASES[normalized] ?? null;
};

const normalizeLocaleCode = (value: string | null | undefined): Locale | null => {
  const normalized = normalizeString(value);
  if (!normalized) return null;
  
  return SUPPORTED_LOCALES.has(normalized as Locale)
    ? (normalized as Locale)
    : LOCALE_ALIASES[normalized] ?? null;
};

export const preferredLanguageToLocale = (value: string | null | undefined): Locale => 
  LANGUAGE_TO_LOCALE[normalizeSupportedLanguage(value)];

export const localeToPreferredLanguage = (locale: string | null | undefined): SupportedLanguage => {
  const normalized = normalizeLocaleCode(locale);
  return normalized ? LOCALE_TO_LANGUAGE[normalized] : DEFAULT_LANGUAGE;
};

export const normalizePreferredLocale = (value: unknown): Locale | null => {
  if (typeof value !== 'string') return null;
  
  const language = coerceSupportedLanguage(value);
  if (language) return LANGUAGE_TO_LOCALE[language];
  
  return normalizeLocaleCode(value);
};

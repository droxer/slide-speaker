import {locales, type Locale} from '@/i18n/config';

export const SUPPORTED_LANGUAGES = ['english', 'simplified_chinese', 'traditional_chinese'] as const;
export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];

export const DEFAULT_LANGUAGE: SupportedLanguage = 'english';

export const LANGUAGE_TO_LOCALE: Record<SupportedLanguage, Locale> = {
  english: 'en',
  simplified_chinese: 'zh-CN',
  traditional_chinese: 'zh-TW',
};

const LOCALE_TO_LANGUAGE: Record<Locale, SupportedLanguage> = {
  en: 'english',
  'zh-CN': 'simplified_chinese',
  'zh-TW': 'traditional_chinese',
};

const LANGUAGE_ALIASES: Record<string, SupportedLanguage> = {
  english: 'english',
  en: 'english',
  'en-us': 'english',
  'en_gb': 'english',
  'en-gb': 'english',
  simplified_chinese: 'simplified_chinese',
  'simplified-chinese': 'simplified_chinese',
  'zh-cn': 'simplified_chinese',
  'zh_cn': 'simplified_chinese',
  'zh-hans': 'simplified_chinese',
  traditional_chinese: 'traditional_chinese',
  'traditional-chinese': 'traditional_chinese',
  'zh-tw': 'traditional_chinese',
  'zh_tw': 'traditional_chinese',
  'zh-hant': 'traditional_chinese',
};

const LOCALE_ALIASES: Record<string, Locale> = {
  en: 'en',
  'en-us': 'en',
  'en_gb': 'en',
  'en-gb': 'en',
  'zh-cn': 'zh-CN',
  'zh_cn': 'zh-CN',
  'zh-hans': 'zh-CN',
  'zh-tw': 'zh-TW',
  'zh_tw': 'zh-TW',
  'zh-hant': 'zh-TW',
};

const LOCALE_SET = new Set<Locale>(locales);

export const normalizeSupportedLanguage = (
  value: string | null | undefined,
): SupportedLanguage => {
  const normalized = (value ?? '').trim().toLowerCase();
  if (SUPPORTED_LANGUAGES.includes(normalized as SupportedLanguage)) {
    return normalized as SupportedLanguage;
  }
  const alias = LANGUAGE_ALIASES[normalized];
  return alias ?? DEFAULT_LANGUAGE;
};

export const coerceSupportedLanguage = (
  value: string | null | undefined,
): SupportedLanguage | null => {
  const normalized = (value ?? '').trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (SUPPORTED_LANGUAGES.includes(normalized as SupportedLanguage)) {
    return normalized as SupportedLanguage;
  }
  return LANGUAGE_ALIASES[normalized] ?? null;
};

const normalizeLocaleCode = (value: string | null | undefined): Locale | null => {
  const raw = (value ?? '').trim();
  if (!raw) {
    return null;
  }
  if (LOCALE_SET.has(raw as Locale)) {
    return raw as Locale;
  }
  const alias = LOCALE_ALIASES[raw.toLowerCase()];
  return alias ?? null;
};

export const preferredLanguageToLocale = (
  value: string | null | undefined,
): Locale => {
  const language = normalizeSupportedLanguage(value);
  return LANGUAGE_TO_LOCALE[language];
};

export const localeToPreferredLanguage = (
  locale: string | null | undefined,
): SupportedLanguage => {
  const normalized = normalizeLocaleCode(locale);
  if (!normalized) {
    return DEFAULT_LANGUAGE;
  }
  return LOCALE_TO_LANGUAGE[normalized] ?? DEFAULT_LANGUAGE;
};

export const normalizePreferredLocale = (value: unknown): Locale | null => {
  if (typeof value !== 'string') {
    return null;
  }
  const language = coerceSupportedLanguage(value);
  if (!language) {
    const normalizedLocale = normalizeLocaleCode(value);
    return normalizedLocale;
  }
  return LANGUAGE_TO_LOCALE[language];
};

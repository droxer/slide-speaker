'use client';

import {useLocale as useNextLocale, useTranslations, IntlErrorCode, IntlError} from 'next-intl';

export const useI18n = () => {
  const locale = useNextLocale();
  const t = useTranslations();

  const translate = (key: string, values?: Record<string, string | number>, fallback?: string) => {
    try {
      return t(key, values);
    } catch (error) {
      if (error instanceof IntlError && error.code === IntlErrorCode.MISSING_MESSAGE) {
        return fallback ?? key;
      }
      throw error;
    }
  };

  return { locale, t: translate };
};

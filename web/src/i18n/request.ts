import {getRequestConfig} from 'next-intl/server';
import {defaultLocale, locales, type Locale} from './config';
import {translations} from './translations';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const normalized = locales.includes(requested as Locale) ? (requested as Locale) : defaultLocale;
  return {
    locale: normalized,
    messages: translations[normalized]
  };
});

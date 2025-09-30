'use client';

import React from 'react';
import {useLocale, useTranslations} from 'next-intl';
import {usePathname, useRouter} from '@/navigation';
import {locales} from '@/i18n/config';

const localeLabels: Record<string, string> = {
  'en': 'language.english',
  'zh-CN': 'language.simplified',
  'zh-TW': 'language.traditional',
};

const LanguageSwitcher: React.FC = () => {
  const locale = useLocale();
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname();

  const normalizedLocale = React.useMemo(() => {
    const lower = locale.toLowerCase();
    return locales.find((code) => code.toLowerCase() === lower) ?? locale;
  }, [locale]);

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextLocale = event.target.value;
    router.replace(pathname, {locale: nextLocale});
  };

  return (
    <label className="language-switcher" title={t('language.switcher.tooltip')}>
      <span className="language-switcher__label sr-only">{t('language.switcher.label')}</span>
      <select
        className="language-switcher__select"
        value={normalizedLocale}
        onChange={handleChange}
        aria-label={t('language.switcher.label')}
      >
        {locales.map((code) => (
          <option key={code} value={code}>
            {t(localeLabels[code] ?? code)}
          </option>
        ))}
      </select>
    </label>
  );
};

export default LanguageSwitcher;

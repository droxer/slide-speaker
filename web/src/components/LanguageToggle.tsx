'use client';

import React from 'react';
import {useSession} from 'next-auth/react';
import {useLocale, useTranslations} from 'next-intl';
import {usePathname, useRouter} from '@/navigation';
import {locales, type Locale} from '@/i18n/config';
import {
  LANGUAGE_TO_LOCALE,
  coerceSupportedLanguage,
  localeToPreferredLanguage,
  type SupportedLanguage,
} from '@/utils/localePreferences';
import {useUpdateUserProfileMutation} from '@/services/queries';

const localeLabels: Record<string, string> = {
  en: 'language.english',
  'zh-CN': 'language.simplified',
  'zh-TW': 'language.traditional',
  ja: 'language.japanese',
  ko: 'language.korean',
  th: 'language.thai',
};

const LanguageToggle = () => {
  const locale = useLocale();
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname();
  const {data: session, update: updateSession} = useSession();
  const pendingLocaleRef = React.useRef<Locale | null>(null);
  const lastAppliedPreferenceRef = React.useRef<Locale | null>(null);

  const normalizedLocale = React.useMemo(() => {
    const lower = locale.toLowerCase();
    return locales.find((code) => code.toLowerCase() === lower) ?? locale;
  }, [locale]);

  const preferredLocale = React.useMemo<Locale | null>(() => {
    const preference = coerceSupportedLanguage(session?.user?.preferred_language);
    if (!preference) {
      return null;
    }
    return LANGUAGE_TO_LOCALE[preference];
  }, [session?.user?.preferred_language]);

  const mutation = useUpdateUserProfileMutation();
  const updateProfile = mutation.mutate;

  const handleUpdateProfile = (preferredLanguage: SupportedLanguage) => {
    updateProfile({preferred_language: preferredLanguage}, {
      onSuccess: (_, preferredLanguage) => {
        pendingLocaleRef.current = null;
        if (typeof updateSession === 'function') {
          void updateSession({
            ...(session ?? {}),
            user: {
              ...(session?.user ?? {}),
              preferred_language: preferredLanguage,
            },
          } as any);
        }
      },
      onError: () => {
        pendingLocaleRef.current = null;
      },
    });
  };

  React.useEffect(() => {
    if (!preferredLocale) {
      lastAppliedPreferenceRef.current = null;
      return;
    }
    if (
      pendingLocaleRef.current &&
      pendingLocaleRef.current !== preferredLocale
    ) {
      return;
    }
    if (preferredLocale === normalizedLocale) {
      lastAppliedPreferenceRef.current = preferredLocale;
      return;
    }
    if (lastAppliedPreferenceRef.current === preferredLocale) {
      return;
    }
    lastAppliedPreferenceRef.current = preferredLocale;
    // Only redirect if we're not already on the preferred locale
    router.replace(pathname, {locale: preferredLocale});
  }, [normalizedLocale, pathname, preferredLocale, router]);

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextLocale = event.target.value as Locale;
    if (nextLocale === normalizedLocale) {
      return;
    }
    pendingLocaleRef.current = nextLocale;
    router.replace(pathname, {locale: nextLocale});
    if (session?.user) {
      const nextLanguage = localeToPreferredLanguage(nextLocale);
      handleUpdateProfile(nextLanguage);
    } else {
      pendingLocaleRef.current = null;
    }
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

export default LanguageToggle;

'use client';

import { useEffect, useRef } from 'react';
import { useSession } from 'next-auth/react';
import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/navigation';
import { coerceSupportedLanguage, LANGUAGE_TO_LOCALE } from '@/utils/localePreferences';
import { locales, type Locale } from '@/i18n/config';
import type { SupportedLanguage } from '@/utils/localePreferences';

type LocaleSyncProviderProps = {
  children: React.ReactNode;
};

/**
 * Component that ensures the user is on their preferred locale based on their account settings.
 * If the user has a different preferred language than the current locale, it redirects them.
 */
export function LocaleSyncProvider({ children }: LocaleSyncProviderProps) {
  const { data: session } = useSession();
  const currentLocale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const hasSynced = useRef(false);

  // Check if the current locale matches the user's preferred language
  useEffect(() => {
    // Only run if the user is authenticated and we haven't synced yet
    if (!session?.user?.preferred_language || hasSynced.current) {
      return;
    }

    // Normalize the user's preferred language to a supported language
    const preferredLanguage = coerceSupportedLanguage(session.user.preferred_language) as SupportedLanguage | null;
    
    if (!preferredLanguage) {
      hasSynced.current = true;
      return; // User doesn't have a valid preferred language set
    }

    // Convert the preferred language to the corresponding locale
    const preferredLocale = LANGUAGE_TO_LOCALE[preferredLanguage];
    
    // If the current locale doesn't match the user's preference, redirect
    if (preferredLocale && preferredLocale !== currentLocale) {
      // Check if the preferred locale is valid
      if (locales.includes(preferredLocale)) {
        hasSynced.current = true;
        // Use router.replace to change the locale without adding to history
        router.replace(pathname, { locale: preferredLocale });
      }
    } else {
      // If locale matches, mark as synced
      hasSynced.current = true;
    }
  }, [session, currentLocale, pathname, router]);

  return <>{children}</>;
}
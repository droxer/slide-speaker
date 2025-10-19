'use client';

import React from 'react';
import {useMutation} from '@tanstack/react-query';
import {useSession} from 'next-auth/react';
import {useLocale} from 'next-intl';
import AppShell from '@/components/AppShell';
import {useI18n} from '@/i18n/hooks';
import {useRouter} from '@/navigation';
import {getLanguageDisplayName} from '@/utils/language';
import {updateCurrentUserProfile} from '@/services/client';
import type {UserProfile} from '@/types/user';
import type {Locale} from '@/i18n/config';
import type {HealthStatus} from '@/types/health';
import {
  LANGUAGE_TO_LOCALE,
  SUPPORTED_LANGUAGES,
  normalizeSupportedLanguage,
  type SupportedLanguage,
} from '@/utils/localePreferences';
import {useTheme} from '@/theme/ThemeProvider';

type ProfilePageClientProps = {
  profile: UserProfile;
  initialHealth?: HealthStatus | null;
};

export default function ProfilePageClient({profile, initialHealth = null}: ProfilePageClientProps) {
  const {t} = useI18n();
  const router = useRouter();
  const locale = useLocale() as Locale;
  const {data: session, update: updateSession} = useSession();
  const {mode: currentTheme, setTheme: setGlobalTheme} = useTheme();
  const initialName = profile.name ?? '';
  const initialLanguage = normalizeSupportedLanguage(profile.preferred_language);
  const initialTheme = profile.preferred_theme ?? 'auto';

  const [baseline, setBaseline] = React.useState({
    name: initialName,
    language: initialLanguage,
    theme: initialTheme,
  });
  const [name, setName] = React.useState(initialName);
  const [language, setLanguage] = React.useState<SupportedLanguage>(initialLanguage);
  const [theme, setTheme] = React.useState<string>(initialTheme);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const nextName = profile.name ?? '';
    const nextLanguage = normalizeSupportedLanguage(profile.preferred_language);
    const nextTheme = profile.preferred_theme ?? 'auto';
    setName(nextName);
    setLanguage(nextLanguage);
    setTheme(nextTheme);
    setBaseline({name: nextName, language: nextLanguage, theme: nextTheme});
  }, [profile.id, profile.name, profile.preferred_language, profile.preferred_theme]);

  const mutation = useMutation({
    mutationFn: (payload: {name?: string | null; preferred_language?: string | null; preferred_theme?: string | null}) =>
      updateCurrentUserProfile(payload),
    onSuccess: (data) => {
      const updated = data.user;
      const updatedName = updated.name ?? '';
      const updatedLanguage = normalizeSupportedLanguage(updated.preferred_language);
      const updatedTheme = updated.preferred_theme ?? 'auto';
      setName(updatedName);
      setLanguage(updatedLanguage);
      setTheme(updatedTheme);
      setBaseline({name: updatedName, language: updatedLanguage, theme: updatedTheme});
      setMessage(t('profile.saveSuccess', undefined, 'Profile updated'));
      setError(null);
      if (typeof updateSession === 'function') {
        void updateSession({
          ...(session ?? {}),
          user: {
            ...(session?.user ?? {}),
            name: updatedName.length > 0 ? updatedName : session?.user?.name ?? '',
            preferred_language: updatedLanguage,
            preferred_theme: updatedTheme,
          },
        } as any);
      }
      // Update the global theme if it has changed
      if (updatedTheme !== currentTheme) {
        setGlobalTheme(updatedTheme as any);
      }
      const targetLocale = LANGUAGE_TO_LOCALE[updatedLanguage];
      if (targetLocale !== locale) {
        router.replace('/profile', {locale: targetLocale});
      } else {
        router.refresh();
      }
    },
    onError: () => {
      setError(t('profile.saveError', undefined, 'Failed to update profile. Please try again.'));
      setMessage(null);
    },
  });

  const normalizedName = name.trim();
  const hasChanges =
    normalizedName !== (baseline.name ?? '').trim() ||
    language !== baseline.language ||
    theme !== baseline.theme;

  const languageOptions = React.useMemo(() => {
    return SUPPORTED_LANGUAGES.map((code) => ({
      value: code,
      label: getLanguageDisplayName(code),
    }));
  }, []);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setMessage(null);
    setError(null);
    mutation.mutate({
      name: normalizedName.length > 0 ? normalizedName : null,
      preferred_language: language,
      preferred_theme: theme,
    });
  };

  return (
    <AppShell
      activeView="profile"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'studio') {
          router.push('/', {locale});
        }
        if (view === 'creations') {
          router.push('/creations', {locale});
        }
      }}
    >
      <div className="profile-page">
        <section className="profile-card">
          <header>
            <h1>{t('profile.title', undefined, 'Profile')}</h1>
            <p>{t('profile.subtitle', undefined, 'Manage your display name and language preferences.')}</p>
          </header>
          <form className="profile-form" onSubmit={handleSubmit}>
            <label htmlFor="profile-name">{t('profile.nameLabel', undefined, 'Display name')}</label>
            <input
              id="profile-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={255}
              placeholder={t('profile.namePlaceholder', undefined, 'How should we address you?')}
            />

            <label htmlFor="profile-language">{t('profile.languageLabel', undefined, 'Preferred language')}</label>
            <select
              id="profile-language"
              value={language}
              onChange={(event) => setLanguage(normalizeSupportedLanguage(event.target.value))}
            >
              {languageOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <label htmlFor="profile-theme">{t('profile.themeLabel', undefined, 'Preferred theme')}</label>
            <select
              id="profile-theme"
              value={theme}
              onChange={(event) => setTheme(event.target.value)}
            >
              <option value="auto">{t('footer.theme.auto', undefined, 'Auto')}</option>
              <option value="light">{t('footer.theme.light', undefined, 'Light')}</option>
              <option value="dark">{t('footer.theme.dark', undefined, 'Dark')}</option>
              <option value="light-hc">{t('footer.theme.highContrastLight', undefined, 'High Contrast Light')}</option>
              <option value="dark-hc">{t('footer.theme.highContrastDark', undefined, 'High Contrast Dark')}</option>
            </select>

            <div className="profile-actions">
              <button
                type="submit"
                className="primary"
                disabled={!hasChanges || mutation.isPending}
              >
                {mutation.isPending
                  ? t('profile.saving', undefined, 'Saving…')
                  : t('profile.saveButton', undefined, 'Save changes')}
              </button>
            </div>

            {(message || error) && (
              <p className={`profile-feedback ${error ? 'error' : 'success'}`} role="status">
                {error ?? message}
              </p>
            )}
          </form>
        </section>
      </div>
    </AppShell>
  );
}

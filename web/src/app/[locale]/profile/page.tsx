import {redirect} from 'next/navigation';
import {getServerSession} from 'next-auth';
import type {Metadata} from 'next';
import ProfilePageClient from './ProfilePageClient';
import {loadInitialHealth, healthRevalidate} from '../../loadInitialHealth';
import {authOptions} from '@/auth/options';
import {loadCurrentUser} from '@/app/profile/loadCurrentUser';
import type {Locale} from '@/i18n/config';

const LANGUAGE_TO_LOCALE: Record<string, Locale> = {
  english: 'en',
  simplified_chinese: 'zh-CN',
  traditional_chinese: 'zh-TW',
};

const normalizeLanguage = (value: string | null | undefined): keyof typeof LANGUAGE_TO_LOCALE => {
  const normalized = (value ?? '').toLowerCase();
  if (normalized in LANGUAGE_TO_LOCALE) {
    return normalized as keyof typeof LANGUAGE_TO_LOCALE;
  }
  return 'english';
};

export const metadata: Metadata = {
  title: 'Profile • SlideSpeaker',
};

export const revalidate = healthRevalidate;

export default async function ProfilePage({params}: {params: {locale: string}}) {
  const session = await getServerSession(authOptions);
  if (!session) {
    redirect(`/login?redirectTo=/${params.locale}/profile`);
  }

  const profile = await loadCurrentUser();
  if (!profile) {
    redirect(`/login?redirectTo=/${params.locale}/profile`);
  }

  const preferredLanguage = normalizeLanguage(profile.preferred_language);
  const expectedLocale = LANGUAGE_TO_LOCALE[preferredLanguage];
  const currentLocale = params.locale as Locale;
  if (expectedLocale !== currentLocale) {
    redirect(`/${expectedLocale}/profile`);
  }

  const initialHealth = await loadInitialHealth();

  return <ProfilePageClient profile={profile} initialHealth={initialHealth} />;
}

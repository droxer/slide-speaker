import {redirect} from 'next/navigation';
import {getServerSession} from 'next-auth';
import StudioPageClient from '../StudioPageClient';
import {loadInitialHealth} from '../loadInitialHealth';
import {authOptions} from '@/auth/options';

export const revalidate = 300;

type LocaleParams = { params: Promise<{ locale: string }> };

export default async function StudioPage({params}: LocaleParams) {
  const {locale} = await params;
  const session = await getServerSession(authOptions);
  if (!session) {
    redirect(`/login?redirectTo=/${locale}`);
  }

  const initialHealth = await loadInitialHealth();
  return <StudioPageClient initialHealth={initialHealth} />;
}

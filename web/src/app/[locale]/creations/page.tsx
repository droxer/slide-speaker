import {redirect} from 'next/navigation';
import {getServerSession} from 'next-auth';
import CreationsPageClient from '../../creations/CreationsPageClient';
import {loadInitialHealth} from '../../loadInitialHealth';
import {authOptions} from '@/auth/options';

export const revalidate = 300;

type LocaleParams = { params: Promise<{ locale: string }> };

export default async function CreationsPage({params}: LocaleParams) {
  const {locale} = await params;
  const session = await getServerSession(authOptions);
  if (!session) {
    redirect(`/login?redirectTo=/${locale}/creations`);
  }

  const initialHealth = await loadInitialHealth();
  return <CreationsPageClient initialHealth={initialHealth} />;
}

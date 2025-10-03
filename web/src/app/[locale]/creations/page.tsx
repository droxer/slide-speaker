import {redirect} from 'next/navigation';
import {getServerSession} from 'next-auth';
import CreationsPageClient from '../../creations/CreationsPageClient';
import {loadInitialHealth, healthRevalidate} from '../../loadInitialHealth';
import {authOptions} from '@/auth/options';

export const revalidate = healthRevalidate;

export default async function CreationsPage({params}: {params: {locale: string}}) {
  const session = await getServerSession(authOptions);
  if (!session) {
    redirect(`/login?redirectTo=/${params.locale}/creations`);
  }

  const initialHealth = await loadInitialHealth();
  return <CreationsPageClient initialHealth={initialHealth} />;
}

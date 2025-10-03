import {redirect} from 'next/navigation';
import {getServerSession} from 'next-auth';
import StudioPageClient from '../StudioPageClient';
import {loadInitialHealth, healthRevalidate} from '../loadInitialHealth';
import {authOptions} from '@/auth/options';

export const revalidate = healthRevalidate;

export default async function StudioPage({params}: {params: {locale: string}}) {
  const session = await getServerSession(authOptions);
  if (!session) {
    redirect(`/login?redirectTo=/${params.locale}`);
  }

  const initialHealth = await loadInitialHealth();
  return <StudioPageClient initialHealth={initialHealth} />;
}

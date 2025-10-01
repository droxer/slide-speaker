'use client';

import {useLocale} from 'next-intl';
import {useRouter} from '@/navigation';
import App from '@/App';
import type { HealthStatus } from '@/types/health';

export type StudioPageClientProps = {
  initialHealth?: HealthStatus | null;
};

export default function StudioPageClient({ initialHealth = null }: StudioPageClientProps) {
  const router = useRouter();
  const locale = useLocale();

  return (
    <App
      activeView="studio"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'creations') {
          router.push('/creations', {locale});
        }
      }}
    />
  );
}

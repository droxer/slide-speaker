'use client';

import {useLocale} from 'next-intl';
import {useRouter} from '@/navigation';
import App from '@/App';
import type { HealthStatus } from '@/types/health';

export type CreationsPageClientProps = {
  initialHealth?: HealthStatus | null;
};

export default function CreationsPageClient({ initialHealth = null }: CreationsPageClientProps) {
  const router = useRouter();
  const locale = useLocale();

  return (
    <App
      activeView="creations"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'studio') {
          router.push('/', {locale});
        }
      }}
    />
  );
}

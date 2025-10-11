'use client';

import {useLocale} from 'next-intl';
import {useRouter} from '@/navigation';
import AppShell from '@/components/AppShell';
import CreationsDashboard from '@/components/CreationsDashboard';
import {resolveApiBaseUrl} from '@/utils/apiBaseUrl';
import type {HealthStatus} from '@/types/health';

export type CreationsPageClientProps = {
  initialHealth?: HealthStatus | null;
};

export default function CreationsPageClient({ initialHealth = null }: CreationsPageClientProps) {
  const router = useRouter();
  const locale = useLocale();
  const apiBaseUrl = resolveApiBaseUrl();

  return (
    <AppShell
      activeView="creations"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'studio') {
          router.push('/', {locale});
        }
      }}
    >
      <div id="monitor-panel" role="tabpanel" aria-labelledby="monitor-tab">
        <CreationsDashboard apiBaseUrl={apiBaseUrl} />
      </div>
    </AppShell>
  );
}

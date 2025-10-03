'use client';

import {useLocale} from 'next-intl';
import {useRouter} from '@/navigation';
import AppShell from '@/components/AppShell';
import StudioWorkspace from '@/components/StudioWorkspace';
import type {HealthStatus} from '@/types/health';

export type StudioPageClientProps = {
  initialHealth?: HealthStatus | null;
};

export default function StudioPageClient({ initialHealth = null }: StudioPageClientProps) {
  const router = useRouter();
  const locale = useLocale();

  return (
    <AppShell
      activeView="studio"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'creations') {
          router.push('/creations', {locale});
        }
      }}
    >
      <StudioWorkspace />
    </AppShell>
  );
}

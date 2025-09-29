'use client';

import { useRouter } from 'next/navigation';
import App from '@/App';
import type { HealthStatus } from '@/types/health';

export type StudioPageClientProps = {
  initialHealth?: HealthStatus | null;
};

export default function StudioPageClient({ initialHealth = null }: StudioPageClientProps) {
  const router = useRouter();

  return (
    <App
      activeView="studio"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'creations') {
          router.push('/creations');
        }
      }}
    />
  );
}

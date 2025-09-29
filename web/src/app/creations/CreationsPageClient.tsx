'use client';

import { useRouter } from 'next/navigation';
import App from '@/App';
import type { HealthStatus } from '@/types/health';

export type CreationsPageClientProps = {
  initialHealth?: HealthStatus | null;
};

export default function CreationsPageClient({ initialHealth = null }: CreationsPageClientProps) {
  const router = useRouter();

  return (
    <App
      activeView="creations"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'studio') {
          router.push('/');
        }
      }}
    />
  );
}

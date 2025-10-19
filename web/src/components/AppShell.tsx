'use client';

import type {ReactNode} from 'react';
import {useEffect} from 'react';
import type {AppView} from '@/components/Header';
import type {HealthStatus} from '@/types/health';
import {useHealthStatus} from '@/hooks/useHealthStatus';
import {useQueryClient} from '@tanstack/react-query';
import dynamic from 'next/dynamic';

import LoadingPlaceholder from '@/components/LoadingPlaceholder';
import SkipLinks from '@/components/SkipLinks';

const Header = dynamic(() => import('@/components/Header'), {
  ssr: false,
  loading: () => <LoadingPlaceholder type="spinner" size="sm" message="Loading header..." />
});

const Footer = dynamic(() => import('@/components/Footer'), {
  ssr: false,
  loading: () => <LoadingPlaceholder type="spinner" size="sm" message="Loading footer..." />
});

type AppShellProps = {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
  initialHealth?: HealthStatus | null;
  children: ReactNode;
};

export function AppShell({activeView, onNavigate, initialHealth = null, children}: AppShellProps) {
  const queryClient = useQueryClient();
  const {queueUnavailable, redisLatencyMs} = useHealthStatus({initialHealth});

  // Prefetch health status on app initialization
  useEffect(() => {
    const prefetchHealth = async () => {
      try {
        // Prefetch health status for better performance
        await queryClient.prefetchQuery({
          queryKey: ['health'],
          queryFn: () => fetch('/api/health').then(res => res.json()),
          staleTime: 300_000, // 5 minutes
        });
      } catch (error) {
        console.warn('Failed to prefetch health status:', error);
      }
    };

    prefetchHealth();
  }, [queryClient]);

  return (
    <div className="App">
      <SkipLinks />
      <nav id="navigation" role="navigation">
        <Header activeView={activeView} onNavigate={onNavigate} />
      </nav>
      <main id="main-content" className="main-content" role="main">
        {children}
      </main>
      <Footer queueUnavailable={queueUnavailable} redisLatencyMs={redisLatencyMs} />
    </div>
  );
}

export default AppShell;

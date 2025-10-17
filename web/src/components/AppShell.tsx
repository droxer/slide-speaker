'use client';

import type {ReactNode} from 'react';
import type {AppView} from '@/components/Header';
import type {HealthStatus} from '@/types/health';
import {useHealthStatus} from '@/hooks/useHealthStatus';
import dynamic from 'next/dynamic';

const Header = dynamic(() => import('@/components/Header'), {
  ssr: false,
  loading: () => <div className="header-placeholder">Loading header...</div>
});

const Footer = dynamic(() => import('@/components/Footer'), {
  ssr: false,
  loading: () => <div className="footer-placeholder">Loading footer...</div>
});

type AppShellProps = {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
  initialHealth?: HealthStatus | null;
  children: ReactNode;
};

export function AppShell({activeView, onNavigate, initialHealth = null, children}: AppShellProps) {
  const {queueUnavailable, redisLatencyMs} = useHealthStatus({initialHealth});

  return (
    <div className="App">
      <Header activeView={activeView} onNavigate={onNavigate} />
      <main className="main-content">{children}</main>
      <Footer queueUnavailable={queueUnavailable} redisLatencyMs={redisLatencyMs} />
    </div>
  );
}

export default AppShell;

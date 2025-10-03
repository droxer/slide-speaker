'use client';

import type {ReactNode} from 'react';
import Header, {type AppView} from '@/components/Header';
import Footer from '@/components/Footer';
import type {HealthStatus} from '@/types/health';
import {useHealthStatus} from '@/hooks/useHealthStatus';

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

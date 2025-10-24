'use client';

import {QueryClientProvider} from '@tanstack/react-query';
import {SessionProvider} from 'next-auth/react';
import type {ReactNode} from 'react';
import type {Session} from 'next-auth';
import {queryClient} from '@/services/queryClient';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import React from 'react';
import { ErrorBoundaryWithI18n } from '@/components/ErrorBoundary';
import { ThemeProviderWrapper } from './ThemeProviderWrapper';
import { StoreProvider } from '@/stores/StoreProvider';

type ProvidersProps = {
  children: ReactNode;
  session: Session | null;
};

export function Providers({children, session}: ProvidersProps) {
  return (
    <SessionProvider session={session}>
      <ThemeProviderWrapper>
        <StoreProvider>
          <QueryClientProvider client={queryClient}>
            <ErrorBoundaryWithI18n>
              <React.Suspense fallback={<div className="app-loading">Loading application...</div>}>
                {children}
              </React.Suspense>
            </ErrorBoundaryWithI18n>
            <ToastContainer />
          </QueryClientProvider>
        </StoreProvider>
      </ThemeProviderWrapper>
    </SessionProvider>
  );
}

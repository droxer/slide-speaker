'use client';

import {QueryClientProvider} from '@tanstack/react-query';
import {SessionProvider} from 'next-auth/react';
import type {ReactNode} from 'react';
import type {Session} from 'next-auth';
import {queryClient} from '@/services/queryClient';
import {ThemeProvider} from '@/theme/ThemeProvider';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

type ProvidersProps = {
  children: ReactNode;
  session: Session | null;
};

export function Providers({children, session}: ProvidersProps) {
  return (
    <SessionProvider session={session}>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          {children}
          <ToastContainer />
        </QueryClientProvider>
      </ThemeProvider>
    </SessionProvider>
  );
}

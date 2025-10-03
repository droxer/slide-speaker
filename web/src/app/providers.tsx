'use client';

import {QueryClientProvider} from '@tanstack/react-query';
import {SessionProvider} from 'next-auth/react';
import type {ReactNode} from 'react';
import {queryClient} from '@/services/queryClient';
import {ThemeProvider} from '@/theme/ThemeProvider';

export function Providers({children}: {children: ReactNode}) {
  return (
    <SessionProvider>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </ThemeProvider>
    </SessionProvider>
  );
}

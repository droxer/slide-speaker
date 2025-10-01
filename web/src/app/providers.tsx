'use client';

import {QueryClientProvider} from '@tanstack/react-query';
import type {ReactNode} from 'react';
import {queryClient} from '@/services/queryClient';
import {ThemeProvider} from '@/theme/ThemeProvider';

export function Providers({children}: {children: ReactNode}) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ThemeProvider>
  );
}

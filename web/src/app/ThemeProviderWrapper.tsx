'use client';

import type {ReactNode} from 'react';
import {useSession} from 'next-auth/react';
import {ThemeProvider} from '@/theme/ThemeProvider';

type ThemeProviderWrapperProps = {
  children: ReactNode;
};

export function ThemeProviderWrapper({children}: ThemeProviderWrapperProps) {
  const {data: session} = useSession();
  const preferredTheme = session?.user?.preferred_theme ?? null;

  return (
    <ThemeProvider initialTheme={preferredTheme}>
      {children}
    </ThemeProvider>
  );
}
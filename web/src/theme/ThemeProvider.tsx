'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useThemeStore } from '@/stores/themeStore';

type ThemeMode = 'light' | 'dark' | 'auto' | 'light-hc' | 'dark-hc';

type ThemeContextValue = {
  mode: ThemeMode;
  theme: 'light' | 'dark' | 'light-hc' | 'dark-hc';
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const THEME_STORAGE_KEY = 'slidespeaker_ui_theme';

export function ThemeProvider({ children, initialTheme }: { children: React.ReactNode; initialTheme?: string | null }) {
  const { mode, theme, setTheme: setThemeMode, toggleTheme } = useThemeStore();

  // Initialize theme from props or localStorage
  useEffect(() => {
    if (initialTheme) {
      setThemeMode(initialTheme as ThemeMode);
    }
  }, [initialTheme, setThemeMode]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      mode,
      theme,
      setTheme: setThemeMode,
      toggleTheme
    }),
    [mode, theme, setThemeMode, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
}
'use client';

import React, {createContext, useCallback, useContext, useEffect, useMemo, useState} from 'react';

type ThemeMode = 'light' | 'dark' | 'auto' | 'high-contrast-light' | 'high-contrast-dark';

type ThemeContextValue = {
  mode: ThemeMode;
  theme: 'light' | 'dark' | 'high-contrast-light' | 'high-contrast-dark';
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const THEME_STORAGE_KEY = 'slidespeaker_ui_theme';

const isBrowser = typeof window !== 'undefined';

const getInitialMode = (): ThemeMode => {
  if (!isBrowser) return 'auto';
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === 'dark' || stored === 'light' || stored === 'auto' || stored === 'high-contrast-light' || stored === 'high-contrast-dark') {
      return stored as ThemeMode;
    }
  } catch {
    /* ignore */
  }
  return 'auto';
};

const getPreferredTheme = () => {
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const prefersHighContrast = window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches;

  if (prefersHighContrast) {
    return prefersDark ? 'high-contrast-dark' : 'high-contrast-light';
  }
  return prefersDark ? 'dark' : 'light';
};

const getPreferredHighContrast = () => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches;
};


export function ThemeProvider({children}: {children: React.ReactNode}) {
  const initialMode = isBrowser ? getInitialMode() : 'auto';
  const [mode, setMode] = useState<ThemeMode>(initialMode);
  const [theme, setThemeState] = useState<'light' | 'dark' | 'high-contrast-light' | 'high-contrast-dark'>(() => {
    if (!isBrowser) return 'light';
    if (initialMode === 'auto') return getPreferredTheme();
    if (initialMode === 'high-contrast-light' || initialMode === 'high-contrast-dark') {
      return initialMode as 'high-contrast-light' | 'high-contrast-dark';
    }
    return initialMode as 'light' | 'dark';
  });

  useEffect(() => {
    if (!isBrowser) return;
    try {
      const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === 'dark' || stored === 'light' || stored === 'auto' || stored === 'high-contrast-light' || stored === 'high-contrast-dark') {
        setMode(stored as ThemeMode);
        if (stored === 'auto') {
          setThemeState(getPreferredTheme());
        } else if (stored === 'high-contrast-light' || stored === 'high-contrast-dark') {
          setThemeState(stored as 'high-contrast-light' | 'high-contrast-dark');
        } else {
          setThemeState(stored as 'light' | 'dark');
        }
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!isBrowser) return;
    if (mode === 'auto') {
      setThemeState(getPreferredTheme());
    } else {
      setThemeState(mode);
    }
  }, [mode]);

  useEffect(() => {
    if (!isBrowser) return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const contrastMedia = window.matchMedia('(prefers-contrast: more)');
    if (mode !== 'auto') return;

    const listener = (event: MediaQueryListEvent) => {
      const prefersDark = event.matches;
      const prefersHighContrast = contrastMedia.matches;

      if (prefersHighContrast) {
        setThemeState(prefersDark ? 'high-contrast-dark' : 'high-contrast-light');
      } else {
        setThemeState(prefersDark ? 'dark' : 'light');
      }
    };

    const contrastListener = (event: MediaQueryListEvent) => {
      const prefersHighContrast = event.matches;
      const prefersDark = media.matches;

      if (prefersHighContrast) {
        setThemeState(prefersDark ? 'high-contrast-dark' : 'high-contrast-light');
      } else {
        setThemeState(prefersDark ? 'dark' : 'light');
      }
    };

    if (media.addEventListener) {
      media.addEventListener('change', listener);
      contrastMedia.addEventListener('change', contrastListener);
      return () => {
        media.removeEventListener('change', listener);
        contrastMedia.removeEventListener('change', contrastListener);
      };
    }

    media.addListener(listener);
    contrastMedia.addListener(contrastListener);
    return () => {
      media.removeListener(listener);
      contrastMedia.removeListener(contrastListener);
    };
  }, [mode]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const body = document.body;
    body.classList.toggle('dark-theme', theme === 'dark');
    body.classList.toggle('light-theme', theme === 'light');
    body.classList.toggle('high-contrast-light', theme === 'high-contrast-light');
    body.classList.toggle('high-contrast-dark', theme === 'high-contrast-dark');
  }, [theme]);

  useEffect(() => {
    if (!isBrowser) return;
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    } catch {
      /* ignore */
    }
  }, [mode]);

  const setTheme = useCallback((next: ThemeMode) => {
    setMode(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setMode((prev) => {
      if (prev === 'auto') {
        return theme === 'dark' ? 'light' : theme === 'light' ? 'dark' : 'light';
      }
      if (prev === 'high-contrast-light' || prev === 'high-contrast-dark') {
        return 'light';
      }
      return prev === 'dark' ? 'light' : 'dark';
    });
  }, [theme]);

  const value = useMemo<ThemeContextValue>(() => ({mode, theme, setTheme, toggleTheme}), [mode, theme, setTheme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
}

'use client';

import React, {createContext, useCallback, useContext, useEffect, useMemo, useState} from 'react';

type ThemeMode = 'light' | 'dark' | 'auto' | 'light-hc' | 'dark-hc';

type ThemeContextValue = {
  mode: ThemeMode;
  theme: 'light' | 'dark' | 'light-hc' | 'dark-hc';
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
    if (stored === 'dark' || stored === 'light' || stored === 'auto' || stored === 'light-hc' || stored === 'dark-hc') {
      return stored as ThemeMode;
    }
    // Handle legacy theme names for backward compatibility
    if (stored === 'high-contrast-light') {
      return 'light-hc';
    }
    if (stored === 'high-contrast-dark') {
      return 'dark-hc';
    }
  } catch {
    /* ignore */
  }
  return 'auto';
};

const getPreferredTheme = (): 'light' | 'dark' | 'light-hc' | 'dark-hc' => {
  if (typeof window === 'undefined') return 'light';

  const darkMedia = window.matchMedia('(prefers-color-scheme: dark)');
  const contrastMedia = window.matchMedia('(prefers-contrast: more)');

  const prefersDark = darkMedia.matches;
  const prefersHighContrast = contrastMedia.matches;

  if (prefersHighContrast) {
    return prefersDark ? 'dark-hc' : 'light-hc';
  }
  return prefersDark ? 'dark' : 'light';
};

const getPreferredHighContrast = () => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches;
};


export function ThemeProvider({children, initialTheme}: {children: React.ReactNode; initialTheme?: string | null}) {
  const initialMode = isBrowser ? (initialTheme ?? getInitialMode()) : 'auto';
  const validatedInitialMode = (initialMode === 'light' || initialMode === 'dark' || initialMode === 'auto' || initialMode === 'light-hc' || initialMode === 'dark-hc')
    ? initialMode
    : getInitialMode();
  const [mode, setMode] = useState<ThemeMode>(validatedInitialMode);
  const [theme, setThemeState] = useState<'light' | 'dark' | 'light-hc' | 'dark-hc'>(() => {
    if (!isBrowser) return 'light';
    if (validatedInitialMode === 'auto') return getPreferredTheme();
    if (validatedInitialMode === 'light-hc' || validatedInitialMode === 'dark-hc') {
      return validatedInitialMode;
    }
    if (validatedInitialMode === 'light' || validatedInitialMode === 'dark') {
      return validatedInitialMode;
    }
    // Handle legacy theme names for backward compatibility
    if (validatedInitialMode === 'high-contrast-light') {
      return 'light-hc';
    }
    if (validatedInitialMode === 'high-contrast-dark') {
      return 'dark-hc';
    }
    return 'light'; // fallback
  });

  useEffect(() => {
    if (!isBrowser) return;
    try {
      const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
      let storedMode: ThemeMode = 'auto';

      if (stored === 'dark' || stored === 'light' || stored === 'auto' || stored === 'light-hc' || stored === 'dark-hc') {
        storedMode = stored as ThemeMode;
      } else if (stored === 'high-contrast-light') {
        // Handle legacy theme names for backward compatibility
        storedMode = 'light-hc';
      } else if (stored === 'high-contrast-dark') {
        // Handle legacy theme names for backward compatibility
        storedMode = 'dark-hc';
      } else {
        storedMode = 'auto';
      }

      setMode(storedMode);
      if (storedMode === 'auto') {
        setThemeState(getPreferredTheme());
      } else if (storedMode === 'light-hc' || storedMode === 'dark-hc') {
        setThemeState(storedMode);
      } else if (storedMode === 'light' || storedMode === 'dark') {
        setThemeState(storedMode);
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
    const darkMedia = window.matchMedia('(prefers-color-scheme: dark)');
    const contrastMedia = window.matchMedia('(prefers-contrast: more)');
    if (mode !== 'auto') return;

    const updateTheme = () => {
      const prefersDark = darkMedia.matches;
      const prefersHighContrast = contrastMedia.matches;

      if (prefersHighContrast) {
        setThemeState(prefersDark ? 'dark-hc' : 'light-hc');
      } else {
        setThemeState(prefersDark ? 'dark' : 'light');
      }
    };

    // Update theme immediately when auto mode is selected
    updateTheme();

    // Set up listeners for changes
    const darkListener = (event: MediaQueryListEvent) => {
      updateTheme();
    };

    const contrastListener = (event: MediaQueryListEvent) => {
      updateTheme();
    };

    // Use modern event listener API if available
    if (darkMedia.addEventListener) {
      darkMedia.addEventListener('change', darkListener);
      contrastMedia.addEventListener('change', contrastListener);
      return () => {
        darkMedia.removeEventListener('change', darkListener);
        contrastMedia.removeEventListener('change', contrastListener);
      };
    }

    // Fallback to older API
    darkMedia.addListener(darkListener);
    contrastMedia.addListener(contrastListener);
    return () => {
      darkMedia.removeListener(darkListener);
      contrastMedia.removeListener(contrastListener);
    };
  }, [mode]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const body = document.body;
    const isLight = theme === 'light';
    const isDark = theme === 'dark';
    const isLightHighContrast = theme === 'light-hc';
    const isDarkHighContrast = theme === 'dark-hc';

    body.classList.toggle('theme-light', isLight);
    body.classList.toggle('theme-dark', isDark);
    body.classList.toggle('theme-light-hc', isLightHighContrast);
    body.classList.toggle('theme-dark-hc', isDarkHighContrast);
    body.classList.toggle('light-theme', isLight || isLightHighContrast);
    body.classList.toggle('dark-theme', isDark || isDarkHighContrast);
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
      if (prev === 'light-hc' || prev === 'dark-hc') {
        return 'light';
      }
      if (prev === 'light') {
        return 'dark';
      }
      if (prev === 'dark') {
        return 'light';
      }
      return 'light'; // fallback
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

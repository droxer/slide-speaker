import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

type ThemeMode = 'light' | 'dark' | 'auto' | 'light-hc' | 'dark-hc';

interface ThemeState {
  mode: ThemeMode;
  theme: 'light' | 'dark' | 'light-hc' | 'dark-hc';
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
}

const isBrowser = typeof window !== 'undefined';

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

const THEME_STORAGE_KEY = 'slidespeaker_ui_theme';

export const useThemeStore = create<ThemeState>()(
  devtools(
    persist(
      (set, get) => ({
        mode: 'auto',
        theme: 'light',
        setTheme: (mode) => set((state) => {
          // When setting a specific mode, also update the theme
          let theme: 'light' | 'dark' | 'light-hc' | 'dark-hc' = 'light';
          if (mode === 'auto') {
            theme = getPreferredTheme();
          } else if (mode === 'light-hc' || mode === 'dark-hc' || mode === 'light' || mode === 'dark') {
            theme = mode;
          }
          return { mode, theme };
        }),
        toggleTheme: () => set((state) => {
          let newMode: ThemeMode;
          let newTheme: 'light' | 'dark' | 'light-hc' | 'dark-hc' = 'light';

          if (state.mode === 'auto') {
            // Toggle between light and dark when in auto mode
            newMode = state.theme === 'dark' || state.theme === 'dark-hc' ? 'light' : 'dark';
            newTheme = newMode;
          } else if (state.mode === 'light-hc') {
            newMode = 'dark-hc';
            newTheme = 'dark-hc';
          } else if (state.mode === 'dark-hc') {
            newMode = 'light';
            newTheme = 'light';
          } else if (state.mode === 'light') {
            newMode = 'dark';
            newTheme = 'dark';
          } else if (state.mode === 'dark') {
            newMode = 'light';
            newTheme = 'light';
          } else {
            newMode = 'light';
            newTheme = 'light';
          }

          return { mode: newMode, theme: newTheme };
        }),
      }),
      {
        name: THEME_STORAGE_KEY,
        partialize: (state) => ({ mode: state.mode }),
        onRehydrateStorage: () => (state) => {
          if (!state) return;

          // Update theme based on mode when rehydrating
          if (isBrowser) {
            if (state.mode === 'auto') {
              state.theme = getPreferredTheme();
            } else if (state.mode === 'light-hc' || state.mode === 'dark-hc') {
              state.theme = state.mode;
            } else if (state.mode === 'light' || state.mode === 'dark') {
              state.theme = state.mode;
            }
          }
        }
      }
    )
  )
);

// Helper function to apply theme classes to body
export const applyThemeClasses = (theme: 'light' | 'dark' | 'light-hc' | 'dark-hc') => {
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
};
import { useUiStore } from './uiStore';
import { useThemeStore } from './themeStore';
import { useTaskStore } from './taskStore';

// Re-export individual stores
export { useUiStore, useThemeStore, useTaskStore };

// Root store hook that combines all stores
export const useAppStore = () => {
  const ui = useUiStore();
  const theme = useThemeStore();
  const task = useTaskStore();

  return {
    ui,
    theme,
    task,
  };
};

// Types for our stores
export type UiStore = ReturnType<typeof useUiStore>;
export type ThemeStore = ReturnType<typeof useThemeStore>;
export type TaskStore = ReturnType<typeof useTaskStore>;
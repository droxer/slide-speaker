import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Task } from '@/types';

interface TaskState {
  // Hidden tasks (for deleted tasks)
  hiddenTasks: Set<string>;
  hideTask: (taskId: string) => void;
  unhideTask: (taskId: string) => void;
  isTaskHidden: (taskId: string) => boolean;

  // Task defaults for run modal
  globalRunDefaults: {
    voice_language?: string;
    subtitle_language?: string | null;
    transcript_language?: string | null;
    video_resolution?: string;
  };
  setGlobalRunDefaults: (defaults: {
    voice_language?: string;
    subtitle_language?: string | null;
    transcript_language?: string | null;
    video_resolution?: string;
  }) => void;

  // Currently selected file for running a task
  selectedFileForRun: {
    upload_id: string;
    filename?: string;
    isPdf: boolean;
    taskType: 'video' | 'podcast';
  } | null;
  setSelectedFileForRun: (file: {
    upload_id: string;
    filename?: string;
    isPdf: boolean;
    taskType: 'video' | 'podcast';
  } | null) => void;

  // Task submission state
  isSubmittingTask: boolean;
  setSubmittingTask: (submitting: boolean) => void;
}

export const useTaskStore = create<TaskState>()(
  devtools(
    persist(
      (set, get) => ({
        // Hidden tasks (for deleted tasks)
        hiddenTasks: new Set(),
        hideTask: (taskId) => set((state) => {
          const newHiddenTasks = new Set(state.hiddenTasks);
          newHiddenTasks.add(taskId);
          return { hiddenTasks: newHiddenTasks };
        }),
        unhideTask: (taskId) => set((state) => {
          const newHiddenTasks = new Set(state.hiddenTasks);
          newHiddenTasks.delete(taskId);
          return { hiddenTasks: newHiddenTasks };
        }),
        isTaskHidden: (taskId) => get().hiddenTasks.has(taskId),

        // Task defaults for run modal
        globalRunDefaults: {
          voice_language: undefined,
          subtitle_language: null,
          transcript_language: null,
          video_resolution: 'hd',
        },
        setGlobalRunDefaults: (defaults) => set({ globalRunDefaults: defaults }),

        // Currently selected file for running a task
        selectedFileForRun: null,
        setSelectedFileForRun: (file) => set({ selectedFileForRun: file }),

        // Task submission state
        isSubmittingTask: false,
        setSubmittingTask: (submitting) => set({ isSubmittingTask: submitting }),
      }),
      {
        name: 'task-storage',
        partialize: (state) => ({
          globalRunDefaults: state.globalRunDefaults,
          hiddenTasks: Array.from(state.hiddenTasks) // Convert Set to Array for storage
        }),
        merge: (persistedState, currentState) => {
          // Convert Array back to Set when restoring from storage
          if (persistedState && typeof persistedState === 'object' && 'hiddenTasks' in persistedState) {
            return {
              ...currentState,
              ...(persistedState as object),
              hiddenTasks: new Set((persistedState as any).hiddenTasks || [])
            };
          }
          return { ...currentState, ...(persistedState as object || {}) };
        }
      }
    )
  )
);
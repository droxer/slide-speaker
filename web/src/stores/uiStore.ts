import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UiState {
  // Toast notifications
  toast: { type: 'success' | 'error' | 'info' | 'warning'; message: string } | null;
  setToast: (toast: { type: 'success' | 'error' | 'info' | 'warning'; message: string } | null) => void;

  // Modal states
  isTaskCreationModalOpen: boolean;
  isTaskProgressModalOpen: boolean;
  processingTaskId: string | null;
  openTaskCreationModal: () => void;
  closeTaskCreationModal: () => void;
  openTaskProgressModal: (taskId: string) => void;
  closeTaskProgressModal: () => void;

  // Search and filter states
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  statusFilter: string;
  setStatusFilter: (filter: string) => void;

  // Pagination
  currentPage: number;
  setCurrentPage: (page: number) => void;

  // UI visibility states
  collapsedGroups: Set<string>;
  toggleGroup: (groupId: string) => void;
  copiedTaskId: string | null;
  setCopiedTaskId: (taskId: string | null) => void;

  // Virtualization
  visibleCount: number;
  setVisibleCount: (count: number) => void;
}

export const useUiStore = create<UiState>()(
  devtools(
    persist(
      (set, get) => ({
        // Toast notifications
        toast: null,
        setToast: (toast) => set({ toast }),

        // Modal states
        isTaskCreationModalOpen: false,
        isTaskProgressModalOpen: false,
        processingTaskId: null,
        openTaskCreationModal: () => set({ isTaskCreationModalOpen: true }),
        closeTaskCreationModal: () => set({ isTaskCreationModalOpen: false }),
        openTaskProgressModal: (taskId) => set({ isTaskProgressModalOpen: true, processingTaskId: taskId }),
        closeTaskProgressModal: () => set({ isTaskProgressModalOpen: false, processingTaskId: null }),

        // Search and filter states
        searchQuery: '',
        setSearchQuery: (query) => set({ searchQuery: query }),

        statusFilter: 'all',
        setStatusFilter: (filter) => set({ statusFilter: filter }),

        // Pagination
        currentPage: 1,
        setCurrentPage: (page) => set({ currentPage: page }),

        // UI visibility states
        collapsedGroups: new Set(),
        toggleGroup: (groupId) => set((state) => {
          const newCollapsedGroups = new Set(state.collapsedGroups);
          if (newCollapsedGroups.has(groupId)) {
            newCollapsedGroups.delete(groupId);
          } else {
            newCollapsedGroups.add(groupId);
          }
          return { collapsedGroups: newCollapsedGroups };
        }),
        copiedTaskId: null,
        setCopiedTaskId: (taskId) => set({ copiedTaskId: taskId }),

        // Virtualization
        visibleCount: 20,
        setVisibleCount: (count) => set({ visibleCount: count }),
      }),
      {
        name: 'ui-storage', // name of the item in the storage (must be unique)
        partialize: (state) => ({
          statusFilter: state.statusFilter,
          currentPage: state.currentPage,
          collapsedGroups: Array.from(state.collapsedGroups) // Convert Set to Array for storage
        }),
        merge: (persistedState, currentState) => {
          // Convert Array back to Set when restoring from storage
          if (persistedState && typeof persistedState === 'object' && 'collapsedGroups' in persistedState) {
            return {
              ...currentState,
              ...(persistedState as object),
              collapsedGroups: new Set((persistedState as any).collapsedGroups || [])
            };
          }
          return { ...currentState, ...(persistedState as object || {}) };
        }
      }
    )
  )
);
import { useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTaskStore } from './taskStore';
import { useUiStore } from './uiStore';
import type { Task } from '@/types';

/**
 * Custom hook that integrates Zustand with React Query for task management
 * This hook provides functions that update both local Zustand state and invalidate React Query caches
 */
export const useQueryStore = () => {
  const queryClient = useQueryClient();
  const { hideTask, setSubmittingTask } = useTaskStore();
  const { setToast } = useUiStore();

  /**
   * Hide a task both in Zustand state and invalidate relevant queries
   */
  const hideTaskAndUpdateQueries = useCallback(
    async (taskId: string) => {
      // Update Zustand state
      hideTask(taskId);

      // Optimistically remove the task from any cached lists
      queryClient.setQueriesData(
        { predicate: ({ queryKey }) => Array.isArray(queryKey) && queryKey[0] === 'files' },
        (old: any) => {
          if (!old || !Array.isArray(old.files)) return old;
          const files = old.files
            .map((file: any) => ({
              ...file,
              tasks: Array.isArray(file.tasks)
                ? file.tasks.filter((t: any) => t?.task_id !== taskId)
                : file.tasks,
            }))
            .filter((file: any) => Array.isArray(file.tasks) ? file.tasks.length > 0 : true);
          return { ...old, files };
        }
      );

      queryClient.setQueriesData(
        { predicate: ({ queryKey }) => Array.isArray(queryKey) && queryKey[0] === 'tasks' },
        (old: any) => {
          if (!Array.isArray(old)) return old;
          return old.filter((t: any) => t?.task_id !== taskId);
        }
      );

      queryClient.setQueriesData(
        { predicate: ({ queryKey }) => Array.isArray(queryKey) && queryKey[0] === 'tasksSearch' },
        (old: any) => {
          if (!old || !Array.isArray(old.tasks)) return old;
          return { ...old, tasks: old.tasks.filter((t: any) => t?.task_id !== taskId) };
        }
      );

      // Invalidate relevant queries to ensure consistency
      await queryClient.invalidateQueries({ queryKey: ['tasks'] });
      await queryClient.invalidateQueries({ queryKey: ['files'] });
    },
    [queryClient, hideTask]
  );

  /**
   * Handle task deletion with proper error handling and state updates
   */
  const deleteTaskAndUpdateState = useCallback(
    async (taskId: string, deleteApiFunction: (taskId: string) => Promise<void>, purgeApiFunction?: (taskId: string) => Promise<void>) => {
      try {
        // Attempt normal deletion
        await deleteApiFunction(taskId);
      } catch (error: any) {
        const message = error?.response?.data?.error || error?.message || '';
        // If normal deletion fails with "cannot be cancelled" error, try purge
        if (typeof message === 'string' && message.toLowerCase().includes('cannot be cancelled') && purgeApiFunction) {
          await purgeApiFunction(taskId);
        } else {
          throw error;
        }
      }

      // Update state after successful deletion
      await hideTaskAndUpdateQueries(taskId);
      setToast({ type: 'success', message: 'Task deleted successfully' });
    },
    [hideTaskAndUpdateQueries, setToast]
  );

  /**
   * Handle task creation with proper state updates
   */
  const createTaskAndUpdateState = useCallback(
    async (createApiFunction: () => Promise<any>, successMessage: string = 'Task created successfully') => {
      try {
        setSubmittingTask(true);
        const result = await createApiFunction();
        setSubmittingTask(false);
        setToast({ type: 'success', message: successMessage });
        return result;
      } catch (error) {
        setSubmittingTask(false);
        setToast({ type: 'error', message: 'Failed to create task' });
        throw error;
      }
    },
    [setSubmittingTask, setToast]
  );

  return {
    hideTaskAndUpdateQueries,
    deleteTaskAndUpdateState,
    createTaskAndUpdateState,
  };
};
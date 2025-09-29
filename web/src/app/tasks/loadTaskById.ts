import resolveServerApiBaseUrl from '@/utils/serverApiBaseUrl';
import type { Task } from '@/types';

const TASK_REVALIDATE_SECONDS = 30;

export const taskRevalidate = TASK_REVALIDATE_SECONDS;

export async function loadTaskById(taskId: string): Promise<Task | null> {
  if (!taskId) return null;

  try {
    const baseUrl = resolveServerApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/task/${encodeURIComponent(taskId)}`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: TASK_REVALIDATE_SECONDS },
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      console.warn(`[loadTaskById] Unexpected status ${response.status} for task ${taskId}`);
      return null;
    }

    return (await response.json()) as Task;
  } catch (error) {
    console.warn(`[loadTaskById] failed to load task ${taskId}:`, error);
    return null;
  }
}

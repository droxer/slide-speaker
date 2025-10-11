import {cookies} from 'next/headers';
import resolveServerApiBaseUrl from '@/utils/serverApiBaseUrl';
import type { Task } from '@/types';

const TASK_REVALIDATE_SECONDS = 30;

export const taskRevalidate = TASK_REVALIDATE_SECONDS;

export async function loadTaskById(taskId: string): Promise<Task | null> {
  if (!taskId) return null;

  try {
    const baseUrl = resolveServerApiBaseUrl();
    const cookieStore = await cookies();
    const cookieHeader = cookieStore
      .getAll()
      .map(({name, value}) => `${name}=${value}`)
      .join('; ');

    const headers: Record<string, string> = {Accept: 'application/json'};
    if (cookieHeader) {
      headers.Cookie = cookieHeader;
    }

    const response = await fetch(`${baseUrl}/api/tasks/${encodeURIComponent(taskId)}`, {
      headers,
      credentials: 'include',
      next: {revalidate: TASK_REVALIDATE_SECONDS},
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

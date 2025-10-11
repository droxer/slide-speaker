import axios from 'axios';
import {resolveApiBaseUrl} from '@/utils/apiBaseUrl';
import type {HealthStatus} from '@/types/health';
import type {Task, DownloadsResponse} from '@/types';
import type {ProfileResponse} from '@/types/user';

const API_BASE_URL = resolveApiBaseUrl();

export const api = axios.create({
  baseURL: API_BASE_URL.length > 0 ? API_BASE_URL : undefined,
  withCredentials: true,
});

export type TaskRow = Task;

export interface TaskListResponse {
  tasks: TaskRow[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export const getTasks = async (params?: Record<string, string | number>): Promise<TaskListResponse> => {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()
    : '';
  const res = await api.get(`/api/tasks${qs}`);
  return res.data as TaskListResponse;
};

export const searchTasks = async (query: string, limit = 20) => {
  const res = await api.get(`/api/tasks/search?query=${encodeURIComponent(query)}&limit=${limit}`);
  return res.data as { tasks: TaskRow[] };
};

export const getDownloads = async (taskId: string) => {
  const res = await api.get(`/api/tasks/${taskId}/downloads`);
  return res.data as DownloadsResponse;
};

export const getTranscriptMarkdown = async (taskId: string) => {
  const res = await api.get(`/api/tasks/${taskId}/transcripts/markdown`, { headers: { Accept: 'text/markdown' } });
  return String(res.data || '');
};

export const getStats = async () => {
  const res = await api.get(`/api/tasks/statistics`);
  return res.data as Record<string, unknown>;
};

export const getTaskById = async (taskId: string): Promise<Task> => {
  const res = await api.get(`/api/tasks/${encodeURIComponent(taskId)}`);
  return res.data as Task;
};

export const deleteTask = async (taskId: string) => {
  await api.delete(`/api/tasks/${taskId}/delete`);
};

export const purgeTask = async (taskId: string) => {
  await api.delete(`/api/tasks/${taskId}/purge`);
};

export const cancelRun = async (taskId: string) => {
  const res = await api.post<{ message: string }>(`/api/tasks/${taskId}/cancel`);
  return res.data;
};

export const upload = async (payload: FormData | Record<string, unknown>) => {
  if (typeof FormData !== 'undefined' && payload instanceof FormData) {
    const res = await api.post(`/api/upload`, payload);
    return res.data as { file_id: string; task_id: string };
  }

  const res = await api.post(`/api/upload`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  return res.data as { file_id: string; task_id: string };
};

export const runFile = async (fileId: string, payload: any) => {
  const res = await api.post(`/api/files/${encodeURIComponent(fileId)}/run`, payload, { headers: { 'Content-Type': 'application/json' } });
  return res.data as { file_id: string; task_id: string };
};

export const getHealth = async (): Promise<HealthStatus> => {
  const res = await api.get<HealthStatus>(`/api/health`, { headers: { Accept: 'application/json' } });
  return res.data;
};

export const headTaskVideo = async (taskId: string) => {
  const res = await api.head(`/api/tasks/${taskId}/video`);
  return res.status >= 200 && res.status < 400;
};

export const getTaskProgress = async <T = any>(taskId: string) => {
  const res = await api.get<T>(`/api/tasks/${taskId}/progress`);
  return res.data;
};

export const getCurrentUserProfile = async (): Promise<ProfileResponse> => {
  const res = await api.get<ProfileResponse>('/api/users/me');
  return res.data;
};

export const updateCurrentUserProfile = async (
  payload: {name?: string | null; preferred_language?: string | null},
): Promise<ProfileResponse> => {
  const res = await api.patch<ProfileResponse>('/api/users/me', payload);
  return res.data;
};

export const getVttText = async (taskId: string, language?: string) => {
  const path = language
    ? `/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(language)}`
    : `/api/tasks/${taskId}/subtitles/vtt`;
  const res = await api.get(path, { headers: { Accept: 'text/vtt,*/*' } });
  return String(res.data || '');
};

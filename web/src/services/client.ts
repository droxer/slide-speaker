import axios from 'axios';

const api = axios.create({
  baseURL: '', // same-origin (proxy)
  headers: { 'Content-Type': 'application/json' },
});

export type TaskRow = any;

export const getTasks = async (params?: Record<string, string | number>) => {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()
    : '';
  const res = await api.get(`/api/tasks${qs}`);
  return res.data as { tasks: TaskRow[]; total: number; limit: number; offset: number; has_more: boolean };
};

export const searchTasks = async (query: string, limit = 20) => {
  const res = await api.get(`/api/tasks/search?query=${encodeURIComponent(query)}&limit=${limit}`);
  return res.data as { tasks: TaskRow[] };
};

export const getDownloads = async (taskId: string) => {
  const res = await api.get(`/api/tasks/${taskId}/downloads`);
  return res.data as { items: Array<{ type: string; url: string; download_url?: string }> };
};

export const getTranscriptMarkdown = async (taskId: string) => {
  const res = await api.get(`/api/tasks/${taskId}/transcripts/markdown`, { headers: { Accept: 'text/markdown' } });
  return String(res.data || '');
};

export const getStats = async () => {
  const res = await api.get(`/api/tasks/statistics`);
  return res.data as any;
};

export const deleteTask = async (taskId: string) => {
  await api.delete(`/api/tasks/${taskId}`);
};

export const purgeTask = async (taskId: string) => {
  await api.delete(`/api/tasks/${taskId}/purge`);
};

export const cancelRun = async (taskId: string) => {
  const res = await api.post<{ message: string }>(`/api/task/${taskId}/cancel`);
  return res.data;
};

export const upload = async (payload: any) => {
  const res = await api.post(`/api/upload`, payload, { headers: { 'Content-Type': 'application/json' } });
  return res.data as { file_id: string; task_id: string };
};

export const getHealth = async () => {
  const res = await api.get(`/api/health`, { headers: { Accept: 'application/json' } });
  return res.data as any;
};

export const headTaskVideo = async (taskId: string) => {
  const res = await api.head(`/api/tasks/${taskId}/video`);
  return res.status >= 200 && res.status < 400;
};

export const getTaskProgress = async <T = any>(taskId: string) => {
  const res = await api.get<T>(`/api/tasks/${taskId}/progress`);
  return res.data;
};

export const getVttText = async (taskId: string, language?: string) => {
  const path = language
    ? `/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(language)}`
    : `/api/tasks/${taskId}/subtitles/vtt`;
  const res = await api.get(path, { headers: { Accept: 'text/vtt,*/*' } });
  return String(res.data || '');
};


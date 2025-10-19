import axios from 'axios';
import {resolveApiBaseUrl} from '@/utils/apiBaseUrl';
import type {HealthStatus} from '@/types/health';
import type {Task, DownloadsResponse, PodcastScriptResponse} from '@/types';
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
  // Default parameters for better pagination
  const defaultParams = {
    limit: '20',
    offset: '0',
    ...params
  };

  const qs = '?' + new URLSearchParams(Object.entries(defaultParams).map(([k, v]) => [k, String(v)])).toString();
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

export interface UploadPayload {
  filename: string;
  file_data: string;
  voice_language?: string;
  subtitle_language?: string | null;
  transcript_language?: string | null;
  video_resolution?: string;
  generate_avatar?: boolean;
  generate_subtitles?: boolean;
  generate_podcast?: boolean;
  generate_video?: boolean;
  task_type?: 'video' | 'podcast' | 'both';
  source_type?: 'pdf' | 'slides' | 'audio';
}

export interface UploadResponse {
  file_id: string;
  upload_id?: string;
  task_id: string;
  message?: string | null;
}

export interface UploadSummary {
  id: string;
  user_id?: string | null;
  filename?: string | null;
  file_ext?: string | null;
  source_type?: string | null;
  content_type?: string | null;
  checksum?: string | null;
  size_bytes?: number | null;
  storage_path?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export const upload = async (payload: FormData | UploadPayload): Promise<UploadResponse> => {
  if (typeof FormData !== 'undefined' && payload instanceof FormData) {
    const res = await api.post<UploadResponse>(`/api/upload`, payload);
    return res.data;
  }

  const res = await api.post<UploadResponse>(`/api/upload`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  return res.data;
};



export const runFile = async (fileId: string, payload: any) => {
  const res = await api.post(`/api/files/${encodeURIComponent(fileId)}/run`, payload, { headers: { 'Content-Type': 'application/json' } });
  return res.data as { upload_id: string; task_id: string };
};

export const getHealth = async (): Promise<HealthStatus> => {
  const res = await api.get<HealthStatus>(`/api/health`, { headers: { Accept: 'application/json' } });
  return res.data;
};

export interface TaskProgressResponse {
  status: string;
  progress: number;
  current_step: string;
  steps: Record<string, unknown>;
  errors?: unknown[];
  filename?: string;
  file_ext?: string;
  source_type?: string;
  voice_language?: string;
  subtitle_language?: string;
  generate_podcast?: boolean;
  generate_video?: boolean;
  task_type?: string;
  created_at?: string;
  updated_at?: string;
  message?: string;
}

export const getTaskProgress = async <T = TaskProgressResponse>(taskId: string): Promise<T> => {
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

export const getPodcastScript = async (taskId: string): Promise<PodcastScriptResponse> => {
  const res = await api.get(`/api/tasks/${taskId}/podcast/script`);
  return res.data as PodcastScriptResponse;
};

export const getUploads = async (): Promise<{ uploads: UploadSummary[] }> => {
  const res = await api.get(`/api/uploads`);
  const data = res.data as { uploads?: UploadSummary[] } | UploadSummary[];
  if (Array.isArray(data)) {
    return { uploads: data };
  }
  return { uploads: Array.isArray(data?.uploads) ? data.uploads : [] };
};

export const getCurrentUserProfile = async (): Promise<ProfileResponse> => {
  const res = await api.get<ProfileResponse>('/api/users/me');
  return res.data;
};

export const updateCurrentUserProfile = async (
  payload: {name?: string | null; preferred_language?: string | null; preferred_theme?: string | null},
): Promise<ProfileResponse> => {
  const res = await api.patch<ProfileResponse>('/api/users/me', payload);
  return res.data;
};

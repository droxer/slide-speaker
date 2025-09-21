import { useMutation, useQuery, useQueryClient, QueryClient } from '@tanstack/react-query';
import { getTasks, getStats, searchTasks, getDownloads, getTranscriptMarkdown, getVttText, cancelRun, purgeTask } from './client';
import type { Task } from '../types';

export const queries = {
  tasks: (filters: { status: string; page: number; limit: number }) => ['tasks', filters] as const,
  stats: () => ['stats'] as const,
  search: (q: string) => ['tasksSearch', q] as const,
  downloads: (taskId: string) => ['downloads', taskId] as const,
  transcript: (taskId: string) => ['transcript', taskId] as const,
  vtt: (taskId: string, language?: string) => (language ? (['vtt', taskId, language] as const) : (['vtt', taskId] as const)),
};

export const useTasksQuery = (
  filters: { status: string; page: number; limit: number },
  opts?: {
    refetchInterval?: number | false | ((q: any) => number | false);
    staleTime?: number;
  }
) => {
  return useQuery<Task[]>({
    queryKey: queries.tasks(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status !== 'all') params.append('status', filters.status);
      params.append('limit', String(filters.limit));
      params.append('offset', String((filters.page - 1) * filters.limit));
      const res = await getTasks(Object.fromEntries(params));
      const real = (res.tasks || []).filter((t: any) => typeof t?.task_id === 'string' && !t.task_id.startsWith('state_'));
      return real as Task[];
    },
    refetchInterval: opts?.refetchInterval,
    staleTime: opts?.staleTime ?? 10000,
  });
};

export const useStatsQuery = () => {
  return useQuery({ queryKey: queries.stats(), queryFn: () => getStats(), refetchInterval: 30000, refetchOnMount: true });
};

export const useSearchTasksQuery = (q: string) => {
  const query = q.trim();
  return useQuery({ queryKey: queries.search(query), queryFn: () => searchTasks(query), enabled: query.length > 0, staleTime: 0 });
};

export const useVttQuery = (taskId: string | null, language?: string, enabled?: boolean) => {
  return useQuery({
    queryKey: queries.vtt(taskId || '', language),
    queryFn: async () => {
      if (!taskId) return '';
      let text = '';
      try { text = await getVttText(taskId, language); } catch {}
      if (!text) { try { text = await getVttText(taskId); } catch {} }
      return text;
    },
    enabled: Boolean(taskId) && (enabled ?? true),
  });
};

export const prefetchDownloads = async (qc: QueryClient, taskId: string) => {
  return qc.fetchQuery({ queryKey: queries.downloads(taskId), queryFn: () => getDownloads(taskId) });
};

export const prefetchTranscript = async (qc: QueryClient, taskId: string) => {
  return qc.fetchQuery({ queryKey: queries.transcript(taskId), queryFn: () => getTranscriptMarkdown(taskId) });
};

export const prefetchVtt = async (qc: QueryClient, taskId: string, language?: string) => {
  return qc.prefetchQuery({ queryKey: queries.vtt(taskId, language), queryFn: () => getVttText(taskId, language) });
};

export const useDownloadsQuery = (taskId: string | null, enabled = true) => {
  const id = taskId || '';
  return useQuery({ queryKey: queries.downloads(id), queryFn: () => getDownloads(id), enabled: Boolean(taskId) && enabled });
};

export const useTranscriptQuery = (taskId: string | null, enabled = true) => {
  const id = taskId || '';
  return useQuery({ queryKey: queries.transcript(id), queryFn: () => getTranscriptMarkdown(id), enabled: Boolean(taskId) && enabled });
};

// Cache selectors (helpers)
export const getCachedDownloads = (qc: QueryClient, taskId: string) => {
  return qc.getQueryData(queries.downloads(taskId)) as { items?: Array<{ type: string; url: string; download_url?: string }>} | undefined;
};

export const getCachedTranscript = (qc: QueryClient, taskId: string) => {
  return qc.getQueryData(queries.transcript(taskId)) as string | undefined;
};

export const hasCachedVideo = (qc: QueryClient, taskId: string) => {
  const dl = getCachedDownloads(qc, taskId);
  return Array.isArray(dl?.items) ? dl!.items!.some((it) => it?.type === 'video') : false;
};

export const hasCachedPodcast = (qc: QueryClient, taskId: string) => {
  const dl = getCachedDownloads(qc, taskId);
  return Array.isArray(dl?.items) ? dl!.items!.some((it) => it?.type === 'podcast') : false;
};

export const hasCachedVtt = (qc: QueryClient, taskId: string, language?: string) => {
  const vttWithLang = qc.getQueryData(queries.vtt(taskId, language));
  const vttNoLang = qc.getQueryData(queries.vtt(taskId));
  const text = (vttWithLang as any) ?? (vttNoLang as any);
  return typeof text === 'string' && text.length > 0;
};

export const prefetchTaskPreview = async (
  qc: QueryClient,
  taskId: string,
  opts?: { language?: string; podcast?: boolean }
) => {
  const language = opts?.language;
  const podcast = opts?.podcast === true;
  await prefetchDownloads(qc, taskId);
  if (podcast) {
    await prefetchTranscript(qc, taskId);
  } else {
    if (language) await prefetchVtt(qc, taskId, language);
    await prefetchVtt(qc, taskId);
  }
};

export const useCancelTaskMutation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => cancelRun(taskId),
    onSettled: async () => {
      await qc.invalidateQueries({ queryKey: queries.tasks({ status: 'all', page: 1, limit: 10 }) as any, exact: false });
      await qc.invalidateQueries({ queryKey: queries.search('') as any, exact: false });
    },
  });
};

export const usePurgeTaskMutation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => purgeTask(taskId),
    onSettled: async () => {
      await qc.invalidateQueries({ queryKey: queries.tasks({ status: 'all', page: 1, limit: 10 }) as any, exact: false });
      await qc.invalidateQueries({ queryKey: queries.search('') as any, exact: false });
    },
  });
};

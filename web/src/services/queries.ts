import { useMutation, useQuery, useQueryClient, QueryClient } from '@tanstack/react-query';
import { getTasks, searchTasks, getDownloads, getTranscriptMarkdown, getVttText, cancelRun, deleteTask, runFile, getTaskById, getPodcastScript, getUploads, getCurrentUserProfile, updateCurrentUserProfile, type UploadSummary } from './client';
import type { Task } from '../types';
import type { ProfileResponse } from '@/types/user';

export const queries = {
  tasks: {
    list: (filters: { status: string; page: number; limit: number }) => ['tasks', 'list', filters] as const,
    search: (q: string) => ['tasks', 'search', q] as const,
    detail: (taskId: string) => ['tasks', 'detail', taskId] as const,
  },
  downloads: (taskId: string) => ['downloads', taskId] as const,
  transcript: (taskId: string) => ['transcript', taskId] as const,
  vtt: (taskId: string, language?: string) => (language ? (['vtt', taskId, language] as const) : (['vtt', taskId] as const)),
  podcastScript: (taskId: string) => ['podcastScript', taskId] as const,
  user: {
    profile: () => ['user', 'profile'] as const,
  },
};

export const useTasksQuery = (
  filters: { status: string; page: number; limit: number },
  opts?: {
    refetchInterval?: number | false | ((q: any) => number | false);
    staleTime?: number;
    refetchIntervalInBackground?: boolean;
  }
) => {
  return useQuery<Task[]>({
    queryKey: queries.tasks.list(filters),
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
    staleTime: opts?.staleTime ?? (filters.status === 'completed' ? 5 * 60 * 1000 : 30 * 1000),
    refetchIntervalInBackground: opts?.refetchIntervalInBackground,
  });
};

export const useSearchTasksQuery = (q: string) => {
  const query = q.trim();
  return useQuery({ queryKey: queries.tasks.search(query), queryFn: () => searchTasks(query), enabled: query.length > 0, staleTime: 0 });
};

export const prefetchDownloads = async (qc: QueryClient, taskId: string) => {
  return qc.fetchQuery({ queryKey: queries.downloads(taskId), queryFn: () => getDownloads(taskId) });
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
  return useQuery({
    queryKey: queries.transcript(id),
    queryFn: async () => {
      return getTranscriptMarkdown(id);
    },
    enabled: Boolean(taskId) && enabled
  });
};

export const usePodcastScriptQuery = (taskId: string | null, enabled = true) => {
  const id = taskId || '';
  return useQuery({
    queryKey: queries.podcastScript(id),
    queryFn: async () => {
      return getPodcastScript(id);
    },
    enabled: Boolean(taskId) && enabled,
  });
};

// User profile queries
export const useUserProfileQuery = () => {
  return useQuery<ProfileResponse>({
    queryKey: queries.user.profile(),
    queryFn: getCurrentUserProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
    // Disable polling when page is not visible to enable bfcache
    refetchIntervalInBackground: false,
  });
};

export const useUpdateUserProfileMutation = () => {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: updateCurrentUserProfile,
    onSuccess: (updatedProfile) => {
      // Update the cache with the new profile data
      qc.setQueryData(queries.user.profile(), updatedProfile);
    },
  });
};

export const prefetchUserProfile = async (qc: QueryClient) => {
  return qc.prefetchQuery({
    queryKey: queries.user.profile(),
    queryFn: getCurrentUserProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useTaskQuery = (
  taskId: string,
  initialData?: Task | null,
  opts?: {
    refetchInterval?: number | false | ((q: any) => number | false);
    staleTime?: number;
    refetchIntervalInBackground?: boolean;
  }
) => {
  return useQuery<Task | null>({
    queryKey: queries.tasks.detail(taskId),
    queryFn: async () => {
      if (!taskId) return null;
      try {
        return await getTaskById(taskId);
      } catch (error: any) {
        if (error?.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: Boolean(taskId),
    staleTime: opts?.staleTime ?? (initialData?.status === 'completed' ? 10 * 60 * 1000 : 30_000),
    refetchInterval: opts?.refetchInterval,
    refetchIntervalInBackground: opts?.refetchIntervalInBackground,
    initialData: initialData ?? undefined,
  });
};

// Cache selectors (helpers)
export const getCachedDownloads = (qc: QueryClient, taskId: string) => {
  return qc.getQueryData(queries.downloads(taskId)) as { items?: Array<{ type: string; url: string; download_url?: string }>} | undefined;
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
    // prefetchPodcastScript was removed as unused
  } else {
    if (language) await prefetchVtt(qc, taskId, language);
    await prefetchVtt(qc, taskId);
  }
};

// Enhanced prefetching with better error handling
export const prefetchTaskDetail = async (qc: QueryClient, taskId: string) => {
  try {
    // Prefetch with error boundaries
    await Promise.allSettled([
      qc.prefetchQuery({
        queryKey: queries.tasks.detail(taskId),
        queryFn: () => getTaskById(taskId),
        staleTime: 5 * 60 * 1000 // 5 minutes for task details
      }),
      qc.prefetchQuery({
        queryKey: queries.downloads(taskId),
        queryFn: () => getDownloads(taskId),
        staleTime: 2 * 60 * 1000 // 2 minutes for downloads
      })
    ]);
  } catch (error) {
    console.warn('Prefetch failed:', error);
    // Don't throw - prefetch failures shouldn't break the UI
  }
};

// Cache management utilities
export const evictOldTaskQueries = (qc: QueryClient, maxAgeMinutes = 60) => {
  const now = Date.now();
  const cutoff = now - (maxAgeMinutes * 60 * 1000);

  qc.getQueryCache().findAll().forEach(query => {
    if (
      Array.isArray(query.queryKey) &&
      query.queryKey[0] === 'tasks' &&
      query.queryKey[1] === 'detail' &&
      query.state.dataUpdatedAt < cutoff
    ) {
      qc.removeQueries({ queryKey: query.queryKey });
    }
  });
};

export const evictOldListQueries = (qc: QueryClient, maxAgeMinutes = 30) => {
  const now = Date.now();
  const cutoff = now - (maxAgeMinutes * 60 * 1000);

  qc.getQueryCache().findAll().forEach(query => {
    if (
      Array.isArray(query.queryKey) &&
      query.queryKey[0] === 'tasks' &&
      query.queryKey[1] === 'list' &&
      query.state.dataUpdatedAt < cutoff
    ) {
      qc.removeQueries({ queryKey: query.queryKey });
    }
  });
};

export const useCancelTaskMutation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => cancelRun(taskId),
    onMutate: async (taskId) => {
      // Cancel any outgoing refetches
      await qc.cancelQueries({ queryKey: queries.tasks.detail(taskId) });

      // Snapshot the previous value
      const previousTask = qc.getQueryData(queries.tasks.detail(taskId));

      // Optimistically update to 'cancelling' status
      qc.setQueryData(queries.tasks.detail(taskId), (old: any) => ({
        ...old,
        status: 'cancelling'
      }));

      return { previousTask, taskId };
    },
    onError: (err, taskId, context: any) => {
      // Rollback on error
      qc.setQueryData(queries.tasks.detail(taskId), context.previousTask);
    },
    onSettled: async (data, error, variables) => {
      const taskId = variables;
      // Refetch after mutation
      await qc.invalidateQueries({ queryKey: queries.tasks.detail(taskId) });

      // For task lists, use updateQueryData instead of invalidation when possible
      qc.setQueriesData(
        { queryKey: ['tasks'], exact: false },
        (oldData: any) => {
          if (!Array.isArray(oldData)) return oldData;
          return oldData.map((task: any) =>
            task.task_id === taskId ? { ...task, status: 'cancelled' } : task
          );
        }
      );

      qc.setQueriesData(
        { queryKey: ['files'], exact: false },
        (oldData: any) => {
          if (!oldData?.files) return oldData;
          return {
            ...oldData,
            files: oldData.files.map((fileGroup: any) => ({
              ...fileGroup,
              tasks: fileGroup.tasks?.map((task: any) =>
                task.task_id === taskId ? { ...task, status: 'cancelled' } : task
              ) || []
            }))
          };
        }
      );
    },
  });
};

export const useFilesQuery = (
  filters: { page: number; limit: number; includeTasks?: boolean; q?: string },
  opts?: {
    refetchInterval?: number | false | ((q: any) => number | false);
    staleTime?: number;
    refetchIntervalInBackground?: boolean;
  },
) => {
  return useQuery({
    queryKey: ['files', filters] as const,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.q) params.append('q', filters.q);
      params.append('limit', String(filters.limit));
      params.append('offset', String((filters.page - 1) * filters.limit));

      const [taskRes, uploadsRes] = await Promise.all([
        getTasks(Object.fromEntries(params)),
        getUploads(),
      ]);
      const tasks = (taskRes.tasks || []).filter(
        (t: any) => typeof t?.task_id === 'string' && !t.task_id.startsWith('state_'),
      ) as Task[];
      const uploads: UploadSummary[] = Array.isArray(uploadsRes.uploads) ? uploadsRes.uploads : [];

      type FileGroup = {
        upload_id?: string;
        filename?: string;
        file_ext?: string;
        source_type?: string | null;
        tasks: Task[];
        uploadOnly: boolean;
        uploadCreatedAt?: string | null;
        uploadUpdatedAt?: string | null;
        upload?: UploadSummary;
        latestUpdatedAt?: number;
      };

      const filesMap = new Map<string, FileGroup>();

      for (const upload of uploads) {
        const key = upload.id || '';
        filesMap.set(key || `upload:${upload.filename || 'unknown'}`, {
          upload_id: upload.id ?? undefined,
          filename: upload.filename ?? undefined,
          file_ext: upload.file_ext ?? undefined,
          source_type: upload.source_type ?? null,
          tasks: [],
          uploadOnly: true,
          uploadCreatedAt: upload.created_at ?? null,
          uploadUpdatedAt: upload.updated_at ?? null,
          upload,
          latestUpdatedAt: upload.updated_at ? Date.parse(upload.updated_at) : undefined,
        });
      }

      for (const task of tasks) {
        const uploadId = task.upload_id || task.kwargs?.upload_id;
        const taskFilename = task.filename || task.kwargs?.filename || task.state?.filename;
        const taskFileExt = task.file_ext || task.kwargs?.file_ext;
        const key = uploadId || `task:${task.task_id}`;
        if (!filesMap.has(key)) {
          filesMap.set(key, {
            upload_id: uploadId ?? undefined,
            filename: taskFilename,
            file_ext: taskFileExt,
            source_type: (task as any)?.source_type || task.kwargs?.source_type || null,
            tasks: [],
            uploadOnly: true,
            uploadCreatedAt: task.created_at,
            uploadUpdatedAt: task.updated_at,
            latestUpdatedAt: Date.parse(task.updated_at || task.created_at || ''),
          });
        }
        const group = filesMap.get(key)!;
        group.tasks.push(task);
        group.filename = group.filename || taskFilename;
        group.file_ext = group.file_ext || taskFileExt;
        group.source_type = group.source_type || (task as any)?.source_type || task.kwargs?.source_type || null;
        group.uploadOnly = false;
        const updatedTs = Date.parse(task.updated_at || task.created_at || '');
        if (!Number.isNaN(updatedTs)) {
          group.latestUpdatedAt = Math.max(group.latestUpdatedAt ?? updatedTs, updatedTs);
        }
      }

      const files = Array.from(filesMap.values()).sort((a, b) => {
        const aTime = (a.latestUpdatedAt ?? Date.parse(a.uploadUpdatedAt || a.uploadCreatedAt || '')) || 0;
        const bTime = (b.latestUpdatedAt ?? Date.parse(b.uploadUpdatedAt || b.uploadCreatedAt || '')) || 0;
        return bTime - aTime;
      });

      return {
        files,
        has_more: taskRes.has_more,
        total: taskRes.total,
      };
    },
    refetchInterval: opts?.refetchInterval,
    staleTime: opts?.staleTime ?? 2 * 60 * 1000, // 2 minutes for files data
    refetchIntervalInBackground: opts?.refetchIntervalInBackground,
    // Only fetch when the component is visible
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
};

export const useRunFileTaskMutation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ uploadId, payload }: { uploadId: string; payload: any }) => runFile(uploadId, payload),
    onMutate: async ({ uploadId, payload }) => {
      // Cancel any outgoing refetches
      await qc.cancelQueries({ queryKey: ['files'] as any, exact: false });
      await qc.cancelQueries({ queryKey: queries.tasks.list({ status: 'all', page: 1, limit: 10 }) as any, exact: false });
      await qc.cancelQueries({ queryKey: queries.tasks.search('') as any, exact: false });
    },
    onSettled: async () => {
      await qc.invalidateQueries({ queryKey: ['files'] as any, exact: false });
      await qc.invalidateQueries({ queryKey: queries.tasks.list({ status: 'all', page: 1, limit: 10 }) as any, exact: false });
      await qc.invalidateQueries({ queryKey: queries.tasks.search('') as any, exact: false });
    },
  });
};

export const usePurgeTaskMutation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => deleteTask(taskId),
    onMutate: async (taskId) => {
      // Cancel any outgoing refetches
      await qc.cancelQueries({ queryKey: queries.tasks.list({ status: 'all', page: 1, limit: 10 }) as any, exact: false });
      await qc.cancelQueries({ queryKey: queries.tasks.search('') as any, exact: false });

      // Optimistically remove the task from cache
      qc.setQueriesData(
        { queryKey: ['tasks'], exact: false },
        (oldData: any) => {
          if (!Array.isArray(oldData)) return oldData;
          return oldData.filter((task: any) => task.task_id !== taskId);
        }
      );

      qc.setQueriesData(
        { queryKey: ['files'], exact: false },
        (oldData: any) => {
          if (!oldData?.files) return oldData;
          return {
            ...oldData,
            files: oldData.files
              .map((fileGroup: any) => ({
                ...fileGroup,
                tasks: fileGroup.tasks?.filter((task: any) => task.task_id !== taskId) || []
              }))
              .filter((fileGroup: any) =>
                fileGroup.tasks?.length > 0 || fileGroup.uploadOnly
              )
          };
        }
      );
    },
    onSettled: async () => {
      await qc.invalidateQueries({ queryKey: queries.tasks.list({ status: 'all', page: 1, limit: 10 }) as any, exact: false });
      await qc.invalidateQueries({ queryKey: queries.tasks.search('') as any, exact: false });
    },
  });
};

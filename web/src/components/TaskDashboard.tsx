'use client';

import React, { useCallback, useEffect, useMemo, useState, useRef, lazy, Suspense } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { cancelRun as apiCancelRun, deleteTask as apiDeleteTask, purgeTask as apiPurgeTask, getHealth } from '../services/client';
import type { UploadSummary } from '../services/client';
import { useCancelTaskMutation, useFilesQuery, useRunFileTaskMutation, useSearchTasksQuery, useTaskQuery, prefetchTaskDetail, evictOldTaskQueries, evictOldListQueries } from '../services/queries';
import { Link } from '@/navigation';
import { getGlobalRunDefaults, saveGlobalRunDefaults } from '../utils/defaults';
import type { Task } from '../types';
import { useI18n } from '@/i18n/hooks';
import { getLanguageDisplayName } from '../utils/language';
import { getTaskStatusClass, getTaskStatusIcon, getTaskStatusLabel, type TaskStatus } from '@/utils/taskStatus';
import { getFileTypeIcon, getFileTypeCategory, isPdf, isPowerPoint } from '@/utils/fileIcons';
import { resolveTaskType } from '@/utils/taskType';

// Lazy load non-critical modal components
const TaskCreationModal = lazy(() => import('./TaskCreationModal'));
const TaskProgressModal = lazy(() => import('./TaskProgressModal'));

interface TaskDashboardProps { apiBaseUrl: string }

const shortId = (id?: string) => {
  if (!id) return '';
  if (id.length <= 12) return id;
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
};


const RESOLUTION_KEYS: Record<string, string> = {
  sd: 'runTask.resolution.sd',
  hd: 'runTask.resolution.hd',
  fullhd: 'runTask.resolution.fullhd',
};

type FileGroup = {
  upload_id?: string;
  filename?: string;
  file_ext?: string;
  source_type?: string | null;
  tasks: Task[];
  uploadOnly?: boolean;
  upload?: UploadSummary;
  uploadCreatedAt?: string | null;
  uploadUpdatedAt?: string | null;
};

const TaskDashboard = ({ apiBaseUrl }: TaskDashboardProps) => {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [status, setStatus] = useState('all');
  const { t } = useI18n();
  const [page, setPage] = useState(1);
  const [toast, setToast] = useState<{ type: 'success'|'error'; message: string }|null>(null);
  const [runOpen, setRunOpen] = useState(false);
  const [runFile, setRunFile] = useState<{ upload_id: string; filename?: string; isPdf: boolean } | null>(null);
  const [runDefaults, setRunDefaults] = useState<any>({});
  const [runSubmitting, setRunSubmitting] = useState(false);
  const [processingTask, setProcessingTask] = useState<Task | null>(null);
  const queryClient = useQueryClient();
  const [hiddenTasks, setHiddenTasks] = useState<Set<string>>(new Set());
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [copiedTaskId, setCopiedTaskId] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(20); // Initial visible items for virtualization
  const containerRef = useRef<HTMLDivElement>(null);

  // Periodically clean up old cache entries
  useEffect(() => {
    const interval = setInterval(() => {
      evictOldTaskQueries(queryClient, 60); // Evict task detail queries older than 60 minutes
      evictOldListQueries(queryClient, 30); // Evict list queries older than 30 minutes
    }, 10 * 60 * 1000); // Run every 10 minutes

    return () => clearInterval(interval);
  }, [queryClient]);

  useEffect(() => { const t = setTimeout(() => setDebounced(search.trim()), 350); return () => clearTimeout(t); }, [search]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

  // Intersection Observer for infinite scrolling
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          // Load more items when user scrolls near the bottom
          setVisibleCount((prev) => Math.min(prev + 10, 100)); // Cap at 100 items
        }
      },
      { threshold: 0.1 }
    );

    const sentinel = containerRef.current.querySelector('.pagination-sentinel');
    if (sentinel) {
      observer.observe(sentinel);
    }

    return () => observer.disconnect();
  }, []);

  const formatFileName = useCallback((name?: string, max = 42): string => {
    if (!name) return t('common.unknownFile', undefined, 'Unknown file');
    const base = name.replace(/\.(pdf|pptx?|PPTX?|PDF)$/,'');
    if (base.length <= max) return base;
    const head = Math.max(12, Math.floor((max - 1) / 2));
    const tail = max - head - 1;
    return base.slice(0, head) + '…' + base.slice(-tail);
  }, [t]);

  const getLanguageName = useCallback((code: string) => {
    const normalized = (code || '').toLowerCase();
    const fallback = getLanguageDisplayName(code);
    return t(`language.display.${normalized}`, undefined, fallback || t('common.unknown', undefined, 'Unknown'));
  }, [t]);

  const getResolutionName = useCallback((value: string) => {
    const normalized = (value || '').toLowerCase();
    const key = RESOLUTION_KEYS[normalized];
    if (key) return t(key, undefined, value);
    return t('common.unknown', undefined, 'Unknown');
  }, [t]);

  const filesQuery = useFilesQuery(
    { page, limit: 10, includeTasks: true, q: debounced || undefined },
    {
      refetchInterval: (q: any) => {
        const files = (q?.state?.data as any)?.files || [];
        const hasActive = files.some((f: any) => (f.tasks || []).some((t: Task) => t.status === 'processing' || t.status === 'queued'));
        return hasActive ? 15000 : false;
      },
      staleTime: 2 * 60 * 1000, // 2 minutes for files data
      // Disable polling when page is not visible to enable bfcache
      refetchIntervalInBackground: false,
    },
  );
  const searchQuery = useSearchTasksQuery(debounced);
  const searching = debounced.length > 0;

  // Health indicator (Redis/DB) - with cleanup for bfcache compatibility
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
    staleTime: 20000,
    // Disable polling when page is not visible to enable bfcache
    refetchIntervalInBackground: false,
  });
  const health = (healthQuery.data as any) || {};
  const overall = String(health.status || 'unknown');
  const redisOk = Boolean(health?.redis?.ok);
  const dbOk = Boolean(health?.db?.ok);
  const redisLatency = health?.redis?.latency_ms as number | undefined;
  const dbLatency = health?.db?.latency_ms as number | undefined;
  const redisError = health?.redis?.error as string | undefined;
  const dbError = health?.db?.error as string | undefined;
  const overallLabel = overall === 'ok'
    ? t('creations.health.overall.okLabel')
    : overall === 'degraded'
      ? t('creations.health.overall.degradedLabel')
      : overall === 'down'
        ? t('creations.health.overall.downLabel')
        : t('creations.health.overall.unknownLabel');
  const queueTooltip = redisOk
    ? t('creations.health.queueLatency', { latency: typeof redisLatency === 'number' ? redisLatency : 'n/a' }, `Queue latency: ${redisLatency ?? 'n/a'} ms`)
    : (redisError || t('creations.health.queueUnavailable'));
  const dbTooltip = dbOk
    ? t('creations.health.databaseLatency', { latency: typeof dbLatency === 'number' ? dbLatency : 'n/a' }, `Database latency: ${dbLatency ?? 'n/a'} ms`)
    : (dbError || t('creations.health.databaseUnavailable'));

  // Build groups when searching (upload_id -> tasks)
  const searchGroups = useMemo(() => {
    if (!searching) return [] as Array<{ upload_id?: string; filename?: string; file_ext?: string; tasks: Task[] }>;
    const items: Task[] = (((searchQuery.data as any)?.tasks) || []) as Task[];
    const map = new Map<string, { upload_id?: string; filename?: string; file_ext?: string; tasks: Task[]; newest: number }>();
    for (const t of items) {
      const fid = t.upload_id || (t as any)?.kwargs?.upload_id;
      const tFilename = t.filename || (t as any)?.kwargs?.filename || t.state?.filename;
      const tFileExt = t.file_ext || (t as any)?.kwargs?.file_ext;
      const key = fid || `unknown:${tFilename || 'Unknown'}`;
      const updated = Date.parse(t.updated_at || t.created_at || '') || 0;
      if (!map.has(key)) map.set(key, { upload_id: fid, filename: tFilename, file_ext: tFileExt, tasks: [t], newest: updated });
      else { const g = map.get(key)!; g.tasks.push(t); g.newest = Math.max(g.newest, updated); g.filename ||= tFilename; g.file_ext ||= tFileExt; }
    }
    const groups = Array.from(map.values()).sort((a, b) => b.newest - a.newest);
    for (const g of groups) g.tasks.sort((a, b) => Date.parse(b.updated_at || b.created_at) - Date.parse(a.updated_at || a.created_at));
    return groups.map(({ newest, ...rest }) => rest);
  }, [searching, searchQuery.data]);

  const counts = useMemo(() => {
    const filterHidden = (tasks: Task[]) => tasks.filter((t) => !hiddenTasks.has(t.task_id));
    if (searching) {
      const filesCount = searchGroups.filter((g) => {
        const visible = filterHidden(g.tasks);
        const vis = status === 'all' ? visible : visible.filter((t) => t.status === status);
        return vis.length > 0;
      }).length;
      const creationsCount = searchGroups.reduce((n, g) => {
        const visible = filterHidden(g.tasks);
        const vis = status === 'all' ? visible : visible.filter((t) => t.status === status);
        return n + vis.length;
      }, 0);
      const runningCount = searchGroups.reduce((n, g) => n + filterHidden(g.tasks).filter((t) => t.status === 'processing').length, 0);
      return { filesCount, creationsCount, runningCount };
    }
    const filesData = filesQuery.data as any;
    const files = (filesData?.files || []) as Array<{ tasks?: Task[]; uploadOnly?: boolean }>;
    let filesCount = 0, creationsCount = 0, runningCount = 0;
    for (const f of files) {
      const tasks = filterHidden((f.tasks || []) as Task[]);
      const vis = status === 'all' ? tasks : tasks.filter((t) => t.status === status);
      const isUploadOnly = Boolean(f.uploadOnly);
      if (vis.length > 0 || (status === 'all' && isUploadOnly)) filesCount++;
      creationsCount += vis.length;
      runningCount += tasks.filter((t) => t.status === 'processing').length;
    }
    return { filesCount, creationsCount, runningCount, total: filesData?.total || 0 };
  }, [searching, searchGroups, filesQuery.data, status, hiddenTasks]);

  const STATUS_ORDER: TaskStatus[] = ['processing', 'queued', 'completed', 'failed', 'cancelled'];

  const formatTimestamp = useCallback(
    (iso?: string | null) => {
      if (!iso) return t('common.unknown', undefined, 'Unknown');
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) {
        return t('common.unknown', undefined, 'Unknown');
      }
      return date.toLocaleString();
    },
    [t],
  );

  const toggleGroup = useCallback((groupKey: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) next.delete(groupKey);
      else next.add(groupKey);
      return next;
    });
  }, []);

  const handleCopyTaskId = useCallback(async (taskId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(taskId);
      setCopiedTaskId(taskId);
      // Show feedback for 2 seconds
      setTimeout(() => setCopiedTaskId(null), 2000);
    } catch (error) {
      console.error('Failed to copy task ID:', error);
    }
  }, []);

  const renderFileGroup = (group: FileGroup, key: string) => {
    const allTasks = [...(group.tasks || [])]
      .filter((task) => !hiddenTasks.has(task.task_id))
      .sort(
        (a, b) =>
          Date.parse(b.updated_at || b.created_at || '') - Date.parse(a.updated_at || a.created_at || ''),
      );
    const filteredTasks = status === 'all' ? allTasks : allTasks.filter((task) => task.status === status);
    const showPlaceholder = group.uploadOnly && status === 'all' && allTasks.length === 0;

    if (!showPlaceholder && filteredTasks.length === 0) {
      return null;
    }

    const referenceTask = filteredTasks[0] ?? allTasks[0];
    const fileName = group.filename || referenceTask?.filename || group.upload?.filename;
    const fileExt = group.file_ext || referenceTask?.file_ext || group.upload?.file_ext;
    const actionUploadId = group.upload_id || group.upload?.id || referenceTask?.upload_id || null;
    const effectiveFileExt = fileExt || referenceTask?.file_ext || '';

    const statusCounts = allTasks.reduce<Record<string, number>>((acc, task) => {
      if (task.status === 'upload_only') return acc;
      acc[task.status] = (acc[task.status] ?? 0) + 1;
      return acc;
    }, {});

    const hasUploadActions = Boolean(actionUploadId);
    const normalizedExt = (effectiveFileExt || '').toLowerCase();
    const isPdfFile = isPdf(effectiveFileExt);
    const isPresentationFile = normalizedExt.includes('ppt');
    const activeStatus = allTasks.find((task) => task.status === 'processing' || task.status === 'queued')?.status ?? null;
    const lastUpdatedIso =
      referenceTask?.updated_at ??
      referenceTask?.created_at ??
      group.uploadUpdatedAt ??
      group.upload?.updated_at ??
      group.uploadCreatedAt ??
      group.upload?.created_at ??
      null;
    // Only show status pills for in-progress tasks (processing and queued)
    const statusPills = STATUS_ORDER.filter((state) => statusCounts[state] && (state === 'processing' || state === 'queued')).map((state) => (
      <span
        key={state}
        className={`file-status-pill status-${state}${activeStatus === state ? ' is-active' : ''}`}
      >
        <span className="file-status-pill__count">{statusCounts[state]}</span>
        <span className="file-status-pill__label">{getTaskStatusLabel(state, t)}</span>
      </span>
    ));
    const canToggle = !showPlaceholder && filteredTasks.length > 0;
    const isCollapsed = canToggle ? collapsedGroups.has(key) : false;
    const taskListId = `file-group-${encodeURIComponent(key)}-tasks`;

    return (
      <section key={key} className={`file-group${isCollapsed ? ' is-collapsed' : ''}`}>
        <header className="file-group-header">
          <div className="file-overview">
            <div className="file-title-row" title={fileName || t('common.unknownFile', undefined, 'Unknown file')}>
              <div className="file-icon">
                <span className={`file-icon-${getFileTypeCategory(effectiveFileExt)}`}>{getFileTypeIcon(effectiveFileExt)}</span>
              </div>
              <div className="file-title-info">
                <div className="file-title-text">
                  {formatFileName(fileName || undefined, 48)}
                  {fileExt && (
                    <div className={`file-type-badge${isPdfFile ? ' pdf' : isPresentationFile ? ' ppt' : ''}`}>
                      {fileExt.replace(/^\./, '').toUpperCase()}
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div
              className="file-meta-row"
              aria-label={t(
                'creations.file.taskGroupLabel',
                { fileName: fileName || '' },
                'Tasks for this upload',
              )}
            >
              <div className="file-meta-item">
                {t('creations.file.taskListTitle', { count: allTasks.length }, `Tasks (${allTasks.length})`)}
              </div>
              {lastUpdatedIso && (
                <div className="file-meta-item">
                  <span className="file-meta-label">
                    {t('task.detail.updated', undefined, 'Updated')}
                  </span>
                  <time dateTime={lastUpdatedIso}>{formatTimestamp(lastUpdatedIso)}</time>
                </div>
              )}
            </div>
            {statusPills.length > 0 && (
              <div className="file-status-row">
                {statusPills}
              </div>
            )}
          </div>
          <div className="file-actions">
            {canToggle && (
              <button
                type="button"
                className={`file-header-toggle${isCollapsed ? ' collapsed' : ''}`}
                onClick={() => toggleGroup(key)}
                aria-expanded={!isCollapsed}
                aria-controls={taskListId}
              >
                <span className="file-header-toggle-icon" aria-hidden="true">
                  {isCollapsed ? '▸' : '▾'}
                </span>
                <span className="file-header-toggle-label">
                  {isCollapsed
                    ? t('creations.file.expand', undefined, 'Expand details')
                    : t('creations.file.collapse', undefined, 'Collapse details')}
                </span>
              </button>
            )}
            {hasUploadActions && actionUploadId && (
              <>
                <button
                  className="file-action-btn primary"
                  title={t('actions.generateVideo')}
                  onClick={() => onRun(actionUploadId, group.filename, effectiveFileExt, 'video')}
                  disabled={!actionUploadId}
                >
                  {t('actions.generateVideo')}
                </button>
                {isPdf(effectiveFileExt) && (
                  <button
                    className="file-action-btn secondary"
                    title={t('actions.generatePodcast')}
                    onClick={() => onRun(actionUploadId, group.filename, effectiveFileExt, 'podcast')}
                    disabled={!actionUploadId}
                  >
                    {t('actions.generatePodcast')}
                  </button>
                )}
              </>
            )}

          </div>
        </header>
        {!showPlaceholder && !isCollapsed && filteredTasks.length > 0 && (
          <div
            id={taskListId}
            className="file-task-list"
            role="group"
            aria-label={t('creations.file.taskGroupLabel', { fileName: fileName || '' }, 'Tasks for this upload')}
          >
            <ul>{filteredTasks.map(renderTaskItem)}</ul>
          </div>
        )}
      </section>
    );
  };


  const runFileTask = useRunFileTaskMutation();
  const cancelMutation = useCancelTaskMutation();
  const processingTaskId = processingTask?.task_id ?? null;
  const { data: processingTaskData } = useTaskQuery(processingTaskId || '', processingTask ?? null);
  const processingModalTask = processingTaskData ?? processingTask;

  const onCancel = useCallback(
    async (taskId: string) => {
      try {
        console.log('Cancelling task:', taskId);
        const result = await cancelMutation.mutateAsync(taskId);
        console.log('Cancel result:', result);
        // The mutation now handles cache updates optimistically
        console.log('Queries updated');
      }
      catch (error) {
        console.error('Failed to cancel task:', error);
        alert(t('creations.toast.cancelFailed', undefined, 'Failed to cancel task'));
      }
    },
    [cancelMutation, t],
  );

  const onDelete = useCallback(
    async (taskId: string) => {
      if (!window.confirm(t('creations.confirm.delete', undefined, 'This will permanently remove the task and its state. Continue?'))) return;
      try {
        await apiDeleteTask(taskId);
      } catch (error: any) {
        const message = error?.response?.data?.error || error?.message || '';
        if (typeof message === 'string' && message.toLowerCase().includes('cannot be cancelled')) {
          await apiPurgeTask(taskId);
        } else {
          throw error;
        }
      }
      try {
        setHiddenTasks((prev) => {
          const next = new Set(prev);
          next.add(taskId);
          return next;
        });
        // Optimistically remove the task from any cached lists
        queryClient.setQueriesData({ predicate: ({ queryKey }) => Array.isArray(queryKey) && queryKey[0] === 'files' }, (old: any) => {
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
        });
        queryClient.setQueriesData({ predicate: ({ queryKey }) => Array.isArray(queryKey) && queryKey[0] === 'tasks' }, (old: any) => {
          if (!Array.isArray(old)) return old;
          return old.filter((t: any) => t?.task_id !== taskId);
        });
        queryClient.setQueriesData({ predicate: ({ queryKey }) => Array.isArray(queryKey) && queryKey[0] === 'tasksSearch' }, (old: any) => {
          if (!old || !Array.isArray(old.tasks)) return old;
          return { ...old, tasks: old.tasks.filter((t: any) => t?.task_id !== taskId) };
        });
        // Use the new query structure for invalidation
        await queryClient.invalidateQueries({ queryKey: ['tasks'] });
        await queryClient.invalidateQueries({ queryKey: ['files'] });
      } catch (error) {
        console.error('Failed to delete task from creations', error);
        alert(t('creations.toast.deleteFailed', undefined, 'Failed to delete task'));
      }
    },
    [queryClient, t],
  );

  const getTaskTypeInfo = useCallback(
    (task: Task) => {
      const { key: sanitized, fallbackLabel } = resolveTaskType(
        task,
        task.state as any,
      );
      const label = t(
        `task.list.type.${sanitized}`,
        undefined,
        fallbackLabel,
      );
      return { typeKey: sanitized, label };
    },
    [t],
  );

  const renderTaskItem = useCallback(
    (task: Task) => {
      const { typeKey, label: typeLabel } = getTaskTypeInfo(task);
      const statusClass = getTaskStatusClass(task.status);
      const icon = getTaskStatusIcon(task.status);
      const label = getTaskStatusLabel(task.status, t);
      const short = shortId(task.task_id);
      const canCancel = task.status === 'processing' || task.status === 'queued';
      const canDelete = !canCancel;
      const createdAt = formatTimestamp(task.created_at);
      const updatedAt = formatTimestamp(task.updated_at);
      const voiceLanguage =
        task.voice_language ??
        task.kwargs?.voice_language ??
        task.state?.voice_language ??
        null;
      const subtitleLanguage =
        task.subtitle_language ??
        task.kwargs?.subtitle_language ??
        task.state?.subtitle_language ??
        null;
      const transcriptLanguage =
        task.transcript_language ??
        task.kwargs?.transcript_language ??
        task.state?.podcast_transcript_language ??
        null;
      const videoResolution =
        task.kwargs?.video_resolution ??
        task.state?.video_resolution ??
        null;

      const generationParamsChips: React.ReactNode[] = [];
      const datetimeChips: React.ReactNode[] = [];

      // Line 1: Task generation parameters
      if (voiceLanguage) {
        generationParamsChips.push(
          <span key="voice" className="file-task-chip">
            {t(
              'task.list.voice',
              { language: getLanguageName(voiceLanguage) },
              `Voice: ${getLanguageName(voiceLanguage)}`,
            )}
          </span>,
        );
      }
      if (subtitleLanguage) {
        generationParamsChips.push(
          <span key="subs" className="file-task-chip">
            {t(
              'task.list.subtitles',
              { language: getLanguageName(subtitleLanguage) },
              `Subs: ${getLanguageName(subtitleLanguage)}`,
            )}
          </span>,
        );
      }
      if (transcriptLanguage) {
        generationParamsChips.push(
          <span key="transcript" className="file-task-chip">
            {t(
              'task.list.transcript',
              { language: getLanguageName(transcriptLanguage) },
              `Transcript: ${getLanguageName(transcriptLanguage)}`,
            )}
          </span>,
        );
      }
      if (videoResolution) {
        generationParamsChips.push(
          <span key="resolution" className="file-task-chip">
            {getResolutionName(videoResolution)}
          </span>,
        );
      }

      // Line 2: Task create/update datetime information
      datetimeChips.push(
        <span key="created" className="file-task-chip subtle">
          {`${t('task.detail.created', undefined, 'Created')}: ${createdAt}`}
        </span>,
      );
      if (updatedAt && updatedAt !== createdAt) {
        datetimeChips.push(
          <span key="updated" className="file-task-chip subtle">
            {`${t('task.detail.updated', undefined, 'Updated')}: ${updatedAt}`}
          </span>,
        );
      }

      return (
        <li
          key={task.task_id}
          className={`file-task ${statusClass}`}
          onMouseEnter={() => prefetchTaskDetail(queryClient, task.task_id)}
        >
          <div className="file-task-header">
            <div className="file-task-heading">
              <Link
                href={`/tasks/${task.task_id}`}
                className="file-task-link"
                title={t('task.list.openTaskTitle', { id: task.task_id }, `Open task ${task.task_id}`)}
              >
                <span className="file-task-icon" aria-hidden="true">
                  {icon}
                </span>
                <span
                  className={`file-task-id ${copiedTaskId === task.task_id ? 'copied' : ''}`}
                  onClick={(e) => handleCopyTaskId(task.task_id, e)}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  title={copiedTaskId === task.task_id ? t('common.copied', undefined, 'Copied!') : t('task.list.copyId', undefined, 'Copy task ID')}
                >
                  {copiedTaskId === task.task_id ? '✓' : task.task_id}
                </span>
              </Link>
              <span className={`file-task-type-badge type-${typeKey}`}>
                {typeLabel}
              </span>
            </div>
            {/* Only show status badge for in-progress tasks (processing or queued) */}
            {(task.status === 'processing' || task.status === 'queued') && (
              task.status === 'processing' ? (
                <button
                  type="button"
                  className={`file-task-status ${statusClass}`}
                  onClick={() => setProcessingTask(task)}
                  title={t('processing.modal.openDetails', undefined, 'View processing details')}
                >
                  {label}
                </button>
              ) : (
                <span className={`file-task-status ${statusClass}`}>
                  {label}
                </span>
              )
            )}
          </div>
          {(generationParamsChips.length > 0 || datetimeChips.length > 0) && (
            <div className="file-task-meta">
              {generationParamsChips.length > 0 && (
                <div className="file-task-meta-line file-task-meta-params">{generationParamsChips}</div>
              )}
              {datetimeChips.length > 0 && (
                <div className="file-task-meta-line file-task-meta-datetime">{datetimeChips}</div>
              )}
            </div>
          )}
          <div className="file-task-actions">
            <Link
              className="file-task-action primary"
              href={`/tasks/${task.task_id}`}
              title={t('task.list.openTaskTitle', { id: task.task_id }, `Open task ${task.task_id}`)}
              target="_blank"
              rel="noopener noreferrer"
            >
              {t('actions.open', undefined, 'Open')}
            </Link>
            {canCancel && (
              <button
                type="button"
                className="file-task-action danger"
                onClick={() => onCancel(task.task_id)}
                title={t('actions.cancel', undefined, 'Cancel')}
              >
                {t('actions.cancel', undefined, 'Cancel')}
              </button>
            )}
            {canDelete && (
              <button
                type="button"
                className="file-task-action danger"
                onClick={() => onDelete(task.task_id)}
                title={t('actions.delete', undefined, 'Delete')}
              >
                {t('actions.delete', undefined, 'Delete')}
              </button>
            )}
          </div>
        </li>
      );
    },
    [
      formatTimestamp,
      getLanguageName,
      getResolutionName,
      getTaskTypeInfo,
      onCancel,
      onDelete,
      setProcessingTask,
      t,
      copiedTaskId,
      handleCopyTaskId,
      queryClient,
    ],
  );

  const onRun = (upload_id: string, filename?: string, file_ext?: string, taskType: 'video'|'podcast' = 'video') => {
    setRunFile({ upload_id, filename, isPdf: isPdf(file_ext) });
    const defs = getGlobalRunDefaults();
    setRunDefaults(taskType === 'video' ? {
      task_type: 'video', voice_language: defs.voice_language, subtitle_language: defs.subtitle_language ?? null, video_resolution: defs.video_resolution || 'hd',
    } : {
      task_type: 'podcast', voice_language: defs.voice_language, transcript_language: defs.transcript_language ?? null, video_resolution: defs.video_resolution || 'hd',
    });
    setRunOpen(true);
  };

  const renderGroups = () => {
    if (searching) {
      if (!searchGroups.length) {
        return <div className="no-tasks">{t('creations.empty', undefined, 'No tasks found')}</div>;
      }
      // Apply virtualization for search results
      const visibleGroups = searchGroups.slice(0, visibleCount);
      return (
        <div className="file-groups">
          {visibleGroups.map((g, idx) =>
            renderFileGroup(
              {
                upload_id: g.upload_id,
                filename: g.filename,
                file_ext: g.file_ext,
                source_type: undefined,
                tasks: g.tasks,
                uploadOnly: false,
              },
              g.upload_id || g.filename || `search-${idx}`,
            ),
          )}
          {searchGroups.length > visibleCount && (
            <div className="pagination-sentinel" style={{ height: '20px' }} />
          )}
        </div>
      );
    }

    const files = ((filesQuery.data as any)?.files || []) as FileGroup[];
    if (!files.length) {
      return <div className="no-tasks">{t('creations.empty', undefined, 'No tasks found')}</div>;
    }

    // Apply virtualization for regular file list
    const visibleFiles = files.slice(0, visibleCount);
    return (
      <div className="file-groups">
        {visibleFiles.map((f, idx) => renderFileGroup(f, f.upload_id || f.filename || `upload-${idx}`))}
        {files.length > visibleCount && (
          <div className="pagination-sentinel" style={{ height: '20px' }} />
        )}
      </div>
    );
  };

  return (
    <div className="task-monitor" ref={containerRef}>
      {toast && <div className={`toast ${toast.type}`} role="status" aria-live="polite">{toast.message}</div>}
      <div className="monitor-header">
        <h2 className="ai-title">{t('creations.title', undefined, 'Creations')}</h2>
        <div className="monitor-counts" aria-live="polite">
          {t('creations.summary', { files: counts.filesCount, creations: counts.creationsCount, running: counts.runningCount }, `${counts.filesCount} files · ${counts.creationsCount} creations · ${counts.runningCount} running`)}
          {counts.total > 0 && (
            <span> · {counts.total} total</span>
          )}
        </div>
        <div className="monitor-controls">
          <form onSubmit={(e)=>{e.preventDefault(); setDebounced(search.trim());}} className="search-form">
            <input type="text" placeholder={t('search.placeholder')} value={search} onChange={(e)=>setSearch(e.target.value)} className="search-input" />
            <button type="submit" className="search-button">{t('search.submit')}</button>
          </form>
          <select value={status} onChange={(e)=>setStatus(e.target.value)} className="status-filter">
            <option value="all">{t('filters.status.all')}</option>
            <option value="queued">{t('task.status.queued')}</option>
            <option value="processing">{t('task.status.processing')}</option>
            <option value="completed">{t('task.status.completed')}</option>
            <option value="failed">{t('task.status.failed')}</option>
            <option value="cancelled">{t('task.status.cancelled')}</option>
          </select>
        </div>
      </div>
      <div className="task-list">
        {renderGroups()}
      </div>

      <div className="pagination">
        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="page-button">{t('pagination.previous')}</button>
        <span className="page-info">{t('pagination.page', { page }, `Page ${page}`)}</span>
        <button onClick={() => setPage(page + 1)} disabled={searching ? ((((searchQuery.data as any)?.tasks) || []).length < 10) : !((filesQuery.data as any)?.has_more)} className="page-button">{t('pagination.next')}</button>
      </div>

      <Suspense fallback={<div className="modal-loading">Loading...</div>}>
        <TaskCreationModal
          open={runOpen}
          isPdf={!!runFile?.isPdf}
          defaults={runDefaults}
          filename={runFile?.filename}
          submitting={runSubmitting}
          onClose={() => setRunOpen(false)}
          onSubmit={(payload) => {
            if (!runFile?.upload_id) return;
            setRunSubmitting(true);
            saveGlobalRunDefaults({ voice_language: payload.voice_language, subtitle_language: payload.subtitle_language ?? null, transcript_language: payload.transcript_language ?? null, video_resolution: payload.video_resolution || 'hd' });
            runFileTask.mutate(
              { uploadId: runFile.upload_id, payload },
              { onSuccess: (res: any) => {
                  setRunOpen(false);
                  setToast({ type: 'success', message: t('creations.toast.taskCreated', { id: res?.task_id || '' }, `Task created: ${res?.task_id || ''}`) });
                },
                onError: () => setToast({ type: 'error', message: t('creations.toast.createFailed', undefined, 'Failed to create task') }),
                onSettled: () => setRunSubmitting(false) }
            );
          }}
        />
      </Suspense>
      <Suspense fallback={<div className="modal-loading">Loading...</div>}>
        <TaskProgressModal
          open={Boolean(processingTask)}
          task={processingModalTask ?? null}
          onClose={() => setProcessingTask(null)}
          onCancel={onCancel}
        />
      </Suspense>
    </div>
  );
};

export default TaskDashboard;

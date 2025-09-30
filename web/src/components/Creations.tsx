import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { cancelRun as apiCancelRun, deleteTask as apiDeleteTask, purgeTask as apiPurgeTask, getHealth } from '../services/client';
import { getCachedDownloads, useFilesQuery, useRunFileTaskMutation, useSearchTasksQuery, useTranscriptQuery } from '../services/queries';
import TaskCard from './TaskCard';
import PreviewModal from './PreviewModal';
import RunTaskModal from './RunTaskModal';
import VideoPlayer from './VideoPlayer';
import AudioPlayer from './AudioPlayer';
import PodcastPlayer from './PodcastPlayer';
import { getGlobalRunDefaults, saveGlobalRunDefaults } from '../utils/defaults';
import type { Task } from '../types';
import { useI18n } from '@/i18n/hooks';
import { getLanguageDisplayName } from '../utils/language';

interface CreationsProps { apiBaseUrl: string }

const isPdf = (ext?: string) => (ext || '').toLowerCase() === '.pdf';
const shortId = (id?: string) => {
  if (!id) return '';
  if (id.length <= 12) return id;
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
};

const LANGUAGE_KEYS: Record<string, string> = {
  english: 'language.english',
  simplified_chinese: 'language.simplified',
  traditional_chinese: 'language.traditional',
  japanese: 'language.japanese',
  korean: 'language.korean',
  thai: 'language.thai',
};

const RESOLUTION_KEYS: Record<string, string> = {
  sd: 'runTask.resolution.sd',
  hd: 'runTask.resolution.hd',
  fullhd: 'runTask.resolution.fullhd',
};

const Creations: React.FC<CreationsProps> = ({ apiBaseUrl }) => {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [status, setStatus] = useState('all');
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const { t } = useI18n();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Task | null>(null);
  const [mode, setMode] = useState<'video'|'audio'>('video');
  const [toast, setToast] = useState<{ type: 'success'|'error'; message: string }|null>(null);
  const [runOpen, setRunOpen] = useState(false);
  const [runFile, setRunFile] = useState<{ file_id: string; filename?: string; isPdf: boolean } | null>(null);
  const [runDefaults, setRunDefaults] = useState<any>({});
  const [runSubmitting, setRunSubmitting] = useState(false);
  const queryClient = useQueryClient();
  const [hiddenTasks, setHiddenTasks] = useState<Set<string>>(new Set());

  useEffect(() => { const t = setTimeout(() => setDebounced(search.trim()), 350); return () => clearTimeout(t); }, [search]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

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
    const key = LANGUAGE_KEYS[normalized];
    if (key) return t(key, undefined, getLanguageDisplayName(normalized));
    return getLanguageDisplayName(code) || t('common.unknown', undefined, 'Unknown');
  }, [t]);

  const getResolutionName = useCallback((value: string) => {
    const normalized = (value || '').toLowerCase();
    const key = RESOLUTION_KEYS[normalized];
    if (key) return t(key, undefined, value);
    return t('common.unknown', undefined, 'Unknown');
  }, [t]);

  const filesQuery = useFilesQuery(
    { page, limit: 10, includeTasks: true, q: debounced || undefined },
    { refetchInterval: (q: any) => {
        const files = (q?.state?.data as any)?.files || [];
        const hasActive = files.some((f: any) => (f.tasks || []).some((t: Task) => t.status === 'processing' || t.status === 'queued'));
        return hasActive ? 15000 : false;
      }, staleTime: 10000 }
  );
  const searchQuery = useSearchTasksQuery(debounced);
  const searching = debounced.length > 0;

  // Health indicator (Redis/DB)
  const healthQuery = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 30000, staleTime: 20000 });
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

  // Selected preview transcript (podcast listen)
  const selectedIsPodcast = useMemo(() => {
    if (!selected) return false;
    const tt = String(selected.task_type || (selected.state as any)?.task_type || '').toLowerCase();
    return tt === 'podcast';
  }, [selected]);
  const transcriptQ = useTranscriptQuery(selected ? selected.task_id : null, !!selected && selectedIsPodcast && mode === 'audio');
  const selectedTranscript = (transcriptQ.data as any) || '';

  // Build groups when searching (file_id -> tasks)
  const searchGroups = useMemo(() => {
    if (!searching) return [] as Array<{ file_id?: string; filename?: string; file_ext?: string; tasks: Task[] }>;
    const items: Task[] = (((searchQuery.data as any)?.tasks) || []) as Task[];
    const map = new Map<string, { file_id?: string; filename?: string; file_ext?: string; tasks: Task[]; newest: number }>();
    for (const t of items) {
      const fid = t.file_id || (t as any)?.kwargs?.file_id;
      const key = fid || `unknown:${(t as any)?.kwargs?.filename || 'Unknown'}`;
      const updated = Date.parse(t.updated_at || t.created_at || '') || 0;
      if (!map.has(key)) map.set(key, { file_id: fid, filename: (t as any)?.kwargs?.filename || t.state?.filename, file_ext: (t as any)?.kwargs?.file_ext, tasks: [t], newest: updated });
      else { const g = map.get(key)!; g.tasks.push(t); g.newest = Math.max(g.newest, updated); g.filename ||= (t as any)?.kwargs?.filename || t.state?.filename; g.file_ext ||= (t as any)?.kwargs?.file_ext; }
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
    const files = ((filesQuery.data as any)?.files || []) as Array<{ tasks?: Task[] }>;
    let filesCount = 0, creationsCount = 0, runningCount = 0;
    for (const f of files) {
      const tasks = filterHidden((f.tasks || []) as Task[]);
      const vis = status === 'all' ? tasks : tasks.filter((t) => t.status === status);
      if (vis.length > 0) filesCount++;
      creationsCount += vis.length;
      runningCount += tasks.filter((t) => t.status === 'processing').length;
    }
    return { filesCount, creationsCount, runningCount };
  }, [searching, searchGroups, filesQuery.data, status, hiddenTasks]);

  const toggleFile = (k: string) => setExpandedFiles((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const toggleTask = (id: string) => setExpandedTasks((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const runFileTask = useRunFileTaskMutation();

  const onCancel = async (taskId: string) => {
    try { await apiCancelRun(taskId); }
    catch { alert(t('creations.toast.cancelFailed', undefined, 'Failed to cancel task')); }
  };
  const onDelete = async (taskId: string) => {
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
      if (selected?.task_id === taskId) {
        setSelected(null);
      }
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
      await queryClient.invalidateQueries({ queryKey: ['tasks'] });
      await queryClient.invalidateQueries({ queryKey: ['files'] });
    } catch (error) {
      console.error('Failed to delete task from creations', error);
      alert(t('creations.toast.deleteFailed', undefined, 'Failed to delete task'));
    }
  };

  const deriveOutputs = (task: Task) => {
    const tt = String(task.task_type || (task.state as any)?.task_type || '').toLowerCase();
    if (tt === 'video') return { video: true, podcast: false };
    if (tt === 'podcast') return { video: false, podcast: true };
    if (tt === 'both') return { video: true, podcast: true };
    const dl = getCachedDownloads(queryClient, task.task_id);
    const items = dl?.items || [];
    return { video: items.some((i: any) => i?.type === 'video'), podcast: items.some((i: any) => i?.type === 'podcast') };
  };

  const openPreview = (task: Task, m?: 'video'|'audio') => {
    if (task.status !== 'completed') { alert(t('alerts.previewUnavailable')); return; }
    setSelected(task);
    if (m) setMode(m); else {
      const outs = deriveOutputs(task); setMode(outs.video ? 'video' : 'audio');
    }
  };
  const closePreview = () => setSelected(null);

  const onRun = (file_id: string, filename?: string, file_ext?: string, taskType: 'video'|'podcast' = 'video') => {
    setRunFile({ file_id, filename, isPdf: isPdf(file_ext) });
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
      if (!searchGroups.length) return <div className="no-tasks">{t('creations.empty', undefined, 'No tasks found')}</div>;
      return (
        <div className="file-groups">
          {searchGroups.map((g, idx) => {
            const key = g.file_id || g.filename || `search-${idx}`;
            const visible = g.tasks.filter((t) => !hiddenTasks.has(t.task_id));
            const vis = status === 'all' ? visible : visible.filter((t) => t.status === status);
            if (!vis.length) return null;
            return (
              <section key={key} className={`file-group ${expandedFiles.has(key) ? 'open' : ''}`}>
                <header className="file-group-header">
                  <button
                    type="button"
                    className="file-toggle"
                    aria-expanded={expandedFiles.has(key)}
                    onClick={() => toggleFile(key)}
                  >
                    <div className="file-title" title={g.filename || t('common.unknownFile', undefined, 'Unknown file')}>
                      <span className="file-title-text">{formatFileName(g.filename, 48)}</span>
                    </div>
                    <div className="file-meta">
                      <span className="file-id-chip" title={g.file_id || ''}>{g.file_id ? t('creations.file.idChip', { id: shortId(g.file_id) }, `ID ${shortId(g.file_id)}`) : t('common.untrackedFile', undefined, 'Untracked file')}</span>
                      <span className="task-count">{vis.length === 1
                        ? t('creations.file.count.one', { count: vis.length }, '1 creation')
                        : t('creations.file.count.other', { count: vis.length }, `${vis.length} creations`)}
                      </span>
                    </div>
                    <span className="chev" aria-hidden>▾</span>
                  </button>
                  {!!g.file_id && (
                    <div className="file-group-actions" onClick={(e) => e.stopPropagation()}>
                      <button className="mini-btn" title={t('actions.generateVideo')} onClick={() => onRun(g.file_id!, g.filename, g.file_ext, 'video')}>
                        <span aria-hidden>🎬</span>
                        <span>{t('actions.generateVideo')}</span>
                      </button>
                      {isPdf(g.file_ext) && (
                        <button className="mini-btn" title={t('actions.generatePodcast')} onClick={() => onRun(g.file_id!, g.filename, g.file_ext, 'podcast')}>
                          <span aria-hidden>🎧</span>
                          <span>{t('actions.generatePodcast')}</span>
                        </button>
                      )}
                    </div>
                  )}
                </header>
                {expandedFiles.has(key) && (
                  <div className="file-task-list">
                    {vis.map((task) => (
                      <TaskCard
                        key={task.task_id}
                        task={task}
                        apiBaseUrl={apiBaseUrl}
                        isRemoving={false}
                        isExpanded={expandedTasks.has(task.task_id)}
                        onToggleDownloads={(t) => toggleTask(t.task_id)}
                        onPreview={openPreview}
                        onCancel={onCancel}
                        onDelete={onDelete}
                        deriveTaskOutputs={deriveOutputs}
                        getLanguageDisplayName={getLanguageName}
                        getVideoResolutionDisplayName={getResolutionName}
                      />
                    ))}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      );
    }
    const files = ((filesQuery.data as any)?.files || []) as Array<{ file_id?: string; filename?: string; file_ext?: string; tasks?: Task[] }>;
    if (!files.length) return <div className="no-tasks">{t('creations.empty', undefined, 'No tasks found')}</div>;
    return (
      <div className="file-groups">
        {files.map((f, idx) => {
          const key = f.file_id || f.filename || `file-${idx}`;
          const tasks = ((f.tasks || []) as Task[]).filter((t) => !hiddenTasks.has(t.task_id));
          const vis = status === 'all' ? tasks : tasks.filter((t) => t.status === status);
          if (!vis.length) return null;
          return (
              <section key={key} className={`file-group ${expandedFiles.has(key) ? 'open' : ''}`}>
                <header className="file-group-header">
                <button
                  type="button"
                  className="file-toggle"
                  aria-expanded={expandedFiles.has(key)}
                  onClick={() => toggleFile(key)}
                >
                  <div className="file-title" title={f.filename || t('common.unknownFile', undefined, 'Unknown file')}>
                    <span className="file-title-text">{formatFileName(f.filename, 48)}</span>
                  </div>
                  <div className="file-meta">
                    <span className="file-id-chip" title={f.file_id || ''}>{f.file_id ? t('creations.file.idChip', { id: shortId(f.file_id) }, `ID ${shortId(f.file_id)}`) : t('common.untrackedFile', undefined, 'Untracked file')}</span>
                    <span className="task-count">{vis.length === 1
                      ? t('creations.file.count.one', { count: vis.length }, '1 creation')
                      : t('creations.file.count.other', { count: vis.length }, `${vis.length} creations`)}
                    </span>
                  </div>
                  <span className="chev" aria-hidden>▾</span>
                </button>
                {!!f.file_id && (
                  <div className="file-group-actions" onClick={(e) => e.stopPropagation()}>
                    <button className="mini-btn" title={t('actions.generateVideo')} onClick={() => onRun(f.file_id!, f.filename, f.file_ext, 'video')}>
                      <span aria-hidden>🎬</span>
                      <span>{t('actions.generateVideo')}</span>
                    </button>
                    {isPdf(f.file_ext) && (
                      <button className="mini-btn" title={t('actions.generatePodcast')} onClick={() => onRun(f.file_id!, f.filename, f.file_ext, 'podcast')}>
                        <span aria-hidden>🎧</span>
                        <span>{t('actions.generatePodcast')}</span>
                      </button>
                    )}
                  </div>
                )}
              </header>
              {expandedFiles.has(key) && (
                <div className="file-task-list">
                  {vis.map((task) => (
                    <TaskCard
                      key={task.task_id}
                      task={task}
                      apiBaseUrl={apiBaseUrl}
                      isRemoving={false}
                      isExpanded={expandedTasks.has(task.task_id)}
                      onToggleDownloads={(t) => toggleTask(t.task_id)}
                      onPreview={openPreview}
                      onCancel={onCancel}
                      onDelete={onDelete}
                      deriveTaskOutputs={deriveOutputs}
                      getLanguageDisplayName={getLanguageName}
                      getVideoResolutionDisplayName={getResolutionName}
                    />
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </div>
    );
  };

  return (
    <div className="task-monitor">
      {toast && <div className={`toast ${toast.type}`} role="status" aria-live="polite">{toast.message}</div>}
      <div className="monitor-header">
        <h2 className="ai-title">{t('creations.title', undefined, 'Creations')}</h2>
        <div className="monitor-counts" aria-live="polite">{t('creations.summary', { files: counts.filesCount, creations: counts.creationsCount, running: counts.runningCount }, `${counts.filesCount} files · ${counts.creationsCount} creations · ${counts.runningCount} running`)}</div>
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

      {/* Selected preview helpers */}
      {(() => {
        /* compute podcast flag at top-level to support hooks */
        return null;
      })()}
      <PreviewModal
        open={!!selected}
        mode={mode}
        onClose={closePreview}
        header={selected ? (
          <div className="modal-header-bar" data-mode={mode}>
            <div className="header-left" aria-label={t('modal.previewTitle')}><span className="header-icon" aria-hidden>{mode === 'video' ? '🎬' : '🎧'}</span><span>{t('modal.previewTitle')}</span></div>
            <div className="header-right">
              <button type="button" className="modal-close-btn" aria-label={t('actions.close')} title={t('actions.close')} onClick={closePreview}>
                <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
              </button>
            </div>
          </div>
        ) : null}
      >
        {selected && (() => {
          const voiceLanguage = selected.kwargs?.voice_language || selected.state?.voice_language || 'english';
          const subtitleLanguage = selected.kwargs?.subtitle_language || selected.state?.subtitle_language || voiceLanguage;
          const vtt = `${apiBaseUrl}/api/tasks/${selected.task_id}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
          const videoUrl = `${apiBaseUrl}/api/tasks/${selected.task_id}/video`;
          const tt = (selected.task_type || (selected.state as any)?.task_type || '').toLowerCase();
          const isPod = tt === 'podcast';
          /* transcript loaded via top-level hook below */
          if (mode === 'video') {
            return (
              <div className="modal-preview-stack">
                <div className="modal-video-wrapper">
                  <VideoPlayer src={videoUrl} trackUrl={vtt} trackLang={subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : subtitleLanguage === 'japanese' ? 'ja' : subtitleLanguage === 'korean' ? 'ko' : subtitleLanguage === 'thai' ? 'th' : 'en'} trackLabel={getLanguageName(subtitleLanguage)} className="video-player" onReady={() => {}} onError={() => {}} />
                </div>
              </div>
            );
          }
          const audioUrl = `${apiBaseUrl}/api/tasks/${selected.task_id}/${isPod ? 'podcast' : 'audio'}`;
          return (
            <div className="modal-preview-stack">
              {isPod ? (<PodcastPlayer src={audioUrl} transcriptMarkdown={(selectedTranscript || '') as any} />) : (<AudioPlayer src={audioUrl} vttUrl={vtt} />)}
            </div>
          );
        })()}
      </PreviewModal>

      <RunTaskModal
        open={runOpen}
        isPdf={!!runFile?.isPdf}
        defaults={runDefaults}
        filename={runFile?.filename}
        submitting={runSubmitting}
        onClose={() => setRunOpen(false)}
        onSubmit={(payload) => {
          if (!runFile?.file_id) return;
          setRunSubmitting(true);
          saveGlobalRunDefaults({ voice_language: payload.voice_language, subtitle_language: payload.subtitle_language ?? null, transcript_language: payload.transcript_language ?? null, video_resolution: payload.video_resolution || 'hd' });
          runFileTask.mutate(
            { fileId: runFile.file_id, payload },
            { onSuccess: (res: any) => {
                setRunOpen(false);
                setToast({ type: 'success', message: t('creations.toast.taskCreated', { id: res?.task_id || '' }, `Task created: ${res?.task_id || ''}`) });
              },
              onError: () => setToast({ type: 'error', message: t('creations.toast.createFailed', undefined, 'Failed to create task') }),
              onSettled: () => setRunSubmitting(false) }
          );
        }}
      />
    </div>
  );
};

export default Creations;

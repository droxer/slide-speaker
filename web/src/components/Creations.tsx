import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { cancelRun as apiCancelRun, purgeTask as apiPurgeTask } from '../services/client';
import { getCachedDownloads, useFilesQuery, useRunFileTaskMutation, useSearchTasksQuery, useTranscriptQuery } from '../services/queries';
import '../styles/task-monitor.scss';
import TaskCard from './TaskCard';
import PreviewModal from './PreviewModal';
import RunTaskModal from './RunTaskModal';
import VideoPlayer from './VideoPlayer';
import AudioPlayer from './AudioPlayer';
import PodcastPlayer from './PodcastPlayer';
import { getGlobalRunDefaults, saveGlobalRunDefaults } from '../utils/defaults';
import type { Task } from '../types';

interface CreationsProps { apiBaseUrl: string }

const isPdf = (ext?: string) => (ext || '').toLowerCase() === '.pdf';
const langName = (code: string) => ({
  english: 'English',
  simplified_chinese: '简体中文',
  traditional_chinese: '繁體中文',
  japanese: '日本語',
  korean: '한국어',
  thai: 'ไทย',
} as any)[(code || '').toLowerCase()] || code || 'Unknown';
const resName = (r: string) => (r === 'sd' ? 'SD (640×480)' : r === 'hd' ? 'HD (1280×720)' : r === 'fullhd' ? 'Full HD (1920×1080)' : r || 'Unknown');
const shortBaseName = (name?: string, max = 42): string => {
  if (!name) return 'Unknown file';
  const base = name.replace(/\.(pdf|pptx?|PPTX?|PDF)$/,'');
  if (base.length <= max) return base;
  const head = Math.max(12, Math.floor((max - 1) / 2));
  const tail = max - head - 1;
  return base.slice(0, head) + '…' + base.slice(-tail);
};

const Creations: React.FC<CreationsProps> = ({ apiBaseUrl }) => {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [status, setStatus] = useState('all');
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Task | null>(null);
  const [mode, setMode] = useState<'video'|'audio'>('video');
  const [toast, setToast] = useState<{ type: 'success'|'error'; message: string }|null>(null);
  const [runOpen, setRunOpen] = useState(false);
  const [runFile, setRunFile] = useState<{ file_id: string; filename?: string; isPdf: boolean } | null>(null);
  const [runDefaults, setRunDefaults] = useState<any>({});
  const [runSubmitting, setRunSubmitting] = useState(false);
  const queryClient = useQueryClient();
  const videoRef = useRef<HTMLVideoElement|null>(null);

  useEffect(() => { const t = setTimeout(() => setDebounced(search.trim()), 350); return () => clearTimeout(t); }, [search]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

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
    if (searching) {
      const filesCount = searchGroups.filter((g) => (status === 'all' ? g.tasks : g.tasks.filter((t) => t.status === status)).length > 0).length;
      const creationsCount = searchGroups.reduce((n, g) => n + (status === 'all' ? g.tasks.length : g.tasks.filter((t) => t.status === status).length), 0);
      const runningCount = searchGroups.reduce((n, g) => n + g.tasks.filter((t) => t.status === 'processing').length, 0);
      return { filesCount, creationsCount, runningCount };
    }
    const files = ((filesQuery.data as any)?.files || []) as Array<{ tasks?: Task[] }>;
    let filesCount = 0, creationsCount = 0, runningCount = 0;
    for (const f of files) {
      const tasks = (f.tasks || []) as Task[];
      const vis = status === 'all' ? tasks : tasks.filter((t) => t.status === status);
      if (vis.length > 0) filesCount++;
      creationsCount += vis.length;
      runningCount += tasks.filter((t) => t.status === 'processing').length;
    }
    return { filesCount, creationsCount, runningCount };
  }, [searching, searchGroups, filesQuery.data, status]);

  const toggleFile = (k: string) => setExpandedFiles((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const toggleTask = (id: string) => setExpandedTasks((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const runFileTask = useRunFileTaskMutation();

  const onCancel = async (taskId: string) => { try { await apiCancelRun(taskId); } catch { alert('Failed to cancel task'); } };
  const onDelete = async (taskId: string) => {
    if (!window.confirm('This will permanently remove the task and its state. Continue?')) return;
    try { await apiPurgeTask(taskId); } catch { alert('Failed to delete task'); }
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
    if (task.status !== 'completed') { alert('Preview is only available for completed tasks.'); return; }
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
      if (!searchGroups.length) return <div className="no-tasks">No tasks found</div>;
      return (
        <div className="file-groups">
          {searchGroups.map((g, idx) => {
            const key = g.file_id || g.filename || `search-${idx}`;
            const vis = (status === 'all' ? g.tasks : g.tasks.filter((t) => t.status === status));
            if (!vis.length) return null;
            return (
              <section key={key} className="file-group">
                <header className="file-group-header" role="button" onClick={() => toggleFile(key)}>
                  <div className="file-title" title={g.filename || 'Unknown file'}>
                    <span className="file-title-text">{shortBaseName(g.filename)}</span>
                    {g.filename && /\.(pdf|pptx?|PPTX?|PDF)$/.test(g.filename) && (
                      <span className="file-ext-chip">{g.filename.slice(g.filename.lastIndexOf('.')).toUpperCase()}</span>
                    )}
                    {g.file_id && (<span className="file-id-chip" title={g.file_id}>ID: <span className="id-mono">{g.file_id}</span></span>)}
                  </div>
                  <div className="task-count">{vis.length} {vis.length === 1 ? 'task' : 'tasks'}</div>
                  <div className="chev" aria-hidden>{expandedFiles.has(key) ? '▴' : '▾'}</div>
                  <div className="file-group-actions" onClick={(e) => e.stopPropagation()}>
                    {!!g.file_id && (
                      <>
                        <button className="mini-btn" title="Create Video" onClick={() => onRun(g.file_id!, g.filename, g.file_ext, 'video')}>Create Video</button>
                        {isPdf(g.file_ext) && <button className="mini-btn" title="Create Podcast" onClick={() => onRun(g.file_id!, g.filename, g.file_ext, 'podcast')}>Create Podcast</button>}
                      </>
                    )}
                  </div>
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
                        getLanguageDisplayName={langName}
                        getVideoResolutionDisplayName={resName}
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
    if (!files.length) return <div className="no-tasks">No tasks found</div>;
    return (
      <div className="file-groups">
        {files.map((f, idx) => {
          const key = f.file_id || f.filename || `file-${idx}`;
          const tasks = (f.tasks || []) as Task[];
          const vis = (status === 'all' ? tasks : tasks.filter((t) => t.status === status));
          if (!vis.length) return null;
          return (
            <section key={key} className="file-group">
              <header className="file-group-header" role="button" onClick={() => toggleFile(key)}>
                <div className="file-title" title={f.filename || 'Unknown file'}>
                  <span className="file-title-text">{shortBaseName(f.filename)}</span>
                  {f.filename && /\.(pdf|pptx?|PPTX?|PDF)$/.test(f.filename) && (
                    <span className="file-ext-chip">{f.filename.slice(f.filename.lastIndexOf('.')).toUpperCase()}</span>
                  )}
                  {f.file_id && (<span className="file-id-chip" title={f.file_id}>ID: <span className="id-mono">{f.file_id}</span></span>)}
                </div>
                <div className="task-count">{vis.length} {vis.length === 1 ? 'task' : 'tasks'}</div>
                <div className="chev" aria-hidden>{expandedFiles.has(key) ? '▴' : '▾'}</div>
                <div className="file-group-actions" onClick={(e) => e.stopPropagation()}>
                  {!!f.file_id && (
                    <>
                      <button className="mini-btn" title="Create Video" onClick={() => onRun(f.file_id!, f.filename, f.file_ext, 'video')}>Create Video</button>
                      {isPdf(f.file_ext) && <button className="mini-btn" title="Create Podcast" onClick={() => onRun(f.file_id!, f.filename, f.file_ext, 'podcast')}>Create Podcast</button>}
                    </>
                  )}
                </div>
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
                      getLanguageDisplayName={langName}
                      getVideoResolutionDisplayName={resName}
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
        <h2 className="ai-title">Creations</h2>
        <div className="monitor-counts" aria-live="polite">{counts.filesCount} files · {counts.creationsCount} creations · {counts.runningCount} running</div>
        <div className="monitor-controls">
          <form onSubmit={(e)=>{e.preventDefault(); setDebounced(search.trim());}} className="search-form">
            <input type="text" placeholder="Search tasks..." value={search} onChange={(e)=>setSearch(e.target.value)} className="search-input" />
            <button type="submit" className="search-button">Search</button>
          </form>
          <select value={status} onChange={(e)=>setStatus(e.target.value)} className="status-filter">
            <option value="all">All Status</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      <div className="task-list">
        {renderGroups()}
      </div>

      <div className="pagination">
        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="page-button">Previous</button>
        <span className="page-info">Page {page}</span>
        <button onClick={() => setPage(page + 1)} disabled={searching ? ((((searchQuery.data as any)?.tasks) || []).length < 10) : !((filesQuery.data as any)?.has_more)} className="page-button">Next</button>
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
            <div className="header-left" aria-label="Media Preview"><span className="header-icon" aria-hidden>{mode === 'video' ? '🎬' : '🎧'}</span><span>Media Preview</span></div>
            <div className="header-right">
              <button type="button" className="modal-close-btn" aria-label="Close" title="Close" onClick={closePreview}>
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
                  <VideoPlayer src={videoUrl} trackUrl={vtt} trackLang={subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : subtitleLanguage === 'japanese' ? 'ja' : subtitleLanguage === 'korean' ? 'ko' : subtitleLanguage === 'thai' ? 'th' : 'en'} trackLabel={langName(subtitleLanguage)} className="video-player" onReady={() => {}} onError={() => {}} />
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
            { onSuccess: (res: any) => { setRunOpen(false); setToast({ type: 'success', message: `Task created: ${res?.task_id || ''}` }); }, onError: () => setToast({ type: 'error', message: 'Failed to create task' }), onSettled: () => setRunSubmitting(false) }
          );
        }}
      />
    </div>
  );
};

export default Creations;

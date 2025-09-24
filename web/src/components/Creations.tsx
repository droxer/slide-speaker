import React, { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { headTaskVideo as apiHeadTaskVideo, cancelRun as apiCancelRun, purgeTask as apiPurgeTask } from '../services/client';
import { useVttQuery, getCachedDownloads, useFilesQuery, useRunFileTaskMutation } from '../services/queries';
import '../styles/task-monitor.scss';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import PodcastPlayer from './PodcastPlayer';
import TaskCard from './TaskCard';
import PreviewModal from './PreviewModal';
import RunTaskModal from './RunTaskModal';
import { getGlobalRunDefaults, saveGlobalRunDefaults } from '../utils/defaults';

// Types for task monitoring
import type { Task } from '../types';


interface CreationsProps {
  apiBaseUrl: string; // kept for compatibility; media uses relative paths
}

const Creations: React.FC<CreationsProps> = ({ apiBaseUrl }) => {
  const EXPANDED_STORAGE_KEY = 'slidespeaker_taskmonitor_expanded_v1';
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queueUnavailable, setQueueUnavailable] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const FILES_EXPANDED_KEY = 'slidespeaker_filegroups_expanded_v1';
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [tasksPerPage] = useState(10);
  const [selectedTaskForPreview, setSelectedTaskForPreview] = useState<Task | null>(null);
  // Subtitle fetch handled by <track> element in preview
  const [videoError, setVideoError] = useState<string | null>(null);
  const [modalVideoLoading, setModalVideoLoading] = useState<boolean>(false);
  // Removed unused audio loading state for modal
  // Removed unused modal audio src state
  const modalVideoRef = React.useRef<HTMLVideoElement | null>(null);
  const modalAudioRef = React.useRef<HTMLAudioElement | null>(null);
  const audioTranscriptRef = React.useRef<HTMLDivElement | null>(null);
  // Removed unused audioAltTriedRef
  // Removed unused modal audio playback state
  // No subtitle object URL caching
  const [removingTaskIds, setRemovingTaskIds] = useState<Set<string>>(new Set());
  const [expandedDownloads, setExpandedDownloads] = useState<Set<string>>(new Set());
  const [audioPreviewTaskId, setAudioPreviewTaskId] = useState<string | null>(null);
  // Availability is derived from downloads cache (no local maps)
  const [previewModeByTask, setPreviewModeByTask] = useState<Record<string, 'video' | 'audio'>>({}); // eslint-disable-line @typescript-eslint/no-unused-vars
  const [transcriptMdByTask, setTranscriptMdByTask] = useState<Record<string, string>>({});
  const [hasVideoAssetByTask, setHasVideoAssetByTask] = useState<Record<string, boolean>>({}); // eslint-disable-line @typescript-eslint/no-unused-vars
  // Networking controls to avoid duplicate requests
  const tasksControllerRef = React.useRef<AbortController | null>(null);
  const queryClient = useQueryClient();
  // removed didInitRef; React Query manages initial fetch
  type Cue = { start: number; end: number; text: string };
  const [audioCues, setAudioCues] = useState<Cue[]>([]);
  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const [activeAudioCueIdx, setActiveAudioCueIdx] = useState<number | null>(null);
  const [modalPreviewMode, setModalPreviewMode] = React.useState<'video' | 'audio'>('video');
  // When user explicitly chooses a mode (Watch/Listen), pin it to avoid being
  // overridden by defaulting effects tied to task_type.
  const modalModePinnedRef = React.useRef<boolean>(false);
  // Modal audio preview (placed close to video preview)
  // No modal audio preview; use task-card Listen for audio with transcript
  const prevStatusesRef = React.useRef<Record<string, string>>({});

  // Rerun modal state
  const [runOpen, setRunOpen] = useState(false);
  const [runFile, setRunFile] = useState<{ file_id: string; filename?: string; isPdf: boolean } | null>(null);
  const [runDefaults, setRunDefaults] = useState<any>({});
  const [runSubmitting, setRunSubmitting] = useState(false);
  // counts computed after filesQuery is declared below

  // Prefetch downloads/transcript/VTT via shared helper
  const prefetchTaskDownloads = async (taskId: string) => {
    try {
      const t = tasks.find((x) => x.task_id === taskId);
      const tt = (t?.task_type || (t?.state as any)?.task_type || '').toLowerCase();
      const isPodcast = ["podcast","both"].includes(tt);
      const lang = (t?.state?.subtitle_language || t?.kwargs?.subtitle_language || t?.kwargs?.voice_language || 'english');
      await (await import('../services/queries')).prefetchTaskPreview(queryClient, taskId, { language: lang, podcast: isPodcast });
      if (isPodcast) {
        const txt = (queryClient.getQueryData(['transcript', taskId]) as any) || '';
        if (typeof txt === 'string') setTranscriptMdByTask((m) => ({ ...m, [taskId]: txt }));
      } else {
        setTranscriptMdByTask((m) => { const n={...m}; delete n[taskId]; return n; });
      }
    } catch {}
  };

  // VTT via React Query for selected task (non-podcast)
  const selectedId = selectedTaskForPreview?.task_id || null;
  const selectedType = (selectedTaskForPreview?.task_type || (selectedTaskForPreview?.state as any)?.task_type || '').toLowerCase();
  const selectedLang = (selectedTaskForPreview?.state?.subtitle_language || (selectedTaskForPreview as any)?.kwargs?.subtitle_language || (selectedTaskForPreview as any)?.kwargs?.voice_language || 'english');
  const vttQuery = useVttQuery(selectedId, selectedLang, Boolean(selectedId) && selectedType !== 'podcast');
  useEffect(() => {
    if (!vttQuery.data || selectedType === 'podcast') { setAudioCues([]); return; }
    const text = String(vttQuery.data);
    const lines = text.split(/\r?\n/);
    const cues: Cue[] = [];
    let i = 0;
    const timeRe = /(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})\.(\d{3})/;
    while (i < lines.length) {
      const line = lines[i++].trim();
      if (!line || line.toUpperCase() === 'WEBVTT' || /^\d+$/.test(line)) continue;
      const m = line.match(timeRe);
      if (m) {
        const start = (Number(m[1])*3600 + Number(m[2])*60 + Number(m[3]) + Number(m[4])/1000);
        const end = (Number(m[5])*3600 + Number(m[6])*60 + Number(m[7]) + Number(m[8])/1000);
        let textLines: string[] = [];
        while (i < lines.length && lines[i].trim() && !timeRe.test(lines[i])) { textLines.push(lines[i].trim()); i++; }
        cues.push({ start, end, text: textLines.join(' ') });
      }
    }
    setAudioCues(cues);
  }, [vttQuery.data, selectedType]);

  // Derive task outputs (video/podcast) from state, kwargs, availability, or step name
  const deriveTaskOutputs = (task: Task): { video: boolean; podcast: boolean } => {
    // Prefer top-level task_type from API/DB
    const topType = (task.task_type || '').toLowerCase();
    if (topType === 'video') return { video: true, podcast: false };
    if (topType === 'podcast') return { video: false, podcast: true };
    if (topType === 'both') return { video: true, podcast: true };
    // Fallback to state.task_type when present
    const taskType = ((task.state as any)?.task_type as string | undefined) || undefined;
    if (taskType === 'video') return { video: true, podcast: false };
    if (taskType === 'podcast') return { video: false, podcast: true };
    if (taskType === 'both') return { video: true, podcast: true };
    // Fall back to discovered availability or step heuristics only
    const dl = getCachedDownloads(queryClient, task.task_id);
    const items = dl?.items;
    let video: boolean | undefined = Array.isArray(items) ? items.some((it: any) => it?.type === 'video') : undefined;
    let podcast: boolean | undefined = Array.isArray(items) ? items.some((it: any) => it?.type === 'podcast') : undefined;
    const step = (task.state?.current_step || '').toLowerCase();
    if (video === undefined && /compose_video|generate_pdf_video|compose final video|composing final video/.test(step)) video = true;
    if (podcast === undefined && /podcast/.test(step)) podcast = true;
    return { video: !!video, podcast: !!podcast };
  };

  const toggleDownloads = (taskId: string) => {
    setExpandedDownloads((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
    // Optimistically set inline preview mode based on task config before downloads load
    try {
      const t = tasks.find((x) => x.task_id === taskId);
      const outs = t ? deriveTaskOutputs(t) : { video: false, podcast: false };
      setPreviewModeByTask((m) => {
        const desired: 'video'|'audio' = outs.video ? 'video' : 'audio';
        if (m[taskId] === desired) return m;
        return { ...m, [taskId]: desired };
      });
      if (t && t.status === 'completed') {
        if (outs.podcast && !outs.video) {
          setAudioPreviewTaskId(taskId);
        } else if (outs.video) {
          setAudioPreviewTaskId(null);
        }
      }
    } catch {}
    // When opening, rely on TaskCard's React Query hook to fetch downloads.
  };

  

  // Sync active cue with audio time (RAF-driven for smoothness)
  useEffect(() => {
    const audio = modalAudioRef.current;
    if (!audio || audioCues.length === 0) return;
    const EPS = 0.03;
    const findIdx = (t: number): number | null => {
      let lo = 0, hi = audioCues.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const c = audioCues[mid];
        if (t < c.start - EPS) hi = mid - 1;
        else if (t > c.end + EPS) lo = mid + 1;
        else return mid;
      }
      return null;
    };

    let rafId: number | null = null;
    const tick = () => {
      const t = audio.currentTime;
      const idx = findIdx(t);
      setActiveAudioCueIdx((prev) => (prev !== idx ? idx : prev));
      rafId = requestAnimationFrame(tick);
    };
    const start = () => { if (rafId == null) rafId = requestAnimationFrame(tick); };
    const stop = () => { if (rafId != null) { cancelAnimationFrame(rafId); rafId = null; } };
    const onPlay = () => start();
    const onPause = () => stop();
    const onEnded = () => stop();
    const onSeeked = () => { const idx = findIdx(audio.currentTime); setActiveAudioCueIdx(idx); };

    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('seeked', onSeeked);
    if (!audio.paused) start(); else onSeeked();
    return () => {
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('seeked', onSeeked);
      stop();
    };
  }, [audioPreviewTaskId, audioCues]);

  // Auto-scroll transcript to active cue in modal
  useEffect(() => {
    if (activeAudioCueIdx === null) return;
    const container = audioTranscriptRef.current;
    if (!container) return;
    const el = container.querySelector(`#audio-cue-${activeAudioCueIdx}`) as HTMLElement | null;
    if (!el) return;
    try {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    } catch {
      const cRect = container.getBoundingClientRect();
      const eRect = el.getBoundingClientRect();
      container.scrollTop += (eRect.top - cRect.top - cRect.height / 2);
    }
  }, [activeAudioCueIdx]);

  // Prevent video and audio from playing simultaneously in task cards
  useEffect(() => {
    // This effect will handle synchronization when audio preview is active
    if (!audioPreviewTaskId) return;
    
    const audio = audioRef.current;
    if (!audio) return;
    
    const handleAudioPlay = () => {
      // If there's a modal video playing, pause it
      if (modalVideoRef.current && !modalVideoRef.current.paused) {
        modalVideoRef.current.pause();
      }
    };
    
    audio.addEventListener('play', handleAudioPlay);
    
    return () => {
      audio.removeEventListener('play', handleAudioPlay);
    };
  }, [audioPreviewTaskId]);

  // No debug logs in production

  // Always set first text track to showing when present
  useEffect(() => {
    if (!selectedTaskForPreview || !modalVideoRef.current) return;
    try {
      const tracks = modalVideoRef.current.textTracks;
      if (tracks && tracks.length > 0) {
        tracks[0].mode = 'showing';
      }
    } catch {}
  }, [selectedTaskForPreview]);

  // Prevent video and audio from playing simultaneously - when modal video plays, pause audio preview
  useEffect(() => {
    if (!selectedTaskForPreview) return;
    
    const video = modalVideoRef.current;
    if (!video) return;
    
    const handleVideoPlay = () => {
      // If there's an audio preview playing, pause it
      if (audioPreviewTaskId && audioRef.current && !audioRef.current.paused) {
        audioRef.current.pause();
      }
    };
    
    video.addEventListener('play', handleVideoPlay);
    
    return () => {
      video.removeEventListener('play', handleVideoPlay);
    };
  }, [selectedTaskForPreview, audioPreviewTaskId]);

  // Probe actual video availability via HEAD when opening/changing selection (skip for podcast-only and when in audio mode)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!selectedTaskForPreview) return;
      const tt = (selectedTaskForPreview.task_type || (selectedTaskForPreview.state as any)?.task_type || '').toLowerCase();
      if (tt === 'podcast' || modalPreviewMode === 'audio') {
        // Podcast-only: don't probe video to avoid spurious requests
        setHasVideoAssetByTask((m) => ({ ...m, [selectedTaskForPreview.task_id]: false }));
        return;
      }
      const id = selectedTaskForPreview.task_id;
      try {
        const ok = await apiHeadTaskVideo(id);
        if (!cancelled) setHasVideoAssetByTask((m) => ({ ...m, [id]: ok }));
      } catch {
        if (!cancelled) setHasVideoAssetByTask((m) => ({ ...m, [id]: false }));
      }
    })();
    return () => { cancelled = true; };
  }, [selectedTaskForPreview, apiBaseUrl, modalPreviewMode]);

  // Choose default modal mode per task: podcast -> audio, else video.
  // Do not override when user explicitly chose a mode.
  useEffect(() => {
    if (!selectedTaskForPreview) return;
    const tt = (selectedTaskForPreview.task_type || (selectedTaskForPreview.state as any)?.task_type || '').toLowerCase();
    if (modalModePinnedRef.current) return;
    setModalPreviewMode(tt === 'podcast' ? 'audio' : 'video');
  }, [selectedTaskForPreview]);

  // Ensure loading overlay appears immediately when switching to Video mode
  useEffect(() => {
    if (!selectedTaskForPreview) return;
    if (modalPreviewMode === 'video') setModalVideoLoading(true);
  }, [selectedTaskForPreview, modalPreviewMode]);

  // When entering audio mode, force a reload to trigger network consistently
  useEffect(() => {
    if (!selectedTaskForPreview) return;
    if (modalPreviewMode !== 'audio') return;
    const a = modalAudioRef.current;
    if (a) {
      try {
        a.load();
      } catch {}
    }
  }, [selectedTaskForPreview, modalPreviewMode]);

  // Fetch paged task list (lightweight) with smart polling only when active tasks exist
  const filesQuery = useFilesQuery(
    { page: currentPage, limit: tasksPerPage, includeTasks: true, q: debouncedSearch || undefined },
    {
      refetchInterval: (query: any) => {
        const data = (query?.state?.data as any)?.files || [];
        // If any embedded task is active, poll
        const hasActive = data.some((f: any) => (f.tasks || []).some((t: Task) => t.status === 'processing' || t.status === 'queued'));
        return hasActive ? 15000 : false;
      },
      staleTime: 10000,
    }
  );
  const counts = React.useMemo(() => {
    const files = ((filesQuery.data as any)?.files || []) as Array<{ tasks?: Task[] }>;
    let filesCount = 0;
    let creationsCount = 0;
    let runningCount = 0;
    for (const f of files) {
      const tasksInFile = (f.tasks || []) as Task[];
      const vis = statusFilter === 'all' ? tasksInFile : tasksInFile.filter((t) => t.status === statusFilter);
      if (vis.length > 0) filesCount++;
      creationsCount += vis.length;
      runningCount += tasksInFile.filter((t) => t.status === 'processing').length;
    }
    return { filesCount, creationsCount, runningCount };
  }, [filesQuery.data, statusFilter]);
  const runFileTask = useRunFileTaskMutation();

  // Bridge query state to existing local state fields
  useEffect(() => {
    // when not searching, mirror tasks to flattened files result for features relying on tasks[]
    setLoading(filesQuery.isLoading || filesQuery.isFetching);
  }, [filesQuery.isLoading, filesQuery.isFetching]);
  useEffect(() => {
    if (filesQuery.isError) {
      setError('Failed to fetch file groups');
      setQueueUnavailable(true);
    } else {
      setError(null);
    }
  }, [filesQuery.isError]);
  useEffect(() => {
    const resp: any = filesQuery.data as any;
    const files = resp?.files;
    if (Array.isArray(files)) {
      // Flatten embedded tasks for helper lookups (prefetchTaskDownloads uses tasks list)
      const flat: Task[] = files.flatMap((f: any) => Array.isArray(f.tasks) ? f.tasks : []);
      setTasks(flat);
      setQueueUnavailable(false);
    }
  }, [filesQuery.data]);

  // Removed system statistics for Creations panel

  // Lightweight polling while tasks are running to keep UI in sync (list only)
  // Lightweight polling while tasks are running
  // React Query handles polling via refetchInterval above

  // Initial load and periodic stats refresh (every 30s)
  // Initial load handled by queries; keep controller cleanup noop
  useEffect(() => {
    const ctrl = tasksControllerRef.current;
    return () => { try { ctrl?.abort(); } catch {} };
  }, []);

  // (Removed) fetching per-task audio tracks; using final audio endpoint directly

  // Persist expanded set to localStorage
  useEffect(() => {
    try {
      const arr = Array.from(expandedDownloads);
      localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify(arr));
    } catch {}
  }, [expandedDownloads]);

  // Load persisted expanded state on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(EXPANDED_STORAGE_KEY);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) {
          setExpandedDownloads(new Set(arr.filter((x) => typeof x === 'string')));
        }
      }
    } catch {}
  }, []);

  // Auto-expand newly completed tasks once
  useEffect(() => {
    if (!tasks || tasks.length === 0) return;
    setExpandedDownloads((prev) => {
      const next = new Set(prev);
      for (const t of tasks) {
        const prevStatus = prevStatusesRef.current[t.task_id];
        if (t.status === 'completed' && prevStatus && prevStatus !== 'completed') {
          // Only auto-expand if user hasn't persisted an opposite preference
          next.add(t.task_id);
        }
        // Update prev status map
        prevStatusesRef.current[t.task_id] = t.status;
      }
      return next;
    });
  }, [tasks]);

  // Debounced search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery.trim()), 400);
    return () => clearTimeout(t);
  }, [searchQuery]);
  const hasSearch = debouncedSearch.length > 0;

  // Lightweight toast
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2800);
    return () => clearTimeout(t);
  }, [toast]);

  // Cancel task
  const cancelTask = async (taskId: string) => {
    try {
      await apiCancelRun(taskId);
      await queryClient.invalidateQueries({ queryKey: ['tasks'] });
      await queryClient.invalidateQueries({ queryKey: ['tasksSearch'] });
    } catch (err) {
      console.error('Error cancelling task:', err);
      alert('Failed to cancel task');
    }
  };

  // Delete task (purge from backend)
  const deleteTask = async (taskId: string) => {
    if (!window.confirm('This will permanently remove the task and its state. Continue?')) {
      return;
    }
    try {
      // Trigger removal animation first
      setRemovingTaskIds((prev) => new Set(prev).add(taskId));

      // Perform deletion request in parallel
      const doDelete = (async () => { try { await apiPurgeTask(taskId); } catch (e) { throw e; } })();

      // Allow CSS transition to play before we refresh the list
      setTimeout(async () => {
        try {
          await doDelete;
        } catch (e) {
          console.error('Error deleting task:', e);
          alert('Failed to delete task');
        } finally {
          // Refresh task list and clear removing flag
          await queryClient.invalidateQueries({ queryKey: ['tasks'] });
          await queryClient.invalidateQueries({ queryKey: ['tasksSearch'] });
          setRemovingTaskIds((prev) => {
            const next = new Set(prev);
            next.delete(taskId);
            return next;
          });
        }
      }, 280);
    } catch (err) {
      console.error('Error deleting task:', err);
      alert('Failed to delete task');
    }
  };

  // File group expand/collapse persistence
  useEffect(() => {
    try {
      const raw = localStorage.getItem(FILES_EXPANDED_KEY);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) setExpandedFiles(new Set(arr.filter((x) => typeof x === 'string')));
      }
    } catch {}
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem(FILES_EXPANDED_KEY, JSON.stringify(Array.from(expandedFiles)));
    } catch {}
  }, [expandedFiles]);
  const toggleFileGroup = (key: string) => {
    setExpandedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Preview task - show generated video
  const previewTask = (task: Task, mode?: 'video' | 'audio') => {
    if (task.status === 'completed') {
      setSelectedTaskForPreview(task);
      // Prefetch downloads/transcript to improve modal readiness
      prefetchTaskDownloads(task.task_id).catch(() => {});
      // Decide initial modal mode (prefer requested mode; else prefer video)
      try {
        if (mode) {
          modalModePinnedRef.current = true;
          setModalPreviewMode(mode);
        } else {
          const dl = getCachedDownloads(queryClient, task.task_id);
          const items = dl?.items;
          const hasVideo = Array.isArray(items) ? items.some((it: any) => it?.type === 'video') : false;
          const isPodcast = Array.isArray(items) ? items.some((it: any) => it?.type === 'podcast') : false;
          setModalPreviewMode(hasVideo ? 'video' : (isPodcast ? 'audio' : 'audio'));
        }
      } catch {}
    } else {
      alert('Preview is only available for completed tasks.');
    }
  };

  // Close preview
  const closePreview = () => {
    setSelectedTaskForPreview(null);
    modalModePinnedRef.current = false;
  };

  // ESC key handler for closing modal (robust across browsers)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const isEscape = event.key === 'Escape' || event.key === 'Esc' || (event as any).keyCode === 27;
      if (isEscape && selectedTaskForPreview) {
        event.preventDefault();
        closePreview();
      }
    };

    if (selectedTaskForPreview) {
      document.addEventListener('keydown', handleKeyDown);
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset'; // Restore scrolling
    };
  }, [selectedTaskForPreview]);

  // Removed modal audio side-effects (unused UI state)

  // Removed unused fmtTime helper

  // getStatusColor removed (unused)

  // formatDate removed (unused)

  // Get language display name
  const getLanguageDisplayName = (languageCode: string): string => {
    const languageNames: Record<string, string> = {
      'english': 'English',
      'simplified_chinese': '简体中文',
      'traditional_chinese': '繁體中文',
      'japanese': '日本語',
      'korean': '한국어',
      'thai': 'ไทย'
    };
    return languageNames[languageCode] || languageCode || 'Unknown';
  };

  // Get video resolution display name
  const getVideoResolutionDisplayName = (resolution: string): string => {
    const resolutionNames: Record<string, string> = {
      'sd': 'SD (640×480)',
      'hd': 'HD (1280×720)',
      'fullhd': 'Full HD (1920×1080)'
    };
    return resolutionNames[resolution] || resolution || 'Unknown';
  };

  // formatStepNameWithLanguages removed (unused)

  // Get file type display name
  const getFileTypeDisplayName = (fileExt: string): string => {
    const ext = fileExt?.toLowerCase();
    switch (ext) {
      case '.pdf':
        return 'PDF';
      case '.pptx':
        return 'PPT';
      case '.ppt':
        return 'PPT';
      default:
        return `${ext?.toUpperCase() || 'Unknown'}`;
    }
  };

  // Check if file is PDF
  const isPdfFile = (fileExt: string): boolean => {
    return fileExt?.toLowerCase() === '.pdf';
  };

  // Handle search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // On submit, sync debounced input immediately
    setDebouncedSearch(searchQuery.trim());
  };

  // Handle status filter change
  const handleStatusFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  // filesQuery key already depends on currentPage and debounced search

  if (loading && tasks.length === 0) {
    return (
      <div className="task-monitor">
        <div className="loading">Loading tasks...</div>
      </div>
    );
  }

  if (error && tasks.length === 0) {
    return (
      <div className="task-monitor">
        <div className="error">{error}</div>
        <button onClick={() => filesQuery.refetch()} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="task-monitor">
      {toast && (
        <div className={`toast ${toast.type}`} role="status" aria-live="polite">{toast.message}</div>
      )}
      <div className="monitor-header">
        <h2>Creations</h2>
        <div className="monitor-counts" aria-live="polite">
          {counts.filesCount} files · {counts.creationsCount} creations · {counts.runningCount} running
        </div>
        <div className="monitor-controls">
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            {/* legacy inline task UI (commented out) */}
            <button type="submit" className="search-button">
              Search
            </button>
          </form>
          
          <select
            value={statusFilter}
            onChange={handleStatusFilterChange}
            className="status-filter"
          >
            <option value="all">All Status</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Creations panel intentionally omits system statistics */}

      {/* Task List (grouped by file) */}
      <div className="task-list">
        {queueUnavailable && (
          <div className="queue-warning" role="status" aria-live="polite">
            ⚠️ Queue unavailable. Processing may be paused. Check Redis connection.
          </div>
        )}

        {(!hasSearch && (!filesQuery.data || (filesQuery.data as any).files?.length === 0)) ? (
          <div className="no-tasks">No tasks found</div>
        ) : hasSearch ? (
          (() => {
            // Group tasks by file_id so multiple runs for the same file are together
            type Group = { file_id: string; filename?: string; file_ext?: string; tasks: Task[]; newestUpdatedAt: number };
            const groupsMap = new Map<string, Group>();
            for (const t of tasks) {
              const fid = t.file_id || t.kwargs?.file_id;
              const key = fid || `unknown:${t.kwargs?.filename || 'Unknown'}`;
              const g = groupsMap.get(key);
              const updatedAt = Date.parse(t.updated_at || t.created_at || '');
              if (!g) {
                groupsMap.set(key, {
                  file_id: fid,
                  filename: t.kwargs?.filename || t.state?.filename,
                  file_ext: t.kwargs?.file_ext,
                  tasks: [t],
                  newestUpdatedAt: isFinite(updatedAt) ? updatedAt : 0,
                });
              } else {
                g.tasks.push(t);
                g.newestUpdatedAt = Math.max(g.newestUpdatedAt, isFinite(updatedAt) ? updatedAt : 0);
                if (!g.filename) g.filename = t.kwargs?.filename || t.state?.filename;
                if (!g.file_ext) g.file_ext = t.kwargs?.file_ext;
              }
            }
            // Sort groups by most recent activity
            const groups = Array.from(groupsMap.values()).sort((a, b) => b.newestUpdatedAt - a.newestUpdatedAt);
            // Sort tasks within each group by most recent first
            for (const g of groups) g.tasks.sort((a, b) => Date.parse(b.updated_at || b.created_at) - Date.parse(a.updated_at || a.created_at));

            return (
              <div className="file-groups">
                {groups.map((g) => {
                  const visibleTasks = g.tasks.filter((t) => statusFilter === 'all' || t.status === statusFilter);
                  if (visibleTasks.length === 0) return null;
                  return (
                  <section key={g.file_id || g.filename || 'unknown-file'} className="file-group">
                    <header className="file-group-header" role="button" onClick={() => toggleFileGroup(g.file_id || g.filename || 'unknown-file')}>
                      <div className={`file-badge ${isPdfFile(g.file_ext as any) ? 'pdf' : 'ppt'}`}>{getFileTypeDisplayName(g.file_ext as any)}</div>
                      <div className="file-title" title={g.filename || 'Unknown file'}>
                        {g.filename || 'Unknown file'}
                        {g.file_id && (
                          <span className="file-id-chip" title={g.file_id}>ID: <span className="id-mono">{g.file_id}</span></span>
                        )}
                      </div>
                      <div className="task-count">{visibleTasks.length} {visibleTasks.length === 1 ? 'task' : 'tasks'}</div>
                      <div className="chev" aria-hidden>{expandedFiles.has(g.file_id || g.filename || 'unknown-file') ? '▴' : '▾'}</div>
                      <div className="file-group-actions" onClick={(e) => e.stopPropagation()}>
                        <button className="mini-btn" title="Run Video" onClick={() => {
                          if (!g.file_id) return;
                          setRunFile({ file_id: g.file_id, filename: g.filename, isPdf: isPdfFile(g.file_ext as any) });
                          const defs = getGlobalRunDefaults();
                          setRunDefaults({
                            task_type: 'video',
                            voice_language: defs.voice_language,
                            subtitle_language: (defs.subtitle_language ?? null),
                            video_resolution: defs.video_resolution || 'hd',
                          });
                          setRunOpen(true);
                        }}>Run Video</button>
                        {isPdfFile(g.file_ext as any) && (
                        <button className="mini-btn" title="Run Podcast" onClick={() => {
                          if (!g.file_id) return;
                          setRunFile({ file_id: g.file_id, filename: g.filename, isPdf: isPdfFile(g.file_ext as any) });
                          const defs = getGlobalRunDefaults();
                          setRunDefaults({
                            task_type: 'podcast',
                            voice_language: defs.voice_language,
                            transcript_language: (defs.transcript_language ?? null),
                            video_resolution: defs.video_resolution || 'hd',
                          });
                          setRunOpen(true);
                        }}>Run Podcast</button>
                        )}
                      </div>
                    </header>
                    {expandedFiles.has(g.file_id || g.filename || 'unknown-file') && (
                    <div className="file-task-list">
                      {visibleTasks.map((task) => (
                        <TaskCard
                          key={task.task_id}
                          task={task}
                          apiBaseUrl={apiBaseUrl}
                          isRemoving={removingTaskIds.has(task.task_id)}
                          isExpanded={expandedDownloads.has(task.task_id)}
                          onToggleDownloads={toggleDownloads}
                          onPreview={previewTask}
                          onCancel={cancelTask}
                          onDelete={deleteTask}
                          deriveTaskOutputs={deriveTaskOutputs}
                          getLanguageDisplayName={getLanguageDisplayName}
                          getVideoResolutionDisplayName={getVideoResolutionDisplayName}
                        />
                      ))}
                    </div>
                    )}
                  </section>
                );})}
              </div>
            );
          })()
        ) : (
          // Render from server-grouped files including embedded tasks
          (() => {
            const files = (filesQuery.data as any)?.files || [];
            return (
              <div className="file-groups">
                {files.map((f: any) => {
                  const tasksInFile: Task[] = (f.tasks || []) as Task[];
                  const visibleTasks = tasksInFile.filter((t) => statusFilter === 'all' || t.status === statusFilter);
                  if (visibleTasks.length === 0) return null;
                  return (
                  <section key={f.file_id || f.filename || 'unknown-file'} className="file-group">
                    <header className="file-group-header" role="button" onClick={() => toggleFileGroup(f.file_id || f.filename || 'unknown-file')}>
                      <div className={`file-badge ${isPdfFile(f.file_ext as any) ? 'pdf' : 'ppt'}`}>{getFileTypeDisplayName(f.file_ext as any)}</div>
                      <div className="file-title" title={f.filename || 'Unknown file'}>
                        {f.filename || 'Unknown file'}
                        {f.file_id && (
                          <span className="file-id-chip" title={f.file_id}>ID: <span className="id-mono">{f.file_id}</span></span>
                        )}
                      </div>
                      <div className="task-count">{visibleTasks.length} {visibleTasks.length === 1 ? 'task' : 'tasks'}</div>
                      <div className="chev" aria-hidden>{expandedFiles.has(f.file_id || f.filename || 'unknown-file') ? '▴' : '▾'}</div>
                      <div className="file-group-actions" onClick={(e) => e.stopPropagation()}>
                        <button className="mini-btn" title="Run Video" onClick={() => {
                          if (!f.file_id) return;
                          setRunFile({ file_id: f.file_id, filename: f.filename, isPdf: isPdfFile(f.file_ext as any) });
                          const defs = getGlobalRunDefaults();
                          setRunDefaults({
                            task_type: 'video',
                            voice_language: defs.voice_language,
                            subtitle_language: (defs.subtitle_language ?? null),
                            video_resolution: defs.video_resolution || 'hd',
                          });
                          setRunOpen(true);
                        }}>Run Video</button>
                        {isPdfFile(f.file_ext as any) && (
                        <button className="mini-btn" title="Run Podcast" onClick={() => {
                          if (!f.file_id) return;
                          setRunFile({ file_id: f.file_id, filename: f.filename, isPdf: isPdfFile(f.file_ext as any) });
                          const defs = getGlobalRunDefaults();
                          setRunDefaults({
                            task_type: 'podcast',
                            voice_language: defs.voice_language,
                            transcript_language: (defs.transcript_language ?? null),
                            video_resolution: defs.video_resolution || 'hd',
                          });
                          setRunOpen(true);
                        }}>Run Podcast</button>
                        )}
                      </div>
                    </header>
                    {expandedFiles.has(f.file_id || f.filename || 'unknown-file') && (
                    <div className="file-task-list">
                      {visibleTasks.map((task: Task) => (
                        <TaskCard
                          key={task.task_id}
                          task={task}
                          apiBaseUrl={apiBaseUrl}
                          isRemoving={removingTaskIds.has(task.task_id)}
                          isExpanded={expandedDownloads.has(task.task_id)}
                          onToggleDownloads={toggleDownloads}
                          onPreview={previewTask}
                          onCancel={cancelTask}
                          onDelete={deleteTask}
                          deriveTaskOutputs={deriveTaskOutputs}
                          getLanguageDisplayName={getLanguageDisplayName}
                          getVideoResolutionDisplayName={getVideoResolutionDisplayName}
                        />
                      ))}
                    </div>
                    )}
                  </section>
                );})}
              </div>
            );
          })()
        )}
      </div>

      {/* Pagination */}
      <div className="pagination">
        <button
          onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          className="page-button"
        >
          Previous
        </button>
        <span className="page-info">
          Page {currentPage}
        </span>
        <button
          onClick={() => setCurrentPage(currentPage + 1)}
          disabled={hasSearch ? tasks.length < tasksPerPage : !((filesQuery.data as any)?.has_more)}
          className="page-button"
        >
          Next
        </button>
      </div>

      {/* Preview Modal (Video or Podcast) */}
      <PreviewModal
        open={Boolean(selectedTaskForPreview)}
        mode={modalPreviewMode}
        onClose={closePreview}
        header={(
                  (() => {
              if (!selectedTaskForPreview) return null as any;
              const tt = (selectedTaskForPreview.task_type || (selectedTaskForPreview.state as any)?.task_type || '').toLowerCase();
              const dl = getCachedDownloads(queryClient, selectedTaskForPreview.task_id);
              const itemsRaw = (dl as any)?.items;
              const items = Array.isArray(itemsRaw) ? itemsRaw : [];
              const hasVideo = items.some((it: any) => it?.type === 'video');
              const hasPodcast = items.some((it: any) => it?.type === 'podcast');
              const showVideoBadge = hasVideo || ["video","both"].includes(tt);
              const showPodcastBadge = hasPodcast || ["podcast","both"].includes(tt);
              const showToggle = hasVideo && hasPodcast;
              const icon = modalPreviewMode === 'video' ? '🎬' : '🎧';
              return (
                <div className="modal-header-bar" data-mode={modalPreviewMode}>
                  <div className="header-left" aria-label="Media Preview">
                    <span className="header-icon" aria-hidden>{icon}</span>
                    <span>Media Preview</span>
                  </div>
                  <div className="header-right">
                    {showVideoBadge && <span className="output-pill video" title="Includes video">🎬 Video</span>}
                    {showPodcastBadge && <span className="output-pill podcast" title="Includes podcast">🎧 Podcast</span>}
                    {showToggle && (
                      <div className="modal-mode-toggle">
                        <button type="button" className={`toggle-btn ${modalPreviewMode === 'video' ? 'active' : ''}`} onClick={() => setModalPreviewMode('video')}>🎬 Video</button>
                        <button type="button" className={`toggle-btn ${modalPreviewMode === 'audio' ? 'active' : ''}`} onClick={() => setModalPreviewMode('audio')}>🎧 Podcast</button>
                      </div>
                    )}
                    <button type="button" className="modal-close-btn" aria-label="Close" title="Close" onClick={closePreview}>
                      <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })()
        )}
      >
        {/* Preview content: video or podcast depending on mode/availability */}
              {(() => {
                if (!selectedTaskForPreview) return null as any;
                const voiceLanguage = selectedTaskForPreview.kwargs?.voice_language || selectedTaskForPreview.state?.voice_language || 'english';
                const subtitleLanguage = selectedTaskForPreview.kwargs?.subtitle_language || selectedTaskForPreview.state?.subtitle_language || voiceLanguage;
                const videoUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/video`;
                const subtitleUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
                const tt = (selectedTaskForPreview.task_type || (selectedTaskForPreview.state as any)?.task_type || '').toLowerCase();
                if (modalPreviewMode === 'video') {
                  return (
                    <div className="modal-preview-stack">
                      <div className="modal-video-wrapper">
                        <VideoPlayer
                          src={videoUrl}
                          trackUrl={subtitleUrl}
                          trackLang={subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : subtitleLanguage === 'japanese' ? 'ja' : subtitleLanguage === 'korean' ? 'ko' : subtitleLanguage === 'thai' ? 'th' : 'en'}
                          trackLabel={getLanguageDisplayName(subtitleLanguage)}
                          className="video-player"
                          onReady={() => setModalVideoLoading(false)}
                          onError={(e) => { console.error('Video loading error:', e); setVideoError('Failed to load video'); }}
                        />
                        {!videoError && modalVideoLoading && (
                          <div className="video-status-overlay loading" role="status" aria-live="polite">
                            <div className="spinner" aria-hidden></div>
                            <span className="loading-text">Loading video…</span>
                          </div>
                        )}
                        <div className="preview-file-info">
                          <div className={`file-type-badge ${isPdfFile(selectedTaskForPreview.kwargs?.file_ext) ? 'pdf' : 'ppt'}`}>
                            {getFileTypeDisplayName(selectedTaskForPreview.kwargs?.file_ext)}
                          </div>
                        </div>
                        {videoError && (
                          <div className="video-status-overlay error">
                            <p>❌ {videoError}</p>
                            <button onClick={() => { setVideoError(null); const el = document.querySelector('.video-player') as HTMLVideoElement; if (el) { el.load(); el.play().catch(()=>{});} }} className="retry-button">Retry</button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }
                // Podcast/audio modal preview (simple & clean)
                // Prefer task_type when available, then availability map
                // Determine mode by task type and availability when rendering audio view
                const isPodcastTask = (tt === 'podcast');
                const audioUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/${isPodcastTask ? 'podcast' : 'audio'}`;
                const vttUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
                return (
                  <div className="modal-preview-stack">
                    {isPodcastTask ? (
                      <PodcastPlayer src={audioUrl} transcriptMarkdown={(queryClient.getQueryData(['transcript', selectedTaskForPreview.task_id]) as any) ?? transcriptMdByTask[selectedTaskForPreview.task_id]} />
                    ) : (
                      <AudioPlayer src={audioUrl} vttUrl={vttUrl} />
                    )}
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
          // Save chosen defaults for next time
          saveGlobalRunDefaults({
            voice_language: payload.voice_language,
            subtitle_language: payload.subtitle_language ?? null,
            transcript_language: payload.transcript_language ?? null,
            video_resolution: payload.video_resolution || 'hd',
          });
          runFileTask.mutate(
            { fileId: runFile.file_id, payload },
            {
              onSuccess: (res: any) => {
                setRunOpen(false);
                setToast({ type: 'success', message: `Task created: ${res?.task_id || ''}` });
              },
              onError: () => {
                setToast({ type: 'error', message: `Failed to create task` });
              },
              onSettled: () => setRunSubmitting(false),
            }
          );
        }}
      />
    </div>
  );
};

export default Creations;

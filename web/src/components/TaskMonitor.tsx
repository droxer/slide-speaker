import React, { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getDownloads as apiGetDownloads, headTaskVideo as apiHeadTaskVideo, cancelRun as apiCancelRun, purgeTask as apiPurgeTask } from '../services/client';
import { useTasksQuery, useStatsQuery, useSearchTasksQuery, useVttQuery, getCachedDownloads } from '../services/queries';
import '../styles/task-monitor.scss';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import PodcastPlayer from './PodcastPlayer';
import TaskCard from './TaskCard';
import PreviewModal from './PreviewModal';
// import { getStepLabel } from '../utils/stepLabels';

// Types for task monitoring
import type { Task } from '../types';

interface TaskStatistics {
  total_tasks: number;
  status_breakdown: Record<string, number>;
  language_stats: Record<string, number>;
  recent_activity: {
    last_24h: number;
    last_7d: number;
    last_30d: number;
  };
  processing_stats: {
    avg_processing_time_minutes?: number;
    success_rate: number;
    failed_rate: number;
  };
}

interface TaskMonitorProps {
  apiBaseUrl: string; // kept for compatibility; media uses relative paths
}

const TaskMonitor: React.FC<TaskMonitorProps> = ({ apiBaseUrl }) => {
  const EXPANDED_STORAGE_KEY = 'slidespeaker_taskmonitor_expanded_v1';
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statistics, setStatistics] = useState<TaskStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queueUnavailable, setQueueUnavailable] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
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
    // When opening, fetch downloads to detect podcast/subtitles/video availability
    ;(async () => {
      try {
        await queryClient.fetchQuery({ queryKey: ['downloads', taskId], queryFn: () => apiGetDownloads(taskId) });
        // Prefetch handled by shared prefetchTaskPreview; nothing else here
      } catch (_e) {
        /* ignore */
      }
    })();
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

  // Debug log for preview state
  useEffect(() => {
    console.log('Selected task for preview:', selectedTaskForPreview);
  }, [selectedTaskForPreview]);

  // Debug API base URL
  useEffect(() => {
    console.log('TaskMonitor apiBaseUrl:', apiBaseUrl);
  }, [apiBaseUrl]);

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

  // Fetch paged task list (lightweight)
  // React Query: tasks list
  const tasksQuery = useTasksQuery({ status: statusFilter, page: currentPage, limit: tasksPerPage });

  // Bridge query state to existing local state fields
  useEffect(() => {
    setLoading(tasksQuery.isLoading || tasksQuery.isFetching);
  }, [tasksQuery.isLoading, tasksQuery.isFetching]);
  useEffect(() => {
    if (tasksQuery.isError) {
      setError('Failed to fetch task data');
      setQueueUnavailable(true);
    } else {
      setError(null);
    }
  }, [tasksQuery.isError]);
  useEffect(() => {
    if (tasksQuery.data) {
      setTasks(tasksQuery.data);
      setQueueUnavailable(false);
    }
  }, [tasksQuery.data]);

  // Fetch overall statistics (decoupled from frequent list polling)
  // React Query: stats (polling every 30s)
  const statsQuery = useStatsQuery();
  useEffect(() => {
    if (statsQuery.data) setStatistics(statsQuery.data as any);
  }, [statsQuery.data]);

  // Lightweight polling while tasks are running to keep UI in sync (list only)
  // Lightweight polling while tasks are running
  useEffect(() => {
    const hasActive = tasks.some(t => t.status === 'processing' || t.status === 'queued');
    if (!hasActive) return;
    const id = setInterval(() => { tasksQuery.refetch(); }, 15000);
    return () => clearInterval(id);
  }, [tasks, tasksQuery]);

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

  // Search tasks via React Query (enabled when query present)
  const hasSearch = searchQuery.trim().length > 0;
  const searchTasksQuery = useSearchTasksQuery(searchQuery);
  useEffect(() => {
    if (!hasSearch) return;
    setLoading(searchTasksQuery.isLoading || searchTasksQuery.isFetching);
  }, [hasSearch, searchTasksQuery.isLoading, searchTasksQuery.isFetching]);
  useEffect(() => {
    if (!hasSearch) return;
    if (searchTasksQuery.isError) {
      setError('Failed to search tasks');
    } else {
      setError(null);
    }
  }, [hasSearch, searchTasksQuery.isError]);
  useEffect(() => {
    if (!hasSearch) return;
    const data = searchTasksQuery.data as any;
    if (data && Array.isArray(data.tasks)) {
      setTasks(data.tasks as any);
    }
  }, [hasSearch, searchTasksQuery.data]);

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

  // Preview task - show generated video
  const previewTask = (task: Task, mode?: 'video' | 'audio') => {
    console.log('Preview task called with:', task);
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
    // Submit triggers search refetch; queries auto-run on input change too
    if (searchQuery.trim()) searchTasksQuery.refetch();
    else tasksQuery.refetch();
  };

  // Handle status filter change
  const handleStatusFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  // tasksQuery key already depends on currentPage and statusFilter

  useEffect(() => {
    if (!searchQuery.trim()) tasksQuery.refetch();
  }, [searchQuery, tasksQuery]);

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
        <button onClick={() => tasksQuery.refetch()} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="task-monitor">
      <div className="monitor-header">
        <h2>Task Monitor</h2>
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

      {/* Enhanced Statistics Summary */}
      {statistics && (
        <div className="statistics-summary">
          <div className="stat-section">
            <h3 className="stat-section-title">📊 System Overview</h3>
            <div className="stat-cards-row">
              <div className="stat-card primary">
                <div className="stat-icon">📋</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.total_tasks}</div>
                  <div className="stat-label"><span className="full">Total Tasks</span><span className="short">Total</span></div>
                </div>
              </div>
              
              <div className="stat-card success">
                <div className="stat-icon">✅</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.processing_stats.success_rate.toFixed(1)}%</div>
                  <div className="stat-label"><span className="full">Success Rate</span><span className="short">Success</span></div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="stat-section">
            <h3 className="stat-section-title">⚡ Real-time Status</h3>
            <div className="stat-cards-row">
              <div className="stat-card info processing">
                <div className="stat-icon">⚡</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.status_breakdown.processing || 0}</div>
                  <div className="stat-label"><span className="full">Currently Running</span><span className="short">Running</span></div>
                  <div className="stat-description">Tasks in progress</div>
                </div>
              </div>
              
              <div className="stat-card warning queued">
                <div className="stat-icon">⏸️</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.status_breakdown.queued || 0}</div>
                  <div className="stat-label"><span className="full">In Queue</span><span className="short">Queue</span></div>
                  <div className="stat-description">Waiting to start</div>
                </div>
              </div>
              
              <div className="stat-card danger failed">
                <div className="stat-icon">❌</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.status_breakdown.failed || 0}</div>
                  <div className="stat-label"><span className="full">Failed Tasks</span><span className="short">Failed</span></div>
                  <div className="stat-description">Need attention</div>
                </div>
              </div>
            </div>
          </div>
          
        </div>
      )}

      {/* Task List */}
      <div className="task-list">
        {queueUnavailable && (
          <div className="queue-warning" role="status" aria-live="polite">
            ⚠️ Queue unavailable. Processing may be paused. Check Redis connection.
          </div>
        )}
        {tasks.length === 0 ? (
          <div className="no-tasks">No tasks found</div>
        ) : (
          tasks.map((task) => (
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
          ))
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
          disabled={tasks.length < tasksPerPage}
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
    </div>
  );
};

export default TaskMonitor;

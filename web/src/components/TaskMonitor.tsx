import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './TaskMonitor.scss';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import PodcastPlayer from './PodcastPlayer';
import { getStepLabel } from '../utils/stepLabels';

// Types for task monitoring
interface TaskState {
  status: string;
  current_step: string;
  filename?: string;
  voice_language: string;
  subtitle_language?: string;
  podcast_transcript_language?: string;
  video_resolution?: string;
  generate_avatar: boolean;
  generate_subtitles: boolean;
  created_at: string;
  updated_at: string;
  errors: string[];
}

interface Task {
  task_id: string;
  file_id: string;
  task_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  // Optional DB-surfaced language hints (present in /api/tasks rows)
  voice_language?: string;
  subtitle_language?: string;
  kwargs: {
    file_id: string;
    file_ext: string;
    filename?: string;
    voice_language: string;
    subtitle_language?: string;
    video_resolution?: string;
    generate_avatar: boolean;
    generate_subtitles: boolean;
    transcript_language?: string;
  };
  state?: TaskState;
  detailed_state?: any;
  completion_percentage?: number;
}

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
  const [podcastAvailableByTask, setPodcastAvailableByTask] = useState<Record<string, boolean>>({});
  const [videoAvailableByTask, setVideoAvailableByTask] = useState<Record<string, boolean>>({});
  const [audioAvailableByTask, setAudioAvailableByTask] = useState<Record<string, boolean>>({}); // eslint-disable-line @typescript-eslint/no-unused-vars
  const [previewModeByTask, setPreviewModeByTask] = useState<Record<string, 'video' | 'audio'>>({}); // eslint-disable-line @typescript-eslint/no-unused-vars
  const [transcriptMdByTask, setTranscriptMdByTask] = useState<Record<string, string>>({});
  const [hasVideoAssetByTask, setHasVideoAssetByTask] = useState<Record<string, boolean>>({}); // eslint-disable-line @typescript-eslint/no-unused-vars
  // Networking controls to avoid duplicate requests
  const tasksControllerRef = React.useRef<AbortController | null>(null);
  const searchControllerRef = React.useRef<AbortController | null>(null);
  const searchDebounceRef = React.useRef<number | null>(null);
  const didInitRef = React.useRef<boolean>(false);
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

  // Prefetch downloads info and transcript for a task
  const prefetchTaskDownloads = async (taskId: string) => {
    try {
      const resp = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/downloads`);
      if (!resp.ok) return;
      const data = await resp.json();
      const items = Array.isArray(data.items) ? data.items : [];
      const hasPodcast = items.some((it: any) => it?.type === 'podcast');
      const hasVideo = items.some((it: any) => it?.type === 'video');
      const hasAudio = items.some((it: any) => it?.type === 'audio');
      setPodcastAvailableByTask((m) => ({ ...m, [taskId]: !!hasPodcast }));
      setVideoAvailableByTask((m) => ({ ...m, [taskId]: !!hasVideo }));
      setAudioAvailableByTask((m) => ({ ...m, [taskId]: !!hasAudio }));
      // Fetch conversation transcript for podcast tasks
      const t = tasks.find((x) => x.task_id === taskId);
      const tt = (t?.task_type || (t?.state as any)?.task_type || '').toLowerCase();
      const isPodcast = hasPodcast || ["podcast","both"].includes(tt);
      if (isPodcast) {
        try {
          const tr = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/transcripts/markdown`, { headers: { Accept: 'text/markdown' } });
          if (tr.ok) {
            const text = await tr.text();
            setTranscriptMdByTask((m) => ({ ...m, [taskId]: text }));
          }
        } catch {}
      } else {
        setTranscriptMdByTask((m) => { const n={...m}; delete n[taskId]; return n; });
      }
    } catch {
      /* ignore */
    }
  };

  // Ensure VTT for non-podcast audio preview is fetched when modal opens (with fallback + logging)
  useEffect(() => {
    const t = selectedTaskForPreview;
    if (!t) { setAudioCues([]); return; }
    const taskType = (t.task_type || (t.state as any)?.task_type || '').toLowerCase();
    if (taskType === 'podcast') { setAudioCues([]); return; }
    const lang = (t.state?.subtitle_language || t.kwargs?.subtitle_language || t.kwargs?.voice_language || 'english');
    const urlWithLang = `${apiBaseUrl}/api/tasks/${t.task_id}/subtitles/vtt?language=${encodeURIComponent(lang)}`;
    const urlNoLang = `${apiBaseUrl}/api/tasks/${t.task_id}/subtitles/vtt`;
    let cancelled = false;
    (async () => {
      try {
        console.log('[TaskMonitor VTT] try:', urlWithLang);
        let resp = await fetch(urlWithLang, { headers: { Accept: 'text/vtt,*/*' } });
        if (!resp.ok) {
          console.log('[TaskMonitor VTT] fallback:', urlNoLang, 'status', resp.status);
          resp = await fetch(urlNoLang, { headers: { Accept: 'text/vtt,*/*' } });
        }
        if (cancelled) return;
        if (!resp.ok) { console.warn('[TaskMonitor VTT] failed'); setAudioCues([]); return; }
        const text = await resp.text();
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
            while (i < lines.length && lines[i].trim() && !timeRe.test(lines[i])) {
              textLines.push(lines[i].trim());
              i++;
            }
            cues.push({ start, end, text: textLines.join(' ') });
          }
        }
        setAudioCues(cues);
      } catch (e) {
        if (!cancelled) { console.warn('[TaskMonitor VTT] error', e); setAudioCues([]); }
      }
    })();
    return () => { cancelled = true; };
  }, [selectedTaskForPreview, apiBaseUrl]);

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
    let video: boolean | undefined = videoAvailableByTask[task.task_id];
    let podcast: boolean | undefined = podcastAvailableByTask[task.task_id];
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
    (async () => {
      try {
        const resp = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/downloads`);
        if (resp.ok) {
          const data = await resp.json();
          const items = Array.isArray(data.items) ? data.items : [];
          const hasPodcast = items.some((it: any) => it?.type === 'podcast');
          const hasVideo = items.some((it: any) => it?.type === 'video');
          const hasAudio = items.some((it: any) => it?.type === 'audio');
          setPodcastAvailableByTask((m) => ({ ...m, [taskId]: !!hasPodcast }));
          setVideoAvailableByTask((m) => (m[taskId] === !!hasVideo ? m : { ...m, [taskId]: !!hasVideo }));
          setAudioAvailableByTask((m) => (m[taskId] === !!hasAudio ? m : { ...m, [taskId]: !!hasAudio }));
          // Set default inline preview mode: prefer video when available
          setPreviewModeByTask((m) => {
            const desired: 'video'|'audio' = hasVideo ? 'video' : 'audio';
            if (m[taskId] === desired) return m;
            return { ...m, [taskId]: desired };
          });
          // Auto-open audio inline preview for podcast-only tasks once completed
          const t = tasks.find((x) => x.task_id === taskId);
          if (t && t.status === 'completed' && (!hasVideo || hasPodcast)) {
            setAudioPreviewTaskId(taskId);
          }
          // Fetch conversation transcript for podcast tasks
          const tt = ((tasks.find((x)=>x.task_id===taskId)?.task_type) || ((tasks.find((x)=>x.task_id===taskId)?.state as any)?.task_type) || '').toLowerCase();
          const isPodcast = hasPodcast || ["podcast","both"].includes(tt);
          if (isPodcast) {
            try {
              const tr = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/transcripts/markdown`, { headers: { Accept: 'text/markdown' } });
              if (tr.ok) {
                const text = await tr.text();
                setTranscriptMdByTask((m) => ({ ...m, [taskId]: text }));
              }
            } catch {}
          } else {
            setTranscriptMdByTask((m) => { const n={...m}; delete n[taskId]; return n; });
            // For non-podcast, prefetch VTT to enable subtitles in audio preview
            try {
              const lang = (t?.state?.subtitle_language || t?.kwargs?.subtitle_language || t?.kwargs?.voice_language || 'english');
              const vtt1 = `${apiBaseUrl}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(lang || 'english')}`;
              const vtt2 = `${apiBaseUrl}/api/tasks/${taskId}/subtitles/vtt`;
              // Fire and forget; parsing happens when modal opens
              fetch(vtt1, { headers: { Accept: 'text/vtt,*/*' } }).catch(()=>{});
              fetch(vtt2, { headers: { Accept: 'text/vtt,*/*' } }).catch(()=>{});
            } catch {}
          }
        }
      } catch {
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

  // Removed periodic health check; rely on fetchTasks errors to show banner

  // Removed explicit subtitle loading; <track> will load VTT on demand

  // Removed prefetching in modal to avoid duplicate network requests

  // Do not force subtitles to display in preview; user can enable via player controls


  // No imperative src assignment; <video src> handles local and S3 redirect

  // No Blob URL cleanup necessary

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
        const resp = await fetch(`${apiBaseUrl}/api/tasks/${id}/video`, { method: 'HEAD' });
        if (!cancelled) {
          setHasVideoAssetByTask((m) => ({ ...m, [id]: resp.ok }));
        }
      } catch {
        if (!cancelled) {
          setHasVideoAssetByTask((m) => ({ ...m, [id]: false }));
        }
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
  const isFetchingRef = React.useRef(false);
  const lastParamsRef = React.useRef<string | null>(null);
  const fetchTasks = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch task list
      const params = new URLSearchParams();
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      params.append('limit', tasksPerPage.toString());
      params.append('offset', ((currentPage - 1) * tasksPerPage).toString());
      const paramsStr = params.toString();
      // If an identical request is already in-flight, skip to avoid redundant/canceled calls
      if (isFetchingRef.current && lastParamsRef.current === paramsStr) {
        return;
      }
      // If a different-params request is in flight, abort it
      if (isFetchingRef.current && lastParamsRef.current !== paramsStr) {
        try { tasksControllerRef.current?.abort(); } catch {}
      }
      const ctrl = new AbortController();
      tasksControllerRef.current = ctrl;
      isFetchingRef.current = true;
      lastParamsRef.current = paramsStr;
      const tasksResponse = await axios.get(`${apiBaseUrl}/api/tasks?${paramsStr}`, { signal: ctrl.signal });
      // Keep only real tasks with valid task_id (exclude synthetic state_* entries)
      const realTasks = (tasksResponse.data.tasks || []).filter((t: any) => typeof t?.task_id === 'string' && !t.task_id.startsWith('state_'));
      setTasks(realTasks);
      setQueueUnavailable(false);

    } catch (err: any) {
      // Ignore abort errors from superseded calls
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') {
        return;
      }
      setError('Failed to fetch task data');
      setQueueUnavailable(true);
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
      isFetchingRef.current = false;
    }
  }, [apiBaseUrl, currentPage, statusFilter, tasksPerPage]);

  // Fetch overall statistics (decoupled from frequent list polling)
  const fetchStats = React.useCallback(async () => {
    try {
      const statsResponse = await axios.get(`${apiBaseUrl}/api/tasks/statistics`);
      setStatistics(statsResponse.data);
    } catch (err) {
      console.warn('Failed to fetch statistics:', err);
    }
  }, [apiBaseUrl]);

  // Lightweight polling while tasks are running to keep UI in sync (list only)
  useEffect(() => {
    const hasActive = tasks.some(t => t.status === 'processing' || t.status === 'queued');
    if (!hasActive) return; // no polling when idle

    const id = setInterval(() => {
      fetchTasks();
    }, 60000);

    return () => clearInterval(id);
  }, [tasks, fetchTasks]);

  // Initial load and periodic stats refresh (every 30s)
  useEffect(() => {
    let initTasksTimer: number | undefined;
    let initStatsTimer: number | undefined;
    if (!didInitRef.current) {
      didInitRef.current = true;
      // Defer initial fetch to avoid React Strict Mode immediate cleanup aborts
      initTasksTimer = window.setTimeout(() => { fetchTasks(); }, 0);
      initStatsTimer = window.setTimeout(() => { fetchStats(); }, 0);
    }
    const id = setInterval(fetchStats, 30000);
    return () => {
      clearInterval(id);
      if (initTasksTimer) window.clearTimeout(initTasksTimer);
      if (initStatsTimer) window.clearTimeout(initStatsTimer);
      try { tasksControllerRef.current?.abort(); } catch {}
    };
  }, [fetchTasks, fetchStats]);

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

  // Search tasks
  const searchTasks = async (query: string) => {
    const q = query.trim();
    // Clear any pending debounce
    if (searchDebounceRef.current) {
      window.clearTimeout(searchDebounceRef.current);
      searchDebounceRef.current = null;
    }
    // Abort in‑flight search
    try { searchControllerRef.current?.abort(); } catch {}

    if (!q) {
      // Empty query: reload current list
      fetchTasks();
      return;
    }

    setLoading(true);
    setError(null);
    searchDebounceRef.current = window.setTimeout(async () => {
      try {
        const ctrl = new AbortController();
        searchControllerRef.current = ctrl;
        const response = await axios.get(`${apiBaseUrl}/api/tasks/search?query=${encodeURIComponent(q)}`,
          { signal: ctrl.signal }
        );
        setTasks(response.data.tasks);
      } catch (err: any) {
        if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return;
        setError('Failed to search tasks');
        console.error('Error searching tasks:', err);
      } finally {
        setLoading(false);
      }
    }, 300);
  };

  // Cancel task
  const cancelTask = async (taskId: string) => {
    try {
      await axios.delete(`${apiBaseUrl}/api/tasks/${taskId}`);
      // Refresh task list
      fetchTasks();
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
      const doDelete = axios.delete(`${apiBaseUrl}/api/tasks/${taskId}/purge`);

      // Allow CSS transition to play before we refresh the list
      setTimeout(async () => {
        try {
          await doDelete;
        } catch (e) {
          console.error('Error deleting task:', e);
          alert('Failed to delete task');
        } finally {
          // Refresh task list and clear removing flag
          await fetchTasks();
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
          const hasVideo = !!videoAvailableByTask[task.task_id];
          const isPodcast = !!podcastAvailableByTask[task.task_id];
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

  // Get task status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-completed';
      case 'processing':
        return 'status-processing';
      case 'queued':
        return 'status-queued';
      case 'failed':
        return 'status-failed';
      case 'cancelled':
        return 'status-cancelled';
      default:
        return 'status-default';
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

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

  // Format step name for better readability
  const formatStepName = (step: string): string => getStepLabel(step);

  // Context-aware step name (collapse translation when languages match)
  const formatStepNameWithLanguages = (
    step: string,
    voiceLang: string,
    subtitleLang?: string
  ): string => {
    const vl = (voiceLang || 'english').toLowerCase();
    const sl = (subtitleLang || vl).toLowerCase();
    const same = vl === sl;
    if (
      same &&
      (step === 'translate_voice_transcripts' || step === 'translate_subtitle_transcripts')
    ) {
      return 'Translating Transcripts';
    }
    return formatStepName(step);
  };

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
    if (searchQuery.trim()) {
      searchTasks(searchQuery);
    } else {
      fetchTasks();
    }
  };

  // Handle status filter change
  const handleStatusFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  useEffect(() => {
    fetchTasks();
  }, [currentPage, statusFilter, fetchTasks]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      fetchTasks();
    }
  }, [searchQuery, fetchTasks]);

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
        <button onClick={fetchTasks} className="retry-button">
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
            <div key={task.task_id} className={`task-item ${getStatusColor(task.status)} ${removingTaskIds.has(task.task_id) ? 'removing' : ''}`}>
              <div className="task-header">
                <div
                  className="task-id"
                  tabIndex={0}
                  role="button"
                  aria-label={`Task ID: ${task.task_id} (press Enter to copy)`}
                  title={task.task_id}
                  onClick={() => {
                    try {
                      navigator.clipboard.writeText(task.task_id);
                      alert('Task ID copied!');
                    } catch (err) {
                      console.error('Failed to copy task id', err);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      try {
                        navigator.clipboard.writeText(task.task_id);
                        alert('Task ID copied!');
                      } catch (err) {
                        console.error('Failed to copy task id', err);
                      }
                    }
                  }}
                >
                  Task: {task.task_id}
                </div>
                {(() => {
                  const statusLabel = (
                    task.status === 'completed' ? 'Completed' :
                    task.status === 'processing' ? 'Processing' :
                    task.status === 'queued' ? 'Queued' :
                    task.status === 'failed' ? 'Failed' :
                    task.status === 'cancelled' ? 'Cancelled' : String(task.status)
                  );
                  const statusContent = (
                    task.status === 'completed' ? 'Completed' :
                    task.status === 'processing' ? '⏳ Processing' :
                    task.status === 'queued' ? '⏸️ Queued' :
                    task.status === 'failed' ? '❌ Failed' :
                    task.status === 'cancelled' ? '🚫 Cancelled' : String(task.status)
                  );
                  return (
                    <div
                      className={`task-status ${getStatusColor(task.status)}`}
                      tabIndex={0}
                      aria-label={`Status: ${statusLabel}`}
                    >
                      {statusContent}
                    </div>
                  );
                })()}
              </div>
              
              <div className="task-details simple-details">
                {(() => {
                  const filename = task.kwargs?.filename || task.state?.filename;
                  const voiceLang = task.voice_language || task.kwargs?.voice_language || task.state?.voice_language || 'english';
                  const topSub = task.subtitle_language || task.kwargs?.subtitle_language || task.state?.subtitle_language || voiceLang;
                  const videoRes = task.kwargs?.video_resolution || task.state?.video_resolution || 'hd';
                  const { video: isVideoTask, podcast: isPodcastTask } = deriveTaskOutputs(task);
                  const transcriptLang = isPodcastTask
                    ? (task.kwargs?.transcript_language
                        || task.state?.podcast_transcript_language
                        || task.subtitle_language
                        || topSub)
                    : topSub;
                  return (
                    <>
                      {/* Title row: filename + file type */}
                      <div className="task-title-row">
                        <div className="task-title" title={filename || task.file_id}>
                          {filename || task.file_id}
                        </div>
                        <div className="output-badges" aria-label="Output type">
                          {isVideoTask && (
                            <span className="output-pill video" title="Video task">🎬 Video</span>
                          )}
                          {isPodcastTask && (
                            <span className="output-pill podcast" title="Podcast task">🎧 Podcast</span>
                          )}
                          <div className={`file-type-badge ${isPdfFile(task.kwargs?.file_ext) ? 'pdf' : 'ppt'}`}>
                            {getFileTypeDisplayName(task.kwargs?.file_ext)}
                          </div>
                        </div>
                      </div>

                      {/* Meta chips */}
                      <div className="meta-row">
                        <span className="chip">Voice: {getLanguageDisplayName(voiceLang)}</span>
                        {isPodcastTask ? (
                          <span className="chip">Transcript: {getLanguageDisplayName(transcriptLang)}</span>
                        ) : (
                          <span className="chip">Subs: {getLanguageDisplayName(transcriptLang)}</span>
                        )}
                        <span className="chip">{getVideoResolutionDisplayName(videoRes)}</span>
                      </div>

                      {/* Current step + progress for non-completed */}
                      {task.status !== 'completed' && task.state && (
                        <div className="step-progress">
                          <div className="step-line" role="status" aria-live="polite">{formatStepNameWithLanguages(task.state.current_step, voiceLang, transcriptLang)}</div>
                          {task.completion_percentage !== undefined && (
                            <div className="progress-rail" aria-valuemin={0} aria-valuemax={100} aria-valuenow={task.completion_percentage} role="progressbar">
                              <div className="progress-fill" style={{ width: `${Math.max(0, Math.min(100, task.completion_percentage))}%` }} />
                            </div>
                          )}
                        </div>
                      )}

                      {/* Timestamps small and subtle */}
                      <div className="timestamps-row">
                        <span className="timestamp">Created: {formatDate(task.created_at)}</span>
                        <span className="timestamp">Updated: {formatDate(task.updated_at)}</span>
                      </div>
                    </>
                  );
                })()}

                {task.status === 'completed' && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'flex-start', marginTop: 8 }}>
                      <button
                        onClick={() => toggleDownloads(task.task_id)}
                        className="link-button"
                        aria-expanded={expandedDownloads.has(task.task_id)}
                        aria-controls={`downloads-${task.task_id}`}
                        type="button"
                        title="Preview"
                      >
                        Preview <span className={`chevron ${expandedDownloads.has(task.task_id) ? 'open' : ''}`} aria-hidden="true" />
                      </button>
                    </div>
                    {!expandedDownloads.has(task.task_id) && (() => {
                      const { podcast: isPodcastTask, video: isVideoTask } = deriveTaskOutputs(task);
                      return (
                      <div className="resource-badges" aria-hidden>
                        {(isVideoTask || videoAvailableByTask[task.task_id]) && <span className="badge">Video</span>}
                        <span className="badge">{isPodcastTask ? 'Podcast' : 'Audio'}</span>
                        <span className="badge">Transcript</span>
                        {!isPodcastTask && <span className="badge">VTT</span>}
                        {!isPodcastTask && <span className="badge">SRT</span>}
                      </div>
                      );
                    })()}
                    <div className={`downloads-collapse ${expandedDownloads.has(task.task_id) ? 'open' : ''}`}>
                      {expandedDownloads.has(task.task_id) && (
                        <div className="resource-links" id={`downloads-${task.task_id}`}>
                        {/* Inline Video Preview removed by request; use header preview-button to open modal */}
                        {/* Inline Audio Preview removed by request; podcast/audio preview opens in modal */}
                        {/* Video (only if available) */}
                        {videoAvailableByTask[task.task_id] && (
                        <div className="url-copy-row">
                          <span className="resource-label-inline">Video</span>
                          <input
                            type="text"
                            value={`${apiBaseUrl}/api/tasks/${task.task_id}/video`}
                          readOnly
                          className="url-input-enhanced"
                          />
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/video`);
                              alert('Video URL copied!');
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>
                        )}

                        {/* Audio / Podcast */}
                        <div className="url-copy-row">
                          <span className="resource-label-inline">{podcastAvailableByTask[task.task_id] ? 'Podcast' : 'Audio'}</span>
                          <input
                            type="text"
                            value={`${apiBaseUrl}/api/tasks/${task.task_id}/${podcastAvailableByTask[task.task_id] ? 'podcast' : 'audio'}`}
                            readOnly
                            className="url-input-enhanced"
                          />
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/${podcastAvailableByTask[task.task_id] ? 'podcast' : 'audio'}`);
                              alert(`${podcastAvailableByTask[task.task_id] ? 'Podcast' : 'Audio'} URL copied!`);
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>

                        {/* Transcript */}
                        <div className="url-copy-row">
                          <span className="resource-label-inline">Transcript</span>
                          <input
                            type="text"
                            value={`${apiBaseUrl}/api/tasks/${task.task_id}/transcripts/markdown`}
                            readOnly
                            className="url-input-enhanced"
                          />
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/transcripts/markdown`);
                              alert('Transcript URL copied!');
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>

                        {/* VTT (hide for podcast-only) */}
                        {(() => {
                          const tt = (
                            (task.task_type || (task.state as any)?.task_type || '')
                              .toLowerCase()
                          );
                          const isPod = ["podcast", "both"].includes(tt) ||
                            Boolean(podcastAvailableByTask[task.task_id]);
                          return !isPod;
                        })() && (
                        <div className="url-copy-row">
                          <span className="resource-label-inline">VTT</span>
                          <input
                            type="text"
                            value={`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/vtt`}
                            readOnly
                            className="url-input-enhanced"
                          />
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/vtt`);
                              alert('VTT URL copied!');
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>
                        )}

                        {/* SRT (hide for podcast-only) */}
                        {(() => {
                          const tt = (
                            (task.task_type || (task.state as any)?.task_type || '')
                              .toLowerCase()
                          );
                          const isPod = ["podcast", "both"].includes(tt) ||
                            Boolean(podcastAvailableByTask[task.task_id]);
                          return !isPod;
                        })() && (
                        <div className="url-copy-row">
                          <span className="resource-label-inline">SRT</span>
                          <input
                            type="text"
                            value={`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/srt`}
                            readOnly
                            className="url-input-enhanced"
                          />
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`${apiBaseUrl}/api/tasks/${task.task_id}/subtitles/srt`);
                              alert('SRT URL copied!');
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>
                        )}

                        

                        
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
              
              <div className="task-actions">
                {task.status === 'completed' && deriveTaskOutputs(task).video && (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      previewTask(task, 'video');
                    }}
                    className="preview-button"
                    title="Open preview"
                    type="button"
                  >
                    ▶️ Watch
                  </button>
                )}
                {task.status === 'completed' && (
                  deriveTaskOutputs(task).podcast || (deriveTaskOutputs(task).video)
                ) && (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      previewTask(task, 'audio');
                    }}
                    className="preview-button"
                    title="Open preview"
                    type="button"
                  >
                    🎧 Listen
                  </button>
                )}
                {(task.status === 'queued' || task.status === 'processing') && (
                  <button
                    onClick={() => cancelTask(task.task_id)}
                    className="cancel-button"
                  >
                    Cancel
                  </button>
                )}
                <button
                  onClick={() => deleteTask(task.task_id)}
                  className="delete-button"
                  title="Delete task"
                  type="button"
                  aria-label="Delete task"
                >
                  <svg
                    className="icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path
                      d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.343.052.682.106 1.018.162m-1.018-.162L19.5 19.5A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 19.5L5.77 5.79m13.458 0a48.108 48.108 0 0 0-3.478-.397m-12 .559c.336-.056.675-.11 1.018-.162m0 0A48.11 48.11 0 0 1 9.25 5.25m5.5 0a48.11 48.11 0 0 1 3.482.342m-8.982-.342V4.5A1.5 1.5 0 0 1 10.25 3h3.5A1.5 1.5 0 0 1 15.25 4.5v.75m-8.982 0a48.667 48.667 0 0 0-3.538.397"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>

            </div>
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
      {selectedTaskForPreview && (
        <div 
          className="video-preview-modal" 
          data-mode={modalPreviewMode}
          onClick={closePreview}
          role="dialog"
          aria-modal="true"
        >
          <div 
            className="video-preview-content" 
            data-mode={modalPreviewMode}
            onClick={(e) => e.stopPropagation()}
            role="document"
          >
            {/* Modal header bar: filename + type + optional mode toggle */}
            {(() => {
              const tt = (selectedTaskForPreview.task_type || (selectedTaskForPreview.state as any)?.task_type || '').toLowerCase();
              const hasVideo = !!videoAvailableByTask[selectedTaskForPreview.task_id];
              const hasPodcast = !!podcastAvailableByTask[selectedTaskForPreview.task_id];
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
            })()}

            {/* Preview content: video or podcast depending on mode/availability */}
            <div className="video-player-container">
              {(() => {
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
                      <PodcastPlayer src={audioUrl} transcriptMarkdown={transcriptMdByTask[selectedTaskForPreview.task_id]} />
                    ) : (
                      <AudioPlayer src={audioUrl} vttUrl={vttUrl} />
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskMonitor;

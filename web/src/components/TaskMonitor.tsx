import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './TaskMonitor.scss';
import PodcastTranscript from './PodcastTranscript';
import { getStepLabel } from '../utils/stepLabels';

// Types for task monitoring
interface TaskState {
  status: string;
  current_step: string;
  filename?: string;
  voice_language: string;
  subtitle_language?: string;
  video_resolution?: string;
  generate_avatar: boolean;
  generate_subtitles: boolean;
  generate_podcast?: boolean;
  generate_video?: boolean;
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
  kwargs: {
    file_id: string;
    file_ext: string;
    filename?: string;
    voice_language: string;
    subtitle_language?: string;
    video_resolution?: string;
    generate_avatar: boolean;
    generate_subtitles: boolean;
    generate_video?: boolean;
    generate_podcast?: boolean;
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
  const [subtitleAvailable, setSubtitleAvailable] = useState<boolean>(false);
  const [subtitleObjectUrl, setSubtitleObjectUrl] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const modalVideoRef = React.useRef<HTMLVideoElement | null>(null);
  const lastSubtitleFileIdRef = React.useRef<string | null>(null);
  const [removingTaskIds, setRemovingTaskIds] = useState<Set<string>>(new Set());
  const [expandedDownloads, setExpandedDownloads] = useState<Set<string>>(new Set());
  const [audioPreviewTaskId, setAudioPreviewTaskId] = useState<string | null>(null);
  const [podcastAvailableByTask, setPodcastAvailableByTask] = useState<Record<string, boolean>>({});
  const [videoAvailableByTask, setVideoAvailableByTask] = useState<Record<string, boolean>>({});
  const [previewModeByTask, setPreviewModeByTask] = useState<Record<string, 'video' | 'audio'>>({});
  const [transcriptMdByTask, setTranscriptMdByTask] = useState<Record<string, string>>({});
  type Cue = { start: number; end: number; text: string }; // eslint-disable-line @typescript-eslint/no-unused-vars
  const [audioCues, setAudioCues] = useState<Cue[]>([]); // eslint-disable-line @typescript-eslint/no-unused-vars
  const [activeAudioCueIdx, setActiveAudioCueIdx] = useState<number | null>(null);
  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  const audioTranscriptRef = React.useRef<HTMLDivElement | null>(null);
  const inlineVideoRefs = React.useRef<Record<string, HTMLVideoElement | null>>({});
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
      const hasSubs = items.some((it: any) => it?.type === 'subtitles');
      setPodcastAvailableByTask((m) => ({ ...m, [taskId]: !!hasPodcast }));
      setVideoAvailableByTask((m) => ({ ...m, [taskId]: !!hasVideo }));
      setSubtitleAvailable(!!hasSubs);
      // Fetch conversation transcript for podcast tasks
      const t = tasks.find((x) => x.task_id === taskId);
      const isPodcast = hasPodcast || ((t?.state?.generate_podcast ?? t?.kwargs?.generate_podcast) === true);
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

  // Derive task outputs (video/podcast) from state, kwargs, availability, or step name
  const deriveTaskOutputs = (task: Task): { video: boolean; podcast: boolean } => {
    // Prefer explicit task_type when present
    const taskType = (task.state as any)?.task_type as string | undefined;
    if (taskType === 'video') return { video: true, podcast: false };
    if (taskType === 'podcast') return { video: false, podcast: true };
    if (taskType === 'both') return { video: true, podcast: true };
    const sv = task.state?.generate_video;
    const sp = task.state?.generate_podcast;
    const kv = task.kwargs?.generate_video;
    const kp = task.kwargs?.generate_podcast;
    let video: boolean | undefined = sv ?? kv;
    let podcast: boolean | undefined = sp ?? kp;
    // Fall back to what we've discovered from downloads
    if (video === undefined) video = !!videoAvailableByTask[task.task_id];
    if (podcast === undefined) podcast = !!podcastAvailableByTask[task.task_id];
    // Heuristic: infer from current step naming when still unknown
    if (video === undefined || podcast === undefined) {
      const step = (task.state?.current_step || '').toLowerCase();
      if ((video === undefined) && /compose_video|generate_pdf_video|compose final video|composing final video/.test(step)) video = true;
      if ((podcast === undefined) && /podcast/.test(step)) podcast = true;
    }
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
      setPreviewModeByTask((m) => ({ ...m, [taskId]: outs.video ? 'video' : 'audio' }));
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
          const hasSubs = items.some((it: any) => it?.type === 'subtitles');
          setPodcastAvailableByTask((m) => ({ ...m, [taskId]: !!hasPodcast }));
          setVideoAvailableByTask((m) => ({ ...m, [taskId]: !!hasVideo }));
          setSubtitleAvailable(!!hasSubs);
          // Set default inline preview mode: prefer video when available
          setPreviewModeByTask((m) => ({ ...m, [taskId]: hasVideo ? 'video' : 'audio' }));
          // Auto-open audio inline preview for podcast-only tasks once completed
          const t = tasks.find((x) => x.task_id === taskId);
          if (t && t.status === 'completed' && (!hasVideo || hasPodcast)) {
            setAudioPreviewTaskId(taskId);
          }
          // Fetch conversation transcript for podcast tasks
          const isPodcast = hasPodcast || ((tasks.find((x)=>x.task_id===taskId)?.state?.generate_podcast ?? tasks.find((x)=>x.task_id===taskId)?.kwargs?.generate_podcast) === true);
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
        }
      } catch {
        /* ignore */
      }
    })();
  };

  

  // Sync active cue with audio time (RAF-driven for smoothness)
  useEffect(() => {
    const audio = audioRef.current;
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

  // Health check: detect when Redis/queue is unavailable and show banner
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const resp = await fetch(`${apiBaseUrl}/api/health`, { headers: { Accept: 'application/json' } });
        if (!resp.ok) throw new Error('health not ok');
        const data = await resp.json();
        if (!cancelled) setQueueUnavailable(!(data?.redis?.ok === true));
      } catch {
        if (!cancelled) setQueueUnavailable(true);
      }
    };
    check();
    const id = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(id); };
  }, [apiBaseUrl]);

  // Load subtitles when task is selected for preview (GET -> Blob URL)
  useEffect(() => {
    const checkSubtitles = async () => {
      if (!selectedTaskForPreview) {
        setSubtitleAvailable(false);
        if (subtitleObjectUrl) {
          URL.revokeObjectURL(subtitleObjectUrl);
          setSubtitleObjectUrl(null);
        }
        return;
      }

      // Prevent repeated fetches for the same file if already loaded
      if (
        lastSubtitleFileIdRef.current === selectedTaskForPreview.file_id &&
        subtitleAvailable
      ) {
        return;
      }

      const preferredLanguage = selectedTaskForPreview.kwargs?.subtitle_language || selectedTaskForPreview.state?.subtitle_language || selectedTaskForPreview.kwargs?.voice_language || 'english';
      const url = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/subtitles/vtt?language=${encodeURIComponent(preferredLanguage)}`;
      try {
        const resp = await fetch(url, { headers: { Accept: 'text/vtt,*/*' } });
        if (resp.ok) {
          const text = await resp.text();
          const blob = new Blob([text], { type: 'text/vtt' });
          const obj = URL.createObjectURL(blob);
          setSubtitleObjectUrl(obj);
          setSubtitleAvailable(true);
          lastSubtitleFileIdRef.current = selectedTaskForPreview.file_id;
          // subtitles loaded
        } else {
          console.warn('Subtitle GET failed', resp.status);
          setSubtitleObjectUrl(null);
          setSubtitleAvailable(false);
        }
      } catch (e) {
        console.warn('Subtitle GET error', e);
        if (subtitleObjectUrl) URL.revokeObjectURL(subtitleObjectUrl);
        setSubtitleObjectUrl(null);
        setSubtitleAvailable(false);
      }
    };
    
    checkSubtitles();
  }, [selectedTaskForPreview, apiBaseUrl, subtitleAvailable, subtitleObjectUrl]);

  // Prefetch video, audio/podcast, and subtitles when task is selected for preview
  useEffect(() => {
    if (!selectedTaskForPreview) return;

    // Create an array to hold all the link elements for cleanup
    const linkElements: HTMLLinkElement[] = [];

    try {
      // Prefetch video (best-effort; may not exist if podcast-only)
      const videoUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/video`;
      const videoLink = document.createElement('link');
      videoLink.rel = 'prefetch';
      videoLink.href = videoUrl;
      videoLink.as = 'video';
      document.head.appendChild(videoLink);
      linkElements.push(videoLink);

      // Prefetch audio or podcast
      const isPodcast = !!podcastAvailableByTask[selectedTaskForPreview.task_id];
      const audioUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/${isPodcast ? 'podcast' : 'audio'}`;
      const audioLink = document.createElement('link');
      audioLink.rel = 'prefetch';
      audioLink.href = audioUrl;
      audioLink.as = 'audio';
      document.head.appendChild(audioLink);
      linkElements.push(audioLink);

      // Prefetch subtitles only when not a podcast
      if (!isPodcast) {
        const preferredLanguage = selectedTaskForPreview.kwargs?.subtitle_language || selectedTaskForPreview.state?.subtitle_language || selectedTaskForPreview.kwargs?.voice_language || 'english';
        const subtitleUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/subtitles/vtt?language=${encodeURIComponent(preferredLanguage)}`;
        const subtitleLink = document.createElement('link');
        subtitleLink.rel = 'prefetch';
        subtitleLink.href = subtitleUrl;
        subtitleLink.as = 'track';
        document.head.appendChild(subtitleLink);
        linkElements.push(subtitleLink);
      }
    } catch (error) {
      console.warn('Failed to create prefetch links:', error);
    }

    // Clean up links when component unmounts or selectedTaskForPreview changes
    return () => {
      linkElements.forEach(link => {
        if (document.head.contains(link)) {
          document.head.removeChild(link);
        }
      });
    };
  }, [selectedTaskForPreview, apiBaseUrl, podcastAvailableByTask]);

  // Do not force subtitles to display in preview; user can enable via player controls


  // No imperative src assignment; <video src> handles local and S3 redirect

  // Cleanup subtitle Blob URL on unmount/changes
  useEffect(() => {
    return () => {
      if (subtitleObjectUrl) URL.revokeObjectURL(subtitleObjectUrl);
    };
  }, [subtitleObjectUrl]);

  // Always set first text track to showing when present
  useEffect(() => {
    if (!selectedTaskForPreview || !modalVideoRef.current) return;
    try {
      const tracks = modalVideoRef.current.textTracks;
      if (tracks && tracks.length > 0) {
        tracks[0].mode = 'showing';
      }
    } catch {}
  }, [selectedTaskForPreview, subtitleObjectUrl, subtitleAvailable]);

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

  // Fetch tasks and statistics
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

      const tasksResponse = await axios.get(`${apiBaseUrl}/api/tasks?${params}`);
      // Keep only real tasks with valid task_id (exclude synthetic state_* entries)
      const realTasks = (tasksResponse.data.tasks || []).filter((t: any) => typeof t?.task_id === 'string' && !t.task_id.startsWith('state_'));
      setTasks(realTasks);

      // Fetch statistics
      const statsResponse = await axios.get(`${apiBaseUrl}/api/tasks/statistics`);
      setStatistics(statsResponse.data);
    } catch (err) {
      setError('Failed to fetch task data');
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, currentPage, statusFilter, tasksPerPage]);

  // Lightweight polling while tasks are running to keep UI in sync
  useEffect(() => {
    const hasActive = tasks.some(t => t.status === 'processing' || t.status === 'queued');
    if (!hasActive) return; // no polling when idle

    const id = setInterval(() => {
      fetchTasks();
    }, 2500);

    return () => clearInterval(id);
  }, [tasks, fetchTasks]);

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
    if (!query.trim()) {
      fetchTasks();
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${apiBaseUrl}/api/tasks/search?query=${encodeURIComponent(query)}`);
      setTasks(response.data.tasks);
    } catch (err) {
      setError('Failed to search tasks');
      console.error('Error searching tasks:', err);
    } finally {
      setLoading(false);
    }
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
  const previewTask = (task: Task) => {
    console.log('Preview task called with:', task);
    // Only show preview for completed tasks that have videos
    if (task.status === 'completed') {
      setSelectedTaskForPreview(task);
    } else {
      alert('Video preview is only available for completed tasks.');
    }
  };

  // Close preview
  const closePreview = () => {
    setSelectedTaskForPreview(null);
  };

  // ESC key handler for closing modal
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && selectedTaskForPreview) {
        event.preventDefault();
        closePreview();
      }
    };

    if (selectedTaskForPreview) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset'; // Restore scrolling
    };
  }, [selectedTaskForPreview]);

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
                  const voiceLang = task.kwargs?.voice_language || task.state?.voice_language || 'english';
                  const subtitleLang = task.kwargs?.subtitle_language || task.state?.subtitle_language || voiceLang;
                  const videoRes = task.kwargs?.video_resolution || task.state?.video_resolution || 'hd';
                  const { video: isVideoTask, podcast: isPodcastTask } = deriveTaskOutputs(task);
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
                        <span className="chip">Subs: {getLanguageDisplayName(subtitleLang)}</span>
                        <span className="chip">{getVideoResolutionDisplayName(videoRes)}</span>
                      </div>

                      {/* Current step + progress for non-completed */}
                      {task.status !== 'completed' && task.state && (
                        <div className="step-progress">
                          <div className="step-line" role="status" aria-live="polite">{formatStepNameWithLanguages(task.state.current_step, voiceLang, subtitleLang)}</div>
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
                        {/* Inline Preview Toggle (show Watch when this is a video task) */}
                        {deriveTaskOutputs(task).video && previewModeByTask[task.task_id] !== 'video' && (
                          <div className="preview-toggle">
                            <button
                              type="button"
                              className={`toggle-btn ${previewModeByTask[task.task_id] === 'video' ? 'active' : ''}`}
                              onClick={() => {
                                setPreviewModeByTask((m) => ({ ...m, [task.task_id]: 'video' }));
                                setAudioPreviewTaskId(null);
                              }}
                            >
                              ▶️ Watch
                            </button>
                          </div>
                        )}
                        {/* Inline Video Preview (when selected) */}
                        {videoAvailableByTask[task.task_id] && previewModeByTask[task.task_id] === 'video' && (
                          <div className="video-preview-block">
                            <div className="media-wrapper">
                              <video
                                ref={(el) => { inlineVideoRefs.current[task.task_id] = el; }}
                                controls
                                playsInline
                                preload="metadata"
                                crossOrigin="anonymous"
                                src={`${apiBaseUrl}/api/tasks/${task.task_id}/video`}
                                style={{ width: '100%', borderRadius: 8 }}
                                aria-label={`Video preview for task ${task.task_id}`}
                              />
                            </div>
                            <div className="video-preview-actions">
                              <button
                                type="button"
                                className="link-button"
                                title="Open full view"
                                onClick={(e) => { e.preventDefault(); e.stopPropagation(); previewTask(task); }}
                              >
                                Open Full View
                              </button>
                            </div>
                          </div>
                        )}
                        {/* Inline Audio Preview with captions / conversation */}
                        {previewModeByTask[task.task_id] === 'audio' && (
                          <div id={`audio-preview-${task.task_id}`} className="audio-preview-block">
                            <div className="media-wrapper">
                              <audio
                                ref={audioRef}
                                controls
                                preload="auto"
                                src={`${apiBaseUrl}/api/tasks/${task.task_id}/${podcastAvailableByTask[task.task_id] ? 'podcast' : 'audio'}`}
                                crossOrigin="anonymous"
                                aria-label={`Audio narration for task ${task.task_id}`}
                              />
                            </div>
                            {/* Slides/video tasks: show VTT-synced transcript */}
                            {!(((task.state?.generate_podcast ?? task.kwargs?.generate_podcast) === true) || podcastAvailableByTask[task.task_id]) && audioCues.length > 0 && (
                              <div className="audio-transcript-pane" ref={audioTranscriptRef}>
                                {audioCues.map((cue, idx) => (
                                  <div
                                    key={idx}
                                    className={`cue ${activeAudioCueIdx === idx ? 'active' : ''}`}
                                    onClick={() => {
                                      const a = audioRef.current;
                                      if (!a) return;
                                      const target = Math.max(0, Math.min(isFinite(a.duration) ? a.duration - 0.05 : cue.start + 0.01, cue.start + 0.01));
                                      const doPlay = () => a.play().catch(() => {});
                                      const doSeek = () => {
                                        try {
                                          if ((a as any).fastSeek) {
                                            (a as any).fastSeek(target);
                                          } else {
                                            a.currentTime = target;
                                          }
                                          const onSeeked = () => { a.removeEventListener('seeked', onSeeked); doPlay(); };
                                          a.addEventListener('seeked', onSeeked, { once: true });
                                        } catch {
                                          a.currentTime = target;
                                          doPlay();
                                        }
                                      };
                                      if (a.readyState >= 1) doSeek();
                                      else a.addEventListener('loadedmetadata', doSeek, { once: true });
                                    }}
                                    role="button"
                                    tabIndex={0}
                                  >
                                    <div className="t-time">{Math.floor(cue.start / 60)}:{String(Math.floor(cue.start % 60)).padStart(2, '0')}</div>
                                    <div className="t-text">{cue.text}</div>
                                  </div>
                                ))}
                              </div>
                            )}
                            {/* Podcast tasks: show conversation transcript synced to audio */}
                            {(((task.state?.generate_podcast ?? task.kwargs?.generate_podcast) === true) || podcastAvailableByTask[task.task_id]) && transcriptMdByTask[task.task_id] && (
                              <div style={{ marginTop: 12 }}>
                                <PodcastTranscript audioRef={audioRef} markdown={transcriptMdByTask[task.task_id]} />
                              </div>
                            )}
                          </div>
                        )}
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
                        {!(((task.state?.generate_podcast ?? task.kwargs?.generate_podcast) === true) || podcastAvailableByTask[task.task_id]) && (
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
                        {!(((task.state?.generate_podcast ?? task.kwargs?.generate_podcast) === true) || podcastAvailableByTask[task.task_id]) && (
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
                      setExpandedDownloads((prev) => new Set(prev).add(task.task_id));
                      prefetchTaskDownloads(task.task_id).finally(() => {
                        setPreviewModeByTask((m) => ({ ...m, [task.task_id]: 'video' }));
                        setAudioPreviewTaskId(null);
                      });
                    }}
                    className="preview-button"
                    title="Watch inline"
                    type="button"
                  >
                    ▶️ Watch
                  </button>
                )}
                {task.status === 'completed' && deriveTaskOutputs(task).podcast && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setExpandedDownloads((prev) => new Set(prev).add(task.task_id));
                        prefetchTaskDownloads(task.task_id).finally(() => {
                          setPreviewModeByTask((m) => ({ ...m, [task.task_id]: 'audio' }));
                          setAudioPreviewTaskId(task.task_id);
                        });
                      }}
                      className="preview-button"
                      title="Listen inline"
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

      {/* Video Preview Modal */}
      {selectedTaskForPreview && (
        <div 
          className="video-preview-modal" 
          onClick={closePreview}
          role="dialog"
          aria-modal="true"
        >
          <div 
            className="video-preview-content" 
            onClick={(e) => e.stopPropagation()}
            role="document"
          >
            {/* Close button */}
            <button 
              onClick={closePreview} 
              className="video-close-button"
              title="Close Preview"
              type="button"
              aria-label="Close video preview"
            >
              ✕
            </button>
            
            {/* Video Player */}
            <div className="video-player-container">
              {(() => {
                const videoUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/video`;
                const voiceLanguage = selectedTaskForPreview.kwargs?.voice_language || selectedTaskForPreview.state?.voice_language || 'english';
                const subtitleLanguage = selectedTaskForPreview.kwargs?.subtitle_language || selectedTaskForPreview.state?.subtitle_language || voiceLanguage;
                const subtitleUrl = `${apiBaseUrl}/api/tasks/${selectedTaskForPreview.task_id}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
                
                
                
                return (
                  <div className="modal-preview-stack">
                    <div className="modal-video-wrapper">
                    <video 
                      key={selectedTaskForPreview.file_id}
                      ref={modalVideoRef}
                      controls 
                      autoPlay
                      playsInline
                      preload="auto"
                      className="video-player"
                      crossOrigin="anonymous"
                      // Avoid forcing CORS preflight for OSS/S3 video playback
                      // by not setting crossOrigin; let the browser fetch normally
                      src={videoUrl}
                      onLoadStart={() => setVideoError(null)}
                      
                      onError={(e) => {
                        console.error('Video loading error:', e);
                        setVideoError('Failed to load video');
                        
                      }}
                      onPlay={() => void 0}
                      onPause={() => void 0}
                      onLoadedMetadata={(e) => {
                        const video = e.currentTarget as HTMLVideoElement;
                        // Attempt playback; browsers may require interaction if audio is unmuted
                        video.play().catch(() => {/* Autoplay may be blocked until user interaction */});
                      }}
                    >
                      {/* Always include track; browser or Blob can load it */}
                      <track
                        kind="subtitles"
                        src={subtitleObjectUrl || subtitleUrl}
                        srcLang={subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : 
                                 subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : 
                                 subtitleLanguage === 'japanese' ? 'ja' : 
                                 subtitleLanguage === 'korean' ? 'ko' : 
                                 subtitleLanguage === 'thai' ? 'th' : 'en'}
                        label={getLanguageDisplayName(subtitleLanguage)}
                        default
                        onError={(e) => console.error('Subtitle track loading error:', e)}
                      />
                      Your browser does not support the video tag.
                    </video>
                    
                    {/* File type information in preview */}
                    <div className="preview-file-info">
                      <div className={`file-type-badge ${isPdfFile(selectedTaskForPreview.kwargs?.file_ext) ? 'pdf' : 'ppt'}`}>
                        {getFileTypeDisplayName(selectedTaskForPreview.kwargs?.file_ext)}
                      </div>
                    </div>
                    
                    {/* Video loading and error states */}
                    {/* Loading overlay removed per request */}
                    
                    {videoError && (
                      <div className="video-status-overlay error">
                        <p>❌ {videoError}</p>
                        <button 
                          onClick={() => {
                            setVideoError(null);
                            // reload video without tracking loading state
                            // Force video reload by changing src slightly
                            const video = document.querySelector('.video-player') as HTMLVideoElement;
                            if (video) {
                              video.load();
                              video.play().catch(err => console.log('Play failed:', err));
                            }
                          }} 
                          className="retry-button"
                        >
                          Retry
                        </button>
                      </div>
                    )}
                    
                    {/* Subtitle indicator removed per request */}
                    </div>
                    {/* Audio preview is available in task card via Listen; not shown in modal */}
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

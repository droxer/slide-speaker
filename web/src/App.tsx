import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.scss';
// Ultra-flat design styles
import './styles/ultra-flat-overrides.scss';
import './styles/subtle-material-overrides.scss';
import TaskMonitor from './components/TaskMonitor';

// Constants for local storage keys
const LOCAL_STORAGE_KEYS = {
  TASK_STATE: 'slidespeaker_task_state',
  FILE_ID: 'slidespeaker_file_id',
  TASK_ID: 'slidespeaker_task_id',
  STATUS: 'slidespeaker_status',
  PROCESSING_DETAILS: 'slidespeaker_processing_details',
  LATEST_TASK_TIMESTAMP: 'slidespeaker_latest_task_timestamp',
  FILE_TYPE: 'slidespeaker_file_type' // Add file type tracking for PDF vs PPT handling
};

// API configuration – prefer same-origin when served over HTTPS to avoid mixed-content blocks
const API_BASE_URL = (() => {
  const env = process.env.REACT_APP_API_BASE_URL;
  if (env !== undefined) return env;
  const { protocol, hostname } = window.location;
  if (protocol === 'https:') {
    // Use same-origin '/api' paths; rely on reverse proxy in production
    return '';
  }
  // Local dev over HTTP
  return `${protocol}//${hostname}:8000`;
})();

// UI Theme key
const THEME_STORAGE_KEY = 'slidespeaker_ui_theme'; // 'flat' | 'classic' | 'material'

// Define TypeScript interfaces
interface StepDetails {
  status: string;
  data?: any;
}

interface ProcessingError {
  step: string;
  error: string;
  timestamp: string;
}

interface ProcessingDetails {
  status: string;
  progress: number;
  current_step: string;
  steps: Record<string, StepDetails>;
  errors: ProcessingError[];
  filename?: string;
  voice_language?: string;
  subtitle_language?: string;
  created_at: string;
  updated_at: string;
}

type AppStatus = 'idle' | 'uploading' | 'processing' | 'completed' | 'error' | 'cancelled';

// Local storage utility functions
const localStorageUtils = {
  saveTaskState: (state: {
    fileId: string | null;
    taskId: string | null;
    status: AppStatus;
    processingDetails: ProcessingDetails | null;
    voiceLanguage: string;
    subtitleLanguage: string;
    generateAvatar: boolean;
    generateSubtitles: boolean;
    fileName: string | null; // Add fileName to track file type
  }) => {
    try {
      const stateToSave = {
        ...state,
        timestamp: new Date().toISOString()
      };
      localStorage.setItem(LOCAL_STORAGE_KEYS.TASK_STATE, JSON.stringify(stateToSave));
      localStorage.setItem(LOCAL_STORAGE_KEYS.LATEST_TASK_TIMESTAMP, new Date().toISOString());
      // Save file type information
      if (state.fileName) {
        const fileType = state.fileName.toLowerCase().split('.').pop() || '';
        localStorage.setItem(LOCAL_STORAGE_KEYS.FILE_TYPE, fileType);
      }
    } catch (error) {
      console.warn('Failed to save task state to local storage:', error);
    }
  },

  loadTaskState: () => {
    try {
      const savedState = localStorage.getItem(LOCAL_STORAGE_KEYS.TASK_STATE);
      if (savedState) {
        const parsed = JSON.parse(savedState);
        // Validate the timestamp to ensure it's recent (within 24 hours)
        const timestamp = new Date(parsed.timestamp);
        const now = new Date();
        const hoursDiff = (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60);
        
        if (hoursDiff < 24) {
          // Load file type information
          const fileType = localStorage.getItem(LOCAL_STORAGE_KEYS.FILE_TYPE);
          return {
            ...parsed,
            fileType
          };
        } else {
          // Clean up old data
          localStorageUtils.clearTaskState();
          return null;
        }
      }
      return null;
    } catch (error) {
      console.warn('Failed to load task state from local storage:', error);
      return null;
    }
  },

  clearTaskState: () => {
    try {
      Object.values(LOCAL_STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key);
      });
    } catch (error) {
      console.warn('Failed to clear task state from local storage:', error);
    }
  },

  saveFileId: (fileId: string) => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEYS.FILE_ID, fileId);
    } catch (error) {
      console.warn('Failed to save file ID to local storage:', error);
    }
  },

  loadFileId: (): string | null => {
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEYS.FILE_ID);
    } catch (error) {
      console.warn('Failed to load file ID from local storage:', error);
      return null;
    }
  },

  saveTaskId: (taskId: string) => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEYS.TASK_ID, taskId);
    } catch (error) {
      console.warn('Failed to save task ID to local storage:', error);
    }
  },

  loadTaskId: (): string | null => {
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEYS.TASK_ID);
    } catch (error) {
      console.warn('Failed to load task ID from local storage:', error);
      return null;
    }
  }
};

function App() {
  // UI theme: 'classic' (Modern, default), 'flat', or 'material'
  const [uiTheme, setUiTheme] = useState<'flat' | 'classic' | 'material'>(() => {
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === 'classic' || saved === 'flat' || saved === 'material') return saved as 'flat' | 'classic' | 'material';
    } catch {}
    return 'classic';
  });

  // Apply/remove ultra-flat class based on theme
  useEffect(() => {
    const isFlat = uiTheme === 'flat';
    const isMaterial = uiTheme === 'material';
    document.body.classList.toggle('ultra-flat', isFlat);
    document.body.classList.toggle('subtle-material', isMaterial);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, uiTheme);
    } catch {}
  }, [uiTheme]);

  const [file, setFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState<string | null>(null); // Track file type for PDF vs PPT handling
  const [uploading, setUploading] = useState<boolean>(false);
  const [fileId, setFileId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [processingDetails, setProcessingDetails] = useState<ProcessingDetails | null>(null);
  const [processingTranscriptMd, setProcessingTranscriptMd] = useState<string | null>(null);
  // Using final audio endpoint; no need to fetch per-track list
  const [voiceLanguage, setVoiceLanguage] = useState<string>('english');
  const [subtitleLanguage, setSubtitleLanguage] = useState<string>('english');
  const [videoResolution, setVideoResolution] = useState<string>('hd'); // hd as default
  const [generateAvatar, setGenerateAvatar] = useState<boolean>(false);
  const [generateSubtitles, setGenerateSubtitles] = useState<boolean>(true);
  const [isResumingTask, setIsResumingTask] = useState<boolean>(false);
  const [showTaskMonitor, setShowTaskMonitor] = useState<boolean>(false);
  const [uploadMode, setUploadMode] = useState<'slides' | 'pdf'>('slides');
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  type Cue = { start: number; end: number; text: string };
  const [audioCues, setAudioCues] = useState<Cue[]>([]);
  const [activeAudioCueIdx, setActiveAudioCueIdx] = useState<number | null>(null);
  const audioTranscriptRef = useRef<HTMLDivElement>(null);
  const [showAudioTranscript, setShowAudioTranscript] = useState<boolean>(false);
  const [audioCuesLoaded, setAudioCuesLoaded] = useState<boolean>(false);
  // Completed banner visibility (dismissible)
  const [showCompletedBanner, setShowCompletedBanner] = useState<boolean>(() => {
    try { return localStorage.getItem('ss_show_completed_banner') !== '0'; } catch { return true; }
  });
  const COMPLETED_MEDIA_KEY = 'slidespeaker_completed_media';
  const [completedMedia, setCompletedMedia] = useState<'video' | 'audio'>(() => {
    try {
      const stored = localStorage.getItem(COMPLETED_MEDIA_KEY);
      if (stored === 'video' || stored === 'audio') return stored as 'video' | 'audio';
    } catch {}
    return 'video';
  });
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const ext = selectedFile.name.toLowerCase().split('.').pop();
      const isPdf = ext === 'pdf';
      const isSlide = ext === 'pptx' || ext === 'ppt';
      if (uploadMode === 'pdf' && !isPdf) {
        alert('Please select a PDF file for PDF processing.');
        return;
      }
      if (uploadMode === 'slides' && !isSlide) {
        alert('Please select a PPTX or PPT file for Slides processing.');
        return;
      }
      if (ext && (isPdf || isSlide)) {
        setFile(selectedFile);
        setFileType(ext);
      } else {
        alert('Please select a PDF or PowerPoint file');
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setStatus('uploading');
    
    try {
      // Read file as array buffer for base64 encoding using FileReader for better performance
      const base64File = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          // Remove the data URL prefix (e.g., "data:application/pdf;base64,")
          const base64Data = result.split(',')[1];
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      
      // Send as JSON
      const response = await axios.post('/api/upload', 
        {
          filename: file.name,
          file_data: base64File,
          voice_language: voiceLanguage,
          subtitle_language: subtitleLanguage,
          video_resolution: videoResolution,
          generate_avatar: generateAvatar,
          generate_subtitles: generateSubtitles
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              setProgress(percentCompleted);
            }
          },
        }
      );
      
      setFileId(response.data.file_id);
      setTaskId(response.data.task_id);
      setStatus('processing');
      setProgress(0);
      
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
      setUploading(false);
      setStatus('idle');
    }
  };

  const handleStopProcessing = async () => {
    if (!taskId) return;
    
    try {
      const response = await axios.post<{ message: string }>(`/api/task/${taskId}/cancel`);
      console.log('Stop processing response:', response.data);
      
      // Instead of immediately setting to idle, let the polling detect the cancelled state
      // This ensures frontend and backend stay in sync
      setStatus('processing'); // Keep showing processing until backend confirms cancelled
      alert('Processing is being stopped... Please wait a moment.');
    } catch (error) {
      console.error('Stop processing error:', error);
      alert('Failed to stop processing. The task may have already completed or failed.');
    }
  };


  const resetForm = () => {
    setFile(null);
    setFileType(null);
    setFileId(null);
    setTaskId(null);
    setStatus('idle');
    setUploading(false);
    setProgress(0);
    setProcessingDetails(null);
    // Keep the current subtitle language selection
    setGenerateAvatar(false);
    setGenerateSubtitles(true);
    if (videoRef.current) {
      videoRef.current.src = '';
    }
    
    // Clear local storage
    localStorageUtils.clearTaskState();
  };

  // Load saved task state on component mount
  useEffect(() => {
    const loadSavedState = async () => {
      const savedState = localStorageUtils.loadTaskState();
      if (savedState) {
        setIsResumingTask(true);
        
        // Restore the saved state
        setFileId(savedState.fileId);
        setTaskId(savedState.taskId);
        setStatus(savedState.status);
        setProgress(savedState.processingDetails?.progress || 0);
        setProcessingDetails(savedState.processingDetails);
        setVoiceLanguage(savedState.voiceLanguage);
        setSubtitleLanguage(savedState.subtitleLanguage);
        setGenerateAvatar(savedState.generateAvatar);
        setGenerateSubtitles(savedState.generateSubtitles);
        setFileType(savedState.fileType || null);
        
        console.log('Resuming task from local storage:', {
          fileId: savedState.fileId,
          taskId: savedState.taskId,
          status: savedState.status,
          fileType: savedState.fileType
        });
        
        setIsResumingTask(false);
      }
    };

    loadSavedState();
  }, []);

  // Fetch transcript markdown during processing for preview
  useEffect(() => {
    const fetchTranscript = async () => {
      if (!taskId || status !== 'processing') return;
      try {
        const resp = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/transcripts/markdown`, { headers: { Accept: 'text/markdown' } });
        if (resp.ok) {
          const text = await resp.text();
          setProcessingTranscriptMd(text);
        }
      } catch {
        /* ignore */
      }
    };
    fetchTranscript();
  }, [taskId, status]);

  // Fetch VTT and build cues for Completed view audio transcript when user plays audio
  useEffect(() => {
    const loadVtt = async () => {
      if (status !== 'completed' || !taskId || !showAudioTranscript || audioCuesLoaded) return;
      try {
        const lang = (processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english');
        const resp = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(lang)}`, { headers: { Accept: 'text/vtt,*/*' } });
        if (!resp.ok) return;
        const text = await resp.text();
        // Parse WebVTT into cues
        const lines = text.split(/\r?\n/);
        const parsed: Cue[] = [];
        let i = 0;
        const timeRe = /(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})\.(\d{3})/;
        while (i < lines.length) {
          const line = lines[i].trim();
          if (!line) { i++; continue; }
          if (line.toUpperCase() === 'WEBVTT' || /^\d+$/.test(line)) { i++; continue; }
          const m = line.match(timeRe);
          if (m) {
            const toSec = (h: string, m: string, s: string, ms: string) => (
              parseInt(h, 10) * 3600 + parseInt(m, 10) * 60 + parseInt(s, 10) + parseInt(ms, 10) / 1000
            );
            const start = toSec(m[1], m[2], m[3], m[4]);
            const end = toSec(m[5], m[6], m[7], m[8]);
            i++;
            const textLines: string[] = [];
            while (i < lines.length && lines[i].trim() !== '') {
              textLines.push(lines[i]);
              i++;
            }
            parsed.push({ start, end, text: textLines.join('\n') });
          } else {
            i++;
          }
        }
        setAudioCues(parsed);
        setAudioCuesLoaded(true);
      } catch {
        // ignore
      }
    };
    loadVtt();
  }, [status, taskId, processingDetails, subtitleLanguage, voiceLanguage, showAudioTranscript, audioCuesLoaded]);

  // Reset transcript state when task/status changes
  useEffect(() => {
    setShowAudioTranscript(false);
    setAudioCuesLoaded(false);
    setAudioCues([]);
    setActiveAudioCueIdx(null);
    // Show banner on transition to completed unless user dismissed it previously
    if (status === 'completed') {
      try {
        const flag = localStorage.getItem('ss_show_completed_banner');
        setShowCompletedBanner(flag !== '0');
      } catch {}
    }
    // Completed view initializes subtitles from processing details only (not editable)
  }, [taskId, status]);

  // Only show transcript after user initiates audio playback
  useEffect(() => {
    if (status !== 'completed') return;
    const el = audioRef.current;
    if (!el) return;
    const onPlay = () => {
      setShowAudioTranscript(true);
      // Auto-hide banner on first media interaction
      if (showCompletedBanner) {
        setShowCompletedBanner(false);
        try { localStorage.setItem('ss_show_completed_banner', '0'); } catch {}
      }
    };
    el.addEventListener('play', onPlay);
    return () => { el.removeEventListener('play', onPlay); };
  }, [status, taskId, showCompletedBanner]);

  // Ensure video subtitles display by default in Completed view
  useEffect(() => {
    if (status !== 'completed') return;
    const v = videoRef.current;
    if (!v) return;
    try {
      const tracks = v.textTracks;
      if (tracks && tracks.length > 0) {
        tracks[0].mode = 'showing';
      }
    } catch {}
  }, [status, taskId, videoRef]);

  // Persist completed media selection
  useEffect(() => {
    try { localStorage.setItem(COMPLETED_MEDIA_KEY, completedMedia); } catch {}
  }, [completedMedia]);

  // Also hide banner when video starts playing
  useEffect(() => {
    if (status !== 'completed') return;
    const v = videoRef.current;
    if (!v) return;
    const onPlay = () => {
      if (showCompletedBanner) {
        setShowCompletedBanner(false);
        try { localStorage.setItem('ss_show_completed_banner', '0'); } catch {}
      }
    };
    v.addEventListener('play', onPlay);
    return () => { v.removeEventListener('play', onPlay); };
  }, [status, taskId, showCompletedBanner]);

  // Prevent video and audio from playing simultaneously
  useEffect(() => {
    if (status !== 'completed') return;
    
    const video = videoRef.current;
    const audio = audioRef.current;
    
    if (!video || !audio) return;
    
    const handleVideoPlay = () => {
      if (!audio.paused) {
        audio.pause();
      }
    };
    
    const handleAudioPlay = () => {
      if (!video.paused) {
        video.pause();
      }
    };
    
    video.addEventListener('play', handleVideoPlay);
    audio.addEventListener('play', handleAudioPlay);
    
    return () => {
      video.removeEventListener('play', handleVideoPlay);
      audio.removeEventListener('play', handleAudioPlay);
    };
  }, [status, taskId]);

  // Prefetch video, audio, and subtitles when task is completed
  useEffect(() => {
    if (status !== 'completed' || !taskId) return;

    // Create an array to hold all the link elements for cleanup
    const linkElements: HTMLLinkElement[] = [];

    try {
      // Prefetch video
      const videoUrl = `${API_BASE_URL}/api/tasks/${taskId}/video`;
      const videoLink = document.createElement('link');
      videoLink.rel = 'prefetch';
      videoLink.href = videoUrl;
      videoLink.as = 'video';
      document.head.appendChild(videoLink);
      linkElements.push(videoLink);

      // Prefetch audio
      const audioUrl = `${API_BASE_URL}/api/tasks/${taskId}/audio`;
      const audioLink = document.createElement('link');
      audioLink.rel = 'prefetch';
      audioLink.href = audioUrl;
      audioLink.as = 'audio';
      document.head.appendChild(audioLink);
      linkElements.push(audioLink);

      // Prefetch subtitles
      const subtitleLanguageCode = processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english';
      const subtitleUrl = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguageCode)}`;
      const subtitleLink = document.createElement('link');
      subtitleLink.rel = 'prefetch';
      subtitleLink.href = subtitleUrl;
      subtitleLink.as = 'track';
      document.head.appendChild(subtitleLink);
      linkElements.push(subtitleLink);
    } catch (error) {
      console.warn('Failed to create prefetch links:', error);
    }

    // Clean up links when component unmounts or taskId changes
    return () => {
      linkElements.forEach(link => {
        if (document.head.contains(link)) {
          document.head.removeChild(link);
        }
      });
    };
  }, [status, taskId, processingDetails, subtitleLanguage, voiceLanguage]);

  // Sync active cue with audio time
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || audioCues.length === 0) return;
    const onTime = () => {
      const t = audio.currentTime;
      let idx: number | null = null;
      for (let j = 0; j < audioCues.length; j++) {
        const c = audioCues[j];
        if (t >= c.start && t <= c.end) { idx = j; break; }
      }
      setActiveAudioCueIdx(idx);
    };
    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('seeked', onTime);
    onTime();
    return () => {
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('seeked', onTime);
    };
  }, [audioCues]);

  // Auto-scroll transcript to active cue
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
      const delta = eRect.top - cRect.top - cRect.height / 2;
      container.scrollTop += delta;
    }
  }, [activeAudioCueIdx]);

  // No-op: final audio is served via a single endpoint

  // Save task state to local storage whenever relevant state changes
  useEffect(() => {
    if (status !== 'idle' && !isResumingTask) {
      localStorageUtils.saveTaskState({
        fileId,
        taskId,
        status,
        processingDetails,
        voiceLanguage,
        subtitleLanguage,
        generateAvatar,
        generateSubtitles,
        fileName: file?.name || null
      });
    }
  }, [
    fileId,
    taskId,
    status,
    processingDetails,
    voiceLanguage,
    subtitleLanguage,
    generateAvatar,
    generateSubtitles,
    isResumingTask,
    file
  ]);

  // Poll for status updates when processing
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;
    
    if (status === 'processing' && fileId) {
      const checkStatus = async () => {
        try {
          const response = await axios.get<ProcessingDetails>(`/api/progress/${fileId}`);
          setProcessingDetails(response.data);
          
          if (response.data.status === 'completed') {
            setStatus('completed');
            setUploading(false);
            setProgress(100);
            // Preserve taskId so task-based endpoints remain valid in the completed view
            // Do not clear local storage here to keep task metadata available
            
          } else if (response.data.status === 'processing' || response.data.status === 'uploaded') {
            setStatus('processing');
            setProgress(response.data.progress);
          } else if (response.data.status === 'cancelled') {
            setStatus('cancelled');
            setUploading(false);
            setTaskId(null);
            setProgress(0);
            
            // Clear local storage when cancelled
            localStorageUtils.clearTaskState();
            
          } else if (response.data.status === 'failed') {
            setStatus('error');
            setUploading(false);
            setTaskId(null);
            
            // Clear local storage when failed
            localStorageUtils.clearTaskState();
          } else {
            setStatus('error');
            setUploading(false);
            setTaskId(null);
            
            // Clear local storage when error
            localStorageUtils.clearTaskState();
          }
        } catch (error) {
          console.error('Status check error:', error);
          setStatus('error');
          setUploading(false);
          
          // Clear local storage on error
          localStorageUtils.clearTaskState();
        }
      };
      
      // Check status immediately
      checkStatus();
      
      // Set up interval to check status every 10 seconds
      intervalId = setInterval(checkStatus, 10000);
    }
    
    // Cleanup function to clear interval
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [status, fileId]);

  // Ensure taskId is populated in completed view (fallback via stats search)
  useEffect(() => {
    const hydrateTaskId = async () => {
      if (status === 'completed' && fileId && (!taskId || taskId === 'null')) {
        try {
          const res = await axios.get(`/api/tasks/search?query=${encodeURIComponent(fileId)}`);
          const tasks = Array.isArray(res.data?.tasks) ? res.data.tasks : [];
          const match = tasks.find((t: any) => t?.file_id === fileId && typeof t?.task_id === 'string' && !t.task_id.startsWith('state_'));
          if (match?.task_id) {
            setTaskId(match.task_id);
          }
        } catch (e) {
          console.warn('Failed to hydrate taskId for completed view', e);
        }
      }
    };
    hydrateTaskId();
  }, [status, fileId, taskId]);

  // Ensure taskId is populated during processing view as well
  useEffect(() => {
    const hydrateTaskIdWhileProcessing = async () => {
      if ((status === 'processing' || status === 'uploading') && fileId && (!taskId || taskId === 'null')) {
        try {
          const res = await axios.get(`/api/tasks/search?query=${encodeURIComponent(fileId)}`);
          const tasks = Array.isArray(res.data?.tasks) ? res.data.tasks : [];
          const match = tasks.find((t: any) => t?.file_id === fileId && typeof t?.task_id === 'string' && !t.task_id.startsWith('state_'));
          if (match?.task_id) {
            setTaskId(match.task_id);
          }
        } catch (e) {
          console.warn('Failed to hydrate taskId for processing view', e);
        }
      }
    };
    hydrateTaskIdWhileProcessing();
  }, [status, fileId, taskId]);

  // Add subtitle tracks when video is loaded
  useEffect(() => {
    if (status === 'completed' && generateSubtitles && taskId && videoRef.current) {
      const addSubtitles = () => {
        if (videoRef.current) {
          // Remove existing tracks
          const existingTracks = videoRef.current.querySelectorAll('track');
          existingTracks.forEach(track => track.remove());
          
          // Ensure video has loaded metadata before adding track
          if (videoRef.current.readyState === 0) {
            console.log('Video not ready, waiting for metadata...');
            return;
          }
          
          // Add VTT subtitle track if subtitles are enabled
          const track = document.createElement('track');
          track.kind = 'subtitles';
          // Always use absolute URL with explicit language to avoid mismatches
          track.src = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
          track.setAttribute('srclang', subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : 
                         subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : 
                         subtitleLanguage === 'japanese' ? 'ja' : 
                         subtitleLanguage === 'korean' ? 'ko' : 
                         subtitleLanguage === 'thai' ? 'th' : 'en');
          track.label = getLanguageDisplayName(subtitleLanguage);
          track.default = true;
          
          track.addEventListener('load', () => {
            console.log('Subtitle track loaded successfully');
            if (videoRef.current && videoRef.current.textTracks.length > 0) {
              const textTrack = videoRef.current.textTracks[0];
              textTrack.mode = 'showing';
              console.log('Subtitles are now showing');
            }
          });
          
          track.addEventListener('error', (e) => {
            console.error('Subtitle track loading error:', e);
            // Fallback: try without explicit language (server infers from state)
            const fallbackUrl = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt`;
            console.log('Trying fallback URL:', fallbackUrl);
            track.src = fallbackUrl;
          });
          
          videoRef.current.appendChild(track);
          
          // Force reload if track fails
          setTimeout(() => {
            if (videoRef.current && videoRef.current.textTracks.length === 0) {
              console.log('Retrying subtitle loading...');
              const retryTrack = document.createElement('track');
              retryTrack.kind = 'subtitles';
              retryTrack.src = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
              retryTrack.setAttribute('srclang', subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : 
                             subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : 
                             subtitleLanguage === 'japanese' ? 'ja' : 
                             subtitleLanguage === 'korean' ? 'ko' : 
                             subtitleLanguage === 'thai' ? 'th' : 'en');
              retryTrack.label = 'Subtitles';
              retryTrack.default = true;
              videoRef.current.appendChild(retryTrack);
            }
          }, 1000);
        }
      };
      
      // Wait for video to be fully loaded
      const handleLoadedMetadata = () => {
        console.log('Video metadata loaded, adding subtitles...');
        addSubtitles();
      };
      
      if (videoRef.current.readyState >= 1) {
        // Metadata already loaded
        addSubtitles();
      } else {
        // Wait for metadata to load
        videoRef.current.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
        videoRef.current.addEventListener('loadeddata', addSubtitles, { once: true });
      }
    }
  }, [status, generateSubtitles, subtitleLanguage, taskId]);

  const formatStepName = (step: string): string => {
    const stepNames: Record<string, string> = {
      // Common steps
      'extract_slides': 'Extracting Slides',
      'analyze_slide_images': 'Analyzing Content',
      'generate_transcripts': 'Generating Transcripts',
      'revise_transcripts': 'Revising Transcripts',
      'translate_voice_transcripts': 'Translating Voice Transcripts',
      'translate_subtitle_transcripts': 'Translating Subtitle Transcripts',
      'generate_subtitle_transcripts': 'Generating Subtitle Transcripts',
      'generate_audio': 'Generating Audio',
      'generate_avatar_videos': 'Creating Avatar',
      'convert_slides_to_images': 'Converting Slides',
      'generate_subtitles': 'Creating Subtitles',
      'compose_video': 'Composing Video',
      
      // PDF-specific steps
      'segment_pdf_content': 'Segmenting Content',
      'revise_pdf_transcripts': 'Revising Transcripts',
      'generate_pdf_chapter_images': 'Creating Video Frames',
      'generate_pdf_audio': 'Generating Audio',
      'generate_pdf_subtitles': 'Creating Subtitles',
      'compose_pdf_video': 'Composing Video',
      
      'unknown': 'Initializing'
    };
    return stepNames[step] || step;
  };

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

  const getLanguageDisplayName = (languageCode: string): string => {
    const languageNames: Record<string, string> = {
      'english': 'English',
      'simplified_chinese': '简体中文',
      'traditional_chinese': '繁體中文',
      'japanese': '日本語',
      'korean': '한국어',
      'thai': 'ไทย'
    };
    return languageNames[languageCode] || languageCode;
  };

  const getProcessingStatusMessage = (): string => {
    if (!processingDetails) {
      return isPdfFile(file?.name || null) 
        ? 'Bringing Your PDF to Life' 
        : 'Bringing Your Presentation to Life';
    }
    
    const activeSteps = Object.entries(processingDetails.steps || {})
      .filter(([_, step]) => step.status === 'in_progress' || step.status === 'processing');
    
    const isPdf = isPdfFile(file?.name || null);
    const fileTypeText = isPdf ? 'PDF' : 'PPT';
    
    if (activeSteps.length > 0) {
      const currentStepKey = activeSteps[0][0];
      const stepName = formatStepNameWithLanguages(
        currentStepKey,
        processingDetails.voice_language || 'english',
        processingDetails.subtitle_language || processingDetails.voice_language || 'english'
      );
      const statusMessages: Record<string, string> = {
        // Common messages for all file types
        'Extracting Slides': `Analyzing your ${fileTypeText} structure...`,
        'Analyzing Content': `Examining ${fileTypeText} content...`,
        'Generating Transcripts': 'Generating transcripts...',
        'Revising Transcripts': 'Polishing transcripts for delivery...',
        'Translating Voice Transcripts': 'Translating transcripts...',
        'Translating Subtitle Transcripts': 'Translating transcripts...',
        'Translating Transcripts': 'Translating transcripts...',
        'Generating Subtitle Transcripts': 'Generating subtitle transcripts...',
        'Reviewing Subtitles': 'Perfecting subtitle timing and accuracy...',
        'Generating Audio': 'Creating natural voice narration...',
        'Creating Avatar': 'Bringing AI presenter to life...',
        'Converting Slides': `Preparing ${fileTypeText} for video composition...`,
        'Creating Video Frames': isPdf ? 'Creating visual representations for chapters...' : 'Creating visual representations for slides...',
        'Composing Video': 'Bringing all elements together...'
      };
      return statusMessages[stepName] || `Working on: ${stepName}`;
    }
    
    return isPdf 
      ? 'Bringing Your PDF to Life' 
      : 'Bringing Your Presentation to Life';
  };

  const isPdfFile = (filename: string | null): boolean => {
    // If we have a filename, use it to determine file type
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ext === 'pdf';
    }
    // If we don't have a filename but have fileType from state, use that
    if (fileType) {
      return fileType.toLowerCase() === 'pdf';
    }
    // Default to false if we can't determine
    return false;
  };

  const getFileTypeHint = (filename: string): JSX.Element => {
    const ext = filename.toLowerCase().split('.').pop();
    
    if (ext === 'pdf') {
      return (
        <div className="file-type-hint pdf">
          <span className="file-type-badge pdf">PDF</span>
          <div className="file-type-description">
            AI will analyze and convert your PDF into engaging video chapters with AI narration and subtitles.
          </div>
        </div>
      );
    } else if (ext === 'pptx' || ext === 'ppt') {
      return (
        <div className="file-type-hint ppt">
          <span className="file-type-badge ppt">PPT</span>
          <div className="file-type-description">
            AI will convert your slides into a video with AI narration and optional avatar presenter.
          </div>
        </div>
      );
    }
    
    return (
      <div className="file-type-hint">
        <span className="file-type-badge">Supported File</span>
        <div className="file-type-description">
          Supports PDF, PPTX, and PPT files
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            {/* Spacer to balance the layout */}
          </div>
          <div className="header-center">
            <h1>SlideSpeaker AI</h1>
            <p>Transform slides into AI-powered videos</p>
          </div>
          <div className="header-right">
            <div className="view-toggle" role="tablist" aria-label="View Toggle">
              <button
                onClick={() => setShowTaskMonitor(false)}
                className={`toggle-btn ${!showTaskMonitor ? 'active' : ''}`}
                title="Studio"
                role="tab"
                aria-selected={!showTaskMonitor}
                aria-controls="studio-panel"
                id="studio-tab"
              >
                <span className="toggle-icon" aria-hidden="true">▶</span>
                <span className="toggle-text">Studio</span>
              </button>
              <button
                onClick={() => setShowTaskMonitor(true)}
                className={`toggle-btn ${showTaskMonitor ? 'active' : ''}`}
                title="Task Monitor"
                role="tab"
                aria-selected={showTaskMonitor}
                aria-controls="monitor-panel"
                id="monitor-tab"
              >
                <span className="toggle-icon" aria-hidden="true">📊</span>
                <span className="toggle-text">Monitor</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="main-content">
        {showTaskMonitor ? (
          <div id="monitor-panel" role="tabpanel" aria-labelledby="monitor-tab">
            <TaskMonitor apiBaseUrl={API_BASE_URL} />
          </div>
        ) : (
          <div id="studio-panel" role="tabpanel" aria-labelledby="studio-tab">
            <div className="card-container">
              <div className={`content-card ${status === 'completed' ? 'wide' : ''}`}>
            {status === 'idle' && (
              <div className="upload-view">
                {/* Entry mode toggle: Slides vs PDF are processed differently */}
                <div className="mode-toggle" role="tablist" aria-label="Entry Mode">
                  <button
                    type="button"
                    className={`toggle-btn ${uploadMode === 'slides' ? 'active' : ''}`}
                    onClick={() => setUploadMode('slides')}
                    role="tab"
                    aria-selected={uploadMode === 'slides'}
                    aria-controls="slides-mode-panel"
                  >
                    🖼️ Slides
                  </button>
                  <button
                    type="button"
                    className={`toggle-btn ${uploadMode === 'pdf' ? 'active' : ''}`}
                    onClick={() => setUploadMode('pdf')}
                    role="tab"
                    aria-selected={uploadMode === 'pdf'}
                    aria-controls="pdf-mode-panel"
                  >
                    📄 PDF
                  </button>
                </div>
                <div className="mode-explainer" aria-live="polite">
                  {uploadMode === 'slides' ? (
                    <>
                      <strong>Slides Mode:</strong> Processes each slide individually for transcripts, audio, subtitles, and composes a final video.
                    </>
                  ) : (
                    <>
                      <strong>PDF Mode:</strong> Segments the document into chapters, generates chapter audio + subtitles, then composes the final video.
                    </>
                  )}
                </div>
                {isResumingTask && (
                  <div className="resume-indicator">
                    <div className="spinner"></div>
                    <p>Resuming your last task...</p>
                  </div>
                )}
                
                <div className="file-upload-area">
                  <input
                    type="file"
                    id="file-upload"
                    accept={uploadMode === 'pdf' ? '.pdf' : '.pptx,.ppt'}
                    onChange={handleFileChange}
                    className="file-input"
                    disabled={isResumingTask}
                  />
                  <label htmlFor="file-upload" className={`file-upload-label ${isResumingTask ? 'disabled' : ''}`}>
                    <div className="upload-icon">📄</div>
                    <div className="upload-text">
                      {file ? file.name : (uploadMode === 'pdf' ? 'Choose a PDF file' : 'Choose a PPTX/PPT file')}
                    </div>
                    <div className="upload-hint">
                      {file ? (
                        getFileTypeHint(file.name)
                      ) : (
                        (uploadMode === 'pdf'
                          ? 'PDF will be processed as chapters for video + audio + subtitles'
                          : 'Slides will be processed per slide for video + audio + subtitles')
                      )}
                    </div>
                  </label>
                </div>
                
                <div className="video-options-section">
                  <div className="video-options-grid">
                    <div className="video-option-card">
                      <div className="video-option-header">
                        <span className="video-option-icon">🔊</span>
                        <span className="video-option-title">Audio Language</span>
                      </div>
                      <select 
                        id="language-select" 
                        value={voiceLanguage} 
                        onChange={(e) => setVoiceLanguage(e.target.value)}
                        className="video-option-select"
                      >
                        <option value="english">English</option>
                        <option value="simplified_chinese">简体中文</option>
                        <option value="traditional_chinese">繁體中文</option>
                        <option value="japanese">日本語</option>
                        <option value="korean">한국어</option>
                        <option value="thai">ไทย</option>
                      </select>
                    </div>
                    
                    <div className="video-option-card">
                      <div className="video-option-header">
                        <span className="video-option-icon">📝</span>
                        <span className="video-option-title">Subtitles</span>
                      </div>
                      <select 
                        id="subtitle-language-select" 
                        value={subtitleLanguage} 
                        onChange={(e) => setSubtitleLanguage(e.target.value)}
                        className="video-option-select"
                      >
                        <option value="english">English</option>
                        <option value="simplified_chinese">简体中文</option>
                        <option value="traditional_chinese">繁體中文</option>
                        <option value="japanese">日本語</option>
                        <option value="korean">한국어</option>
                        <option value="thai">ไทย</option>
                      </select>
                    </div>
                    
                    <div className="video-option-card">
                      <div className="video-option-header">
                        <span className="video-option-icon">📺</span>
                        <span className="video-option-title">Quality</span>
                      </div>
                      <select 
                        id="video-resolution-select" 
                        value={videoResolution} 
                        onChange={(e) => setVideoResolution(e.target.value)}
                        className="video-option-select"
                      >
                        <option value="sd">SD (640×480)</option>
                        <option value="hd">HD (1280×720)</option>
                        <option value="fullhd">Full HD (1920×1080)</option>
                      </select>
                    </div>
                  </div>
                </div>
                
                <div className="option-item minimal">
                  <input
                    type="checkbox"
                    id="generate-avatar"
                    checked={generateAvatar}
                    onChange={(e) => setGenerateAvatar(e.target.checked)}
                    disabled
                    title="AI Avatar is not available yet"
                  />
                  <label htmlFor="generate-avatar" className="minimal-label">AI Avatar</label>
                </div>
                
                {/* Subtle AI Disclaimer in Upload View */}
                <div className="ai-notice-subtle">
                  AI-generated content may contain inaccuracies. Review carefully.
                </div>
                
                {file && (
                  <button 
                    onClick={handleUpload} 
                    className="primary-btn"
                    disabled={uploading}
                  >
                    Create Video
                  </button>
                )}
              </div>
            )}

            {status === 'uploading' && (
              <div className="processing-view">
                <div className="spinner"></div>
                <h3>Uploading Your Presentation</h3>
                <div className="progress-container">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <p className="progress-text">{progress}% Uploaded</p>
                  <p className="processing-status">
                    Preparing your content for AI transformation...
                  </p>
                </div>
              </div>
            )}

            {status === 'processing' && (
              <div className="processing-view">
                <div className="spinner"></div>
                <h3>{getProcessingStatusMessage()}</h3>
                {/* Meta header: filename + task id */}
                <div className="processing-meta" role="group" aria-label="Task Meta">
                  <div className="meta-card file" title={processingDetails?.filename || file?.name || fileId || ''}>
                    <div className="meta-title">
                      <span className="meta-icon">📄</span>
                      <span className="meta-text">
                        {processingDetails?.filename || file?.name || 'Untitled'}
                      </span>
                    </div>
                    <div className="meta-badge">
                      {isPdfFile(file?.name || processingDetails?.filename || null) ? (
                        <span className="file-type-badge pdf">PDF</span>
                      ) : (
                        <span className="file-type-badge ppt">PPT</span>
                      )}
                    </div>
                  </div>
                  <div className="meta-card task" title={taskId || fileId || ''}>
                    <div className="meta-title">
                      <span className="meta-icon">🆔</span>
                    </div>
                    <div className="meta-actions">
                      <code
                        className={`meta-code ${taskId ? 'clickable' : ''}`}
                        aria-label={`Task ID: ${taskId || 'locating'} (press Enter to copy)`}
                        role="button"
                        tabIndex={taskId ? 0 : -1}
                        onClick={() => { if (taskId) { navigator.clipboard.writeText(taskId); alert('Task ID copied!'); } }}
                        onKeyDown={(e) => {
                          if (!taskId) return;
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            try {
                              navigator.clipboard.writeText(taskId);
                              alert('Task ID copied!');
                            } catch (err) {
                              console.error('Failed to copy task id', err);
                            }
                          }
                        }}
                        title={taskId || undefined}
                      >
                        {taskId || '(locating…)'}
                      </code>
                      {!taskId && (
                        <span className="meta-hint">from file {fileId?.slice(0, 8) || '…'}</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="progress-container">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>
                       
                <button 
                  onClick={handleStopProcessing} 
                  className="cancel-btn"
                >
                  STOP
                </button>
        
                
                {processingDetails && (
                  <div className="steps-container">
                    <h4>🌟 Crafting Your Masterpiece</h4>
                    {/* Meta moved into header */}
                    <div className="steps-grid">
                      {isPdfFile(file?.name || null) ? (
                        // PDF-specific steps
                        [
                          'segment_pdf_content',
                          'revise_pdf_transcripts',
                          'translate_voice_transcripts',
                          'translate_subtitle_transcripts',
                          'generate_pdf_chapter_images', 
                          'generate_pdf_audio',
                          'generate_pdf_subtitles',
                          // Backend uses 'compose_video' for the PDF compose step
                          'compose_video'
                        ]
                          .map((stepName) => {
                            const stepData = processingDetails.steps[stepName];
                            // Hide steps that are not present or explicitly skipped
                            if (!stepData || stepData.status === 'skipped') {
                              return null;
                            }
                            const vl = (processingDetails.voice_language || 'english').toLowerCase();
                            const sl = (processingDetails.subtitle_language || vl).toLowerCase();
                            const same = vl === sl;
                            if (same && stepName === 'translate_subtitle_transcripts') {
                              return null; // collapse duplicate translate step
                            }
                            return (
                              <div key={stepName} className={`step-item ${stepData.status}`}>
                                <span className="step-icon">
                                  {stepData.status === 'completed' ? '✓' :
                                   stepData.status === 'processing' || stepData.status === 'in_progress' ? '⏳' :
                                   stepData.status === 'failed' ? '✗' : '○'}
                                </span>
                                <span className="step-name">{formatStepNameWithLanguages(stepName, vl, sl)}</span>
                              </div>
                            );
                          })
                          .filter(Boolean)
                      ) : (
                        // PPT/PPTX-specific steps with translation steps
                        [
                          'extract_slides',
                          'convert_slides_to_images', 
                          'analyze_slide_images',
                          'generate_transcripts',
                          'revise_transcripts',
                          'translate_voice_transcripts',
                          'translate_subtitle_transcripts',
                          'generate_audio',
                          'generate_avatar_videos',
                          'generate_subtitles',
                          'compose_video'
                        ]
                          .map((stepName) => {
                            const stepData = processingDetails.steps[stepName];
                            // Hide steps that are not present or explicitly skipped
                            if (!stepData || stepData.status === 'skipped') {
                              return null;
                            }
                            const vl = (processingDetails.voice_language || 'english').toLowerCase();
                            const sl = (processingDetails.subtitle_language || vl).toLowerCase();
                            const same = vl === sl;
                            if (same && stepName === 'translate_subtitle_transcripts') {
                              return null; // collapse duplicate translate step
                            }
                            return (
                              <div key={stepName} className={`step-item ${stepData.status}`}>
                                <span className="step-icon">
                                  {stepData.status === 'completed' ? '✓' :
                                   stepData.status === 'processing' || stepData.status === 'in_progress' ? '⏳' :
                                   stepData.status === 'failed' ? '✗' : '○'}
                                </span>
                                <span className="step-name">{formatStepNameWithLanguages(stepName, vl, sl)}</span>
                              </div>
                            );
                          })
                          .filter(Boolean)
                      )}
                    </div>
                    
                    {processingDetails.errors && processingDetails.errors.length > 0 && (
                      <div className="error-section">
                        <h4>Errors Encountered</h4>
                        <div className="error-list">
                          {processingDetails.errors.map((error, index) => {
                            const vl = (processingDetails.voice_language || 'english').toLowerCase();
                            const sl = (processingDetails.subtitle_language || vl).toLowerCase();
                            return (
                              <div key={index} className="error-item">
                                <strong>{formatStepNameWithLanguages(error.step, vl, sl)}:</strong> {error.error}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {processingTranscriptMd && (
                  <div className="processing-transcript">
                    <h4>Transcript (Preview)</h4>
                    <div className="transcript-content" role="region" aria-label="Transcript preview">
                      <pre>
                        {processingTranscriptMd}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            )}

            {status === 'completed' && (
              <div className="completed-view">
                {showCompletedBanner && (
                  <div className="completed-banner">
                    <div className="success-icon">✓</div>
                    <h3>Your Masterpiece is Ready!</h3>
                    <p className="success-message">Congratulations! Your presentation has been transformed into an engaging AI-powered video.</p>
                    <button
                      type="button"
                      className="banner-dismiss"
                      aria-label="Dismiss banner"
                      onClick={() => {
                        setShowCompletedBanner(false);
                        try { localStorage.setItem('ss_show_completed_banner', '0'); } catch {}
                      }}
                    >
                      ✕
                    </button>
                  </div>
                )}
                
                {/* Tabs for switching media mode - placed at the top for better visibility */}
                <div className="mode-toggle-container">
                  <div className="mode-toggle compact">
                    <button
                      type="button"
                      className={`toggle-btn ${completedMedia === 'video' ? 'active' : ''}`}
                      onClick={() => setCompletedMedia('video')}
                    >
                      🎬 Video
                    </button>
                    <button
                      type="button"
                      className={`toggle-btn ${completedMedia === 'audio' ? 'active' : ''}`}
                      onClick={() => setCompletedMedia('audio')}
                    >
                      🎧 Audio
                    </button>
                  </div>
                </div>
                
                {/* Video area (shows only in Video mode) */}
                {completedMedia === 'video' && (
                  <div className="media-section video-active">
                    <div className="video-wrapper">
                      <video 
                        ref={videoRef}
                        controls
                        src={`${API_BASE_URL}/api/tasks/${taskId}/video`}
                        crossOrigin="anonymous"
                        className="preview-video-large"
                      >
                        {/* Always include a subtitles track for the completed view */}
                        <track
                          kind="subtitles"
                          src={`${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english')}`}
                          srcLang={(processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english') === 'simplified_chinese' ? 'zh-Hans' :
                                   (processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english') === 'traditional_chinese' ? 'zh-Hant' :
                                   (processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english') === 'japanese' ? 'ja' :
                                   (processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english') === 'korean' ? 'ko' :
                                   (processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english') === 'thai' ? 'th' : 'en'}
                          label={getLanguageDisplayName(processingDetails?.subtitle_language || subtitleLanguage || voiceLanguage || 'english')}
                          default
                        />
                      </video>
                    </div>
                  </div>
                )}
                
                {/* Audio area (shows only in Audio mode) */}
                {completedMedia === 'audio' && (
                  <div className="media-section audio-active">
                    <div className="audio-section">
                      {/* Inline audio player for quick listening */}
                      <div className="audio-player-inline">
                        <audio
                          ref={audioRef}
                          controls
                          preload="auto"
                          src={`${API_BASE_URL}/api/tasks/${taskId}/audio`}
                          crossOrigin="anonymous"
                          aria-label="Audio narration preview"
                        >
                          Your browser does not support the audio element.
                        </audio>
                      </div>
                      {showAudioTranscript && audioCues.length > 0 && (
                        <div className="audio-transcript-pane" ref={audioTranscriptRef} aria-label="Audio captions">
                          {audioCues.map((cue, idx) => (
                            <div
                              key={idx}
                              id={`audio-cue-${idx}`}
                              className={`cue ${activeAudioCueIdx === idx ? 'active' : ''}`}
                              onClick={() => {
                                const a = audioRef.current;
                                if (!a) return;
                                const target = Math.max(0, Math.min(isFinite(a.duration) ? a.duration - 0.05 : cue.start + 0.01, cue.start + 0.01));
                                const doPlay = () => a.play().catch(() => {});
                                const doSeekReady = () => {
                                  try {
                                    const onSeeked = () => { a.removeEventListener('seeked', onSeeked); doPlay(); };
                                    a.addEventListener('seeked', onSeeked, { once: true });
                                    if ((a as any).fastSeek) {
                                      (a as any).fastSeek(target);
                                    } else {
                                      a.currentTime = target;
                                    }
                                  } catch {
                                    a.currentTime = target;
                                    doPlay();
                                  }
                                };
                                if (a.readyState >= 1) doSeekReady();
                                else a.addEventListener('loadedmetadata', doSeekReady, { once: true });
                              }}
                              role="button"
                              tabIndex={0}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  const a = audioRef.current;
                                  if (!a) return;
                                  const target = Math.max(0, Math.min(isFinite(a.duration) ? a.duration - 0.05 : cue.start + 0.01, cue.start + 0.01));
                                  const doPlay = () => a.play().catch(() => {});
                                  const doSeekReady = () => {
                                    try {
                                      const onSeeked = () => { a.removeEventListener('seeked', onSeeked); doPlay(); };
                                      a.addEventListener('seeked', onSeeked, { once: true });
                                      if ((a as any).fastSeek) {
                                        (a as any).fastSeek(target);
                                      } else {
                                        a.currentTime = target;
                                      }
                                    } catch {
                                      a.currentTime = target;
                                      doPlay();
                                    }
                                  };
                                  if (a.readyState >= 1) doSeekReady();
                                  else a.addEventListener('loadedmetadata', doSeekReady, { once: true });
                                }
                              }}
                            >
                              <div className="t-time">{Math.floor(cue.start / 60)}:{String(Math.floor(cue.start % 60)).padStart(2, '0')}</div>
                              <div className="t-text">{cue.text}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Information section */}
                <div className="preview-info-compact">
                  <div className="info-grid">
                    <div className="info-item">
                      <span className="info-label">Voice Language:</span>
                      <span className="info-value">{processingDetails?.voice_language ? getLanguageDisplayName(processingDetails.voice_language) : 'English'}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Subtitle Language:</span>
                      <span className="info-value">{processingDetails?.subtitle_language ? getLanguageDisplayName(processingDetails.subtitle_language) : getLanguageDisplayName(subtitleLanguage)}</span>
                    </div>
                    {isPdfFile(file?.name || null) ? (
                      <div className="info-item">
                        <span className="info-label">Document Type:</span>
                        <span className="info-value">PDF Chapters</span>
                      </div>
                    ) : (
                      <div className="info-item">
                        <span className="info-label disabled">AI Avatar:</span>
                        <span className="info-value">{generateAvatar ? '✓ Generated' : '✗ Disabled'}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Resource URLs */}
                <div className="resource-links">
                  {/* Video */}
                  <div className="url-copy-row">
                    <span className="resource-label-inline">Video</span>
                    <input 
                      type="text" 
                        value={`${API_BASE_URL}/api/tasks/${taskId}/video`}
                        readOnly 
                        className="url-input-enhanced"
                      />
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(`${API_BASE_URL}/api/tasks/${taskId}/video`);
                          alert('Video URL copied!');
                        }}
                        className="copy-btn-enhanced"
                      >
                        Copy
                      </button>
                    </div>

                    {/* Audio */}
                    <div className="url-copy-row">
                      <span className="resource-label-inline">Audio</span>
                      <input 
                        type="text" 
                        value={`${API_BASE_URL}/api/tasks/${taskId}/audio`}
                        readOnly 
                        className="url-input-enhanced"
                      />
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(`${API_BASE_URL}/api/tasks/${taskId}/audio`);
                          alert(`Audio URL copied!`);
                        }}
                        className="copy-btn-enhanced"
                      >
                        Copy
                      </button>
                    </div>

                    {/* Transcript */}
                    {fileId && (
                      <div className="url-copy-row">
                        <span className="resource-label-inline">Transcript</span>
                        <input 
                          type="text" 
                          value={`${API_BASE_URL}/api/tasks/${taskId}/transcripts/markdown`}
                          readOnly 
                          className="url-input-enhanced"
                        />
                        <button 
                          onClick={() => {
                            navigator.clipboard.writeText(`${API_BASE_URL}/api/tasks/${taskId}/transcripts/markdown`);
                            alert('Transcript URL copied!');
                          }}
                          className="copy-btn-enhanced"
                        >
                          Copy
                        </button>
                      </div>
                    )}

                    {/* VTT */}
                    <div className="url-copy-row">
                      <span className="resource-label-inline">VTT</span>
                      <input 
                        type="text" 
                        value={`${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt`}
                        readOnly 
                        className="url-input-enhanced"
                      />
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(`${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt`);
                          alert('VTT URL copied!');
                        }}
                        className="copy-btn-enhanced"
                      >
                        Copy
                      </button>
                    </div>

                    {/* SRT */}
                    {generateSubtitles && fileId && (
                      <div className="url-copy-row">
                        <span className="resource-label-inline">SRT</span>
                        <input 
                          type="text" 
                          value={`${API_BASE_URL}/api/tasks/${taskId}/subtitles/srt`}
                          readOnly 
                          className="url-input-enhanced"
                        />
                        <button 
                          onClick={() => {
                            navigator.clipboard.writeText(`${API_BASE_URL}/api/tasks/${taskId}/subtitles/srt`);
                            alert('SRT URL copied!');
                          }}
                          className="copy-btn-enhanced"
                        >
                          Copy
                        </button>
                      </div>
                    )}
                  </div>
                
                {/* Prominent create-new CTA placed at the end of the completed view for better user flow */}
                <div className="completed-cta-bottom">
                  <button onClick={resetForm} className="primary-btn" type="button">
                    Create Another Video
                  </button>
                </div>
              </div>
            )}

            {status === 'error' && (
              <div className="error-view">
                <div className="error-icon">⚠️</div>
                <h3>Processing Failed</h3>
                <p className="error-message">Something went wrong during video generation. Please try again with a different file.</p>
                <button onClick={resetForm} className="primary-btn">
                  Try Again
                </button>
              </div>
            )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer with note + Theme toggle at the bottom */}
      <footer className="app-footer" role="contentinfo">
        <div className="footer-content">
          <p className="footer-note">Powered by SlideSpeaker AI • Where presentations become your masterpiece</p>
          <div className="view-toggle theme-toggle" role="tablist" aria-label="Theme Toggle">
            <button
              onClick={() => setUiTheme('classic')}
              className={`toggle-btn ${uiTheme === 'classic' ? 'active' : ''}`}
              title="Modern Theme"
              role="tab"
              aria-selected={uiTheme === 'classic'}
              aria-controls="modern-theme-panel"
            >
              <span className="toggle-text">Modern</span>
            </button>
            <button
              onClick={() => setUiTheme('flat')}
              className={`toggle-btn ${uiTheme === 'flat' ? 'active' : ''}`}
              title="Flat Theme"
              role="tab"
              aria-selected={uiTheme === 'flat'}
              aria-controls="flat-theme-panel"
            >
              <span className="toggle-text">Flat</span>
            </button>
            <button
              onClick={() => setUiTheme('material')}
              className={`toggle-btn ${uiTheme === 'material' ? 'active' : ''}`}
              title="Material Theme"
              role="tab"
              aria-selected={uiTheme === 'material'}
              aria-controls="material-theme-panel"
            >
              <span className="toggle-text">Material</span>
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

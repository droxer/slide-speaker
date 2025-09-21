import React, { useState, useRef, useEffect, useMemo } from "react";
import { upload as apiUpload, cancelRun as apiCancel, getHealth as apiHealth, getTaskProgress as apiGetProgress, getTranscriptMarkdown as apiGetTranscript, headTaskVideo as apiHeadVideo, getVttText as apiGetVttText } from "./services/client";
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import "./styles/app.scss";
import "./styles/ultra-flat-overrides.scss";
import "./styles/subtle-material-overrides.scss";
import "./styles/classic-overrides.scss";
import TaskMonitor from "./components/TaskMonitor";
import ProcessingView from "./components/ProcessingView";
import CompletedView from "./components/CompletedView";
import UploadPanel from "./components/UploadPanel";
import { getStepLabel } from './utils/stepLabels';
import { useUI } from './context/UIContext';
// Players are used within components (CompletedView/TaskMonitor) not here

// Constants for local storage keys
const LOCAL_STORAGE_KEYS = {
  TASK_STATE: "slidespeaker_task_state",
  FILE_ID: "slidespeaker_file_id",
  TASK_ID: "slidespeaker_task_id",
  STATUS: "slidespeaker_status",
  PROCESSING_DETAILS: "slidespeaker_processing_details",
  LATEST_TASK_TIMESTAMP: "slidespeaker_latest_task_timestamp",
  FILE_TYPE: "slidespeaker_file_type", // Add file type tracking for PDF vs PPT handling
};

// API configuration – prefer same-origin when served over HTTPS to avoid mixed-content blocks
const API_BASE_URL = (() => {
  const env = process.env.REACT_APP_API_BASE_URL;
  if (env !== undefined) return env;
  const { protocol, hostname } = window.location;
  if (protocol === "https:") {
    // Use same-origin '/api' paths; rely on reverse proxy in production
    return "";
  }
  // Local dev over HTTP
  return `${protocol}//${hostname}:8000`;
})();

// UI Theme key
const THEME_STORAGE_KEY = "slidespeaker_ui_theme"; // 'flat' | 'classic' | 'material'

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
  file_ext?: string;
  voice_language?: string;
  subtitle_language?: string;
  created_at: string;
  updated_at: string;
}

type AppStatus =
  | "idle"
  | "uploading"
  | "processing"
  | "completed"
  | "error"
  | "cancelled";

// Local storage utility functions
const localStorageUtils = {
  saveTaskState: (state: {
    fileId: string | null;
    taskId: string | null;
    status: AppStatus;
    processingDetails: ProcessingDetails | null;
    voiceLanguage: string;
    subtitleLanguage: string;
    transcriptLanguage: string;
    generateAvatar: boolean;
    generateSubtitles: boolean;
    fileName: string | null; // Add fileName to track file type
  }) => {
    try {
      const stateToSave = {
        ...state,
        timestamp: new Date().toISOString(),
      };
      localStorage.setItem(
        LOCAL_STORAGE_KEYS.TASK_STATE,
        JSON.stringify(stateToSave),
      );
      localStorage.setItem(
        LOCAL_STORAGE_KEYS.LATEST_TASK_TIMESTAMP,
        new Date().toISOString(),
      );
      // Save file type information
      if (state.fileName) {
        const fileType = state.fileName.toLowerCase().split(".").pop() || "";
        localStorage.setItem(LOCAL_STORAGE_KEYS.FILE_TYPE, fileType);
      }
    } catch (error) {
      console.warn("Failed to save task state to local storage:", error);
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
        const hoursDiff =
          (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60);

        if (hoursDiff < 24) {
          // Load file type information
          const fileType = localStorage.getItem(LOCAL_STORAGE_KEYS.FILE_TYPE);
          return {
            ...parsed,
            fileType,
          };
        } else {
          // Clean up old data
          localStorageUtils.clearTaskState();
          return null;
        }
      }
      return null;
    } catch (error) {
      console.warn("Failed to load task state from local storage:", error);
      return null;
    }
  },

  clearTaskState: () => {
    try {
      Object.values(LOCAL_STORAGE_KEYS).forEach((key) => {
        localStorage.removeItem(key);
      });
    } catch (error) {
      console.warn("Failed to clear task state from local storage:", error);
    }
  },

  saveFileId: (fileId: string) => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEYS.FILE_ID, fileId);
    } catch (error) {
      console.warn("Failed to save file ID to local storage:", error);
    }
  },

  loadFileId: (): string | null => {
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEYS.FILE_ID);
    } catch (error) {
      console.warn("Failed to load file ID from local storage:", error);
      return null;
    }
  },

  saveTaskId: (taskId: string) => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEYS.TASK_ID, taskId);
    } catch (error) {
      console.warn("Failed to save task ID to local storage:", error);
    }
  },

  loadTaskId: (): string | null => {
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEYS.TASK_ID);
    } catch (error) {
      console.warn("Failed to load task ID from local storage:", error);
      return null;
    }
  },
};

function App() {
  const queryClient = useQueryClient();
  // UI theme: 'classic' (Modern, default), 'flat', or 'material'
  const [uiTheme, setUiTheme] = useState<"flat" | "classic" | "material">(
    () => {
      try {
        const saved = localStorage.getItem(THEME_STORAGE_KEY);
        if (saved === "classic" || saved === "flat" || saved === "material")
          return saved as "flat" | "classic" | "material";
      } catch {}
      return "classic";
    },
  );

  // Apply/remove theme classes on body
  useEffect(() => {
    const isFlat = uiTheme === "flat";
    const isMaterial = uiTheme === "material";
    const isClassic = uiTheme === "classic";
    document.body.classList.toggle("ultra-flat", isFlat);
    document.body.classList.toggle("subtle-material", isMaterial);
    document.body.classList.toggle("classic", isClassic);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, uiTheme);
    } catch {}
  }, [uiTheme]);

  const [file, setFile] = useState<File | null>(null);
  const [, setFileType] = useState<string | null>(null); // Track file type for PDF vs PPT handling (setter only) // eslint-disable-line @typescript-eslint/no-unused-vars
  const [uploading, setUploading] = useState<boolean>(false);
  const [fileId, setFileId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [processingDetails, setProcessingDetails] =
    useState<ProcessingDetails | null>(null);
  // Using final audio endpoint; no need to fetch per-track list
  const [voiceLanguage, setVoiceLanguage] = useState<string>("english");
  const [subtitleLanguage, setSubtitleLanguage] = useState<string>("english");
  const [transcriptLanguage, setTranscriptLanguage] = useState<string>("english");
  const [transcriptLangTouched, setTranscriptLangTouched] = useState<boolean>(false);
  const [videoResolution, setVideoResolution] = useState<string>("hd"); // hd as default
  const [generateAvatar, setGenerateAvatar] = useState<boolean>(false);
  const [generateSubtitles, setGenerateSubtitles] = useState<boolean>(true);
  const [isResumingTask, setIsResumingTask] = useState<boolean>(false);
  const { showTaskMonitor, setShowTaskMonitor } = useUI();
  const [uploadMode, setUploadMode] = useState<"slides" | "pdf">("slides");
  const [pdfOutputMode, setPdfOutputMode] = useState<"video" | "podcast">(
    "video",
  );
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  // Video loading state handled inside components
  // Keep transcriptLanguage in sync with voiceLanguage for PDF+Podcast unless user changed it
  useEffect(() => {
    if (uploadMode === 'pdf' && pdfOutputMode === 'podcast' && !transcriptLangTouched) {
      setTranscriptLanguage(voiceLanguage);
    }
  }, [uploadMode, pdfOutputMode, voiceLanguage, transcriptLangTouched]);

  // Reset touch flag when switching into podcast mode so it follows voice by default
  useEffect(() => {
    if (uploadMode === 'pdf' && pdfOutputMode === 'podcast') {
      setTranscriptLangTouched(false);
    }
  }, [uploadMode, pdfOutputMode]);
  // Global health (footer indicator) via React Query
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: apiHealth,
    refetchInterval: 15000,
    refetchOnWindowFocus: false,
  });
  const queueUnavailable = !((healthQuery.data as any)?.redis?.ok === true || (healthQuery.data as any)?.redis_ok === true);
  const redisLatencyMs = (() => {
    const d: any = healthQuery.data;
    const latRaw = (d?.redis && d.redis.latency_ms) ?? d?.redis_latency_ms;
    return typeof latRaw === 'number' ? Math.round(latRaw) : null;
  })();
  // Audio transcript UI is handled by reusable components
  // Completed banner visibility (dismissible)
  const [showCompletedBanner, setShowCompletedBanner] = useState<boolean>(
    () => {
      try {
        return localStorage.getItem("ss_show_completed_banner") !== "0";
      } catch {
        return true;
      }
    },
  );
  const COMPLETED_MEDIA_KEY = "slidespeaker_completed_media";
  const [completedMedia, setCompletedMedia] = useState<"video" | "audio">(
    () => {
      try {
        const stored = localStorage.getItem(COMPLETED_MEDIA_KEY);
        if (stored === "video" || stored === "audio")
          return stored as "video" | "audio";
      } catch {}
      return "video";
    },
  );
  const [processingPreviewMode, setProcessingPreviewMode] = useState<
    "video" | "audio"
  >("video");
  // Completed view: pin user choice to prevent auto-forcing
  const completedMediaPinnedRef = useRef<boolean>(false);
  // Completed view: subtitles handled by VideoPlayer/AudioPlayer components

  // Studio policy: upload form is shown only when idle

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const ext = selectedFile.name.toLowerCase().split(".").pop();
      const isPdf = ext === "pdf";
      const isSlide = ext === "pptx" || ext === "ppt";
      if (uploadMode === "pdf" && !isPdf) {
        alert("Please select a PDF file for PDF processing.");
        return;
      }
      if (uploadMode === "slides" && !isSlide) {
        alert("Please select a PPTX or PPT file for Slides processing.");
        return;
      }
      if (ext && (isPdf || isSlide)) {
        setFile(selectedFile);
        setFileType(ext);
      } else {
        alert("Please select a PDF or PowerPoint file");
      }
    }
  };

  const uploadMutation = useMutation({
    mutationFn: apiUpload,
    onSettled: async () => {
      try {
        await queryClient.invalidateQueries({ queryKey: ['tasks'] });
        await queryClient.invalidateQueries({ queryKey: ['tasksSearch'] });
      } catch {}
    },
  });

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setStatus("uploading");

    try {
      // Read file as array buffer for base64 encoding using FileReader for better performance
      const base64File = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          // Remove the data URL prefix (e.g., "data:application/pdf;base64,")
          const base64Data = result.split(",")[1];
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      // Send as JSON
      const response = await uploadMutation.mutateAsync({
          filename: file.name,
          file_data: base64File,
          voice_language: voiceLanguage,
          subtitle_language: subtitleLanguage,
          transcript_language:
            uploadMode === 'pdf' && pdfOutputMode === 'podcast'
              ? transcriptLanguage
              : undefined,
          video_resolution: videoResolution,
          generate_avatar: generateAvatar,
          generate_subtitles: generateSubtitles,
          ...(uploadMode === "pdf"
            ? {
                task_type: pdfOutputMode === "video" ? "video" : "podcast",
                source_type: "pdf",
              }
            : {
                task_type: "video",
                source_type: "slides",
              }),
        });

      setFileId(response.file_id);
      setTaskId(response.task_id);
      setStatus("processing");
      setProgress(0);
    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload failed. Please try again.");
      setUploading(false);
      setStatus("idle");
    }
  };

  const cancelMutation = useMutation({
    mutationFn: (id: string) => apiCancel(id),
    onSettled: async () => {
      try {
        await queryClient.invalidateQueries({ queryKey: ['progress'] });
        await queryClient.invalidateQueries({ queryKey: ['tasks'] });
      } catch {}
    },
  });

  const handleStopProcessing = async () => {
    if (!taskId) return;

    try {
      const response = await cancelMutation.mutateAsync(taskId);
      console.log("Stop processing response:", response);

      // Instead of immediately setting to idle, let the polling detect the cancelled state
      // This ensures frontend and backend stay in sync
      setStatus("processing"); // Keep showing processing until backend confirms cancelled
      alert("Processing is being stopped... Please wait a moment.");
    } catch (error) {
      console.error("Stop processing error:", error);
      alert(
        "Failed to stop processing. The task may have already completed or failed.",
      );
    }
  };

  const resetForm = () => {
    setFile(null);
    setFileType(null);
    setFileId(null);
    setTaskId(null);
    setStatus("idle");
    setUploading(false);
    setProgress(0);
    setProcessingDetails(null);
    // Keep the current subtitle language selection
    setGenerateAvatar(false);
    setGenerateSubtitles(true);
    if (videoRef.current) {
      videoRef.current.src = "";
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
        setTranscriptLanguage(savedState.transcriptLanguage || savedState.subtitleLanguage || 'english');
        setGenerateAvatar(savedState.generateAvatar);
        setGenerateSubtitles(savedState.generateSubtitles);
        setFileType(savedState.fileType || null);

        console.log("Resuming task from local storage:", {
          fileId: savedState.fileId,
          taskId: savedState.taskId,
          status: savedState.status,
          fileType: savedState.fileType,
        });

        setIsResumingTask(false);
      }
    };

    loadSavedState();
  }, []);

  // Processing transcript preview fetch removed to avoid duplicate/early transcript view

  // Transcript/VTT handling moved to reusable players

  // Detect actual video availability via HEAD for Completed view using React Query
  const [hasVideoAsset, setHasVideoAsset] = useState<boolean>(false);
  const videoHeadQuery = useQuery({
    queryKey: ['videoHead', taskId],
    queryFn: () => apiHeadVideo(taskId as string),
    enabled: status === 'completed' && Boolean(taskId),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
  useEffect(() => {
    if (status !== 'completed') { setHasVideoAsset(false); return; }
    if (videoHeadQuery.isSuccess) setHasVideoAsset(Boolean(videoHeadQuery.data));
  }, [status, videoHeadQuery.isSuccess, videoHeadQuery.data]);

  // Stable task type for dependency-light effects
  const taskType = useMemo(() => {
    return ((((processingDetails as any)?.task_type) || '').toLowerCase());
  }, [processingDetails]);

  // Fetch conversation transcript (Query) for Completed podcast
  const completedTranscriptQuery = useQuery({
    queryKey: ['transcript', taskId],
    queryFn: () => apiGetTranscript(taskId as string),
    enabled: status === 'completed' && Boolean(taskId) && (["podcast","both"].includes(taskType)),
    staleTime: 5 * 60_000,
  });
  const [completedTranscriptMd, setCompletedTranscriptMd] = useState<string | null>(null);
  useEffect(() => {
    if (completedTranscriptQuery.isSuccess) setCompletedTranscriptMd(String(completedTranscriptQuery.data || ''));
    else if (status !== 'completed') setCompletedTranscriptMd(null);
  }, [completedTranscriptQuery.isSuccess, completedTranscriptQuery.data, status]);

  // Ensure video subtitles display by default in Completed view
  useEffect(() => {
    if (status !== "completed") return;
    const v = videoRef.current;
    if (!v) return;
    try {
      const tracks = v.textTracks;
      if (tracks && tracks.length > 0) {
        tracks[0].mode = "showing";
      }
    } catch {}
  }, [status, taskId, videoRef]);

  // Stable subtitle language code for completed view
  const subtitleLanguageCode = useMemo(() => {
    const explicit = (processingDetails as any)?.subtitle_language;
    return explicit || subtitleLanguage || voiceLanguage || 'english';
  }, [processingDetails, subtitleLanguage, voiceLanguage]);

  const subtitleLocale = useMemo(() => {
    const lang = (subtitleLanguageCode || '').toLowerCase();
    if (lang === 'simplified_chinese') return 'zh-Hans';
    if (lang === 'traditional_chinese') return 'zh-Hant';
    if (lang === 'japanese') return 'ja';
    if (lang === 'korean') return 'ko';
    if (lang === 'thai') return 'th';
    return 'en';
  }, [subtitleLanguageCode]);

  const vttUrl = useMemo(() => `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguageCode)}`,
    [taskId, subtitleLanguageCode]);

  // Prefetch VTT for Completed video (optional warm cache)
  useQuery({
    queryKey: ['vtt', taskId, subtitleLanguageCode],
    queryFn: () => apiGetVttText(taskId as string, subtitleLanguageCode),
    enabled: status === 'completed' && Boolean(taskId) && (["video","both"].includes(taskType)),
    staleTime: 5 * 60_000,
  });

  // Persist completed media selection
  useEffect(() => {
    try {
      localStorage.setItem(COMPLETED_MEDIA_KEY, completedMedia);
    } catch {}
  }, [completedMedia]);

  // If only podcast is generated (no video), force audio tab in Completed view (unless user pinned)
  useEffect(() => {
    if (status !== "completed") return;
    if (completedMediaPinnedRef.current) return;
    const genVideo = ["video", "both"].includes(taskType);
    if (!genVideo && completedMedia !== "audio") {
      setCompletedMedia("audio");
    }
  }, [status, taskType, completedMedia]);

  // Default to Video on Completed view when video exists (unless user pinned)
  useEffect(() => {
    if (status !== 'completed') return;
    if (completedMediaPinnedRef.current) return;
    const genVideo = ["video", "both"].includes(taskType) || hasVideoAsset;
    if (genVideo && completedMedia !== 'video') {
      setCompletedMedia('video');
    }
  }, [status, taskId, taskType, completedMedia, hasVideoAsset]);

  // Video loading overlay handled inside VideoPlayer component

  // Also hide banner when video starts playing
  useEffect(() => {
    if (status !== "completed") return;
    const v = videoRef.current;
    if (!v) return;
    const onPlay = () => {
      if (showCompletedBanner) {
        setShowCompletedBanner(false);
        try {
          localStorage.setItem("ss_show_completed_banner", "0");
        } catch {}
      }
    };
    v.addEventListener("play", onPlay);
    return () => {
      v.removeEventListener("play", onPlay);
    };
  }, [status, taskId, showCompletedBanner]);

  // Prevent video and audio from playing simultaneously
  useEffect(() => {
    if (status !== "completed") return;

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

    video.addEventListener("play", handleVideoPlay);
    audio.addEventListener("play", handleAudioPlay);

    return () => {
      video.removeEventListener("play", handleVideoPlay);
      audio.removeEventListener("play", handleAudioPlay);
    };
  }, [status, taskId]);

  // Prefetch media when task is completed (once per taskId). Skips subtitles to avoid duplicate VTT loads.
  const prefetchDoneRef = useRef<string | null>(null);
  useEffect(() => {
    if (status !== "completed" || !taskId) return;
    if (prefetchDoneRef.current === taskId) return;
    try {
      const videoEnabled = ["video", "both"].includes(taskType) || hasVideoAsset;
      const podcastEnabled = ["podcast", "both"].includes(taskType);

      if (videoEnabled) {
        const videoUrl = `${API_BASE_URL}/api/tasks/${taskId}/video`;
        const hasVideoLink = Array.from(document.querySelectorAll('link[rel="prefetch"]')).some((el) => (el as HTMLLinkElement).href === videoUrl);
        if (!hasVideoLink) {
          const l = document.createElement('link');
          l.rel = 'prefetch';
          l.href = videoUrl;
          l.as = 'video';
          document.head.appendChild(l);
        }
      }
      const audioUrl = `${API_BASE_URL}/api/tasks/${taskId}/${podcastEnabled ? 'podcast' : 'audio'}`;
      const hasAudioLink = Array.from(document.querySelectorAll('link[rel="prefetch"]')).some((el) => (el as HTMLLinkElement).href === audioUrl);
      if (!hasAudioLink) {
        const l = document.createElement('link');
        l.rel = 'prefetch';
        l.href = audioUrl;
        l.as = 'audio';
        document.head.appendChild(l);
      }

      prefetchDoneRef.current = taskId;
    } catch (e) {
      console.warn('Prefetch links failed:', e);
    }
  }, [status, taskId, hasVideoAsset, taskType]);

  // Transcript/VTT sync is now encapsulated in components

  // No-op: final audio is served via a single endpoint

  // Save task state to local storage whenever relevant state changes
  useEffect(() => {
    if (status !== "idle" && !isResumingTask) {
      localStorageUtils.saveTaskState({
        fileId,
        taskId,
        status,
        processingDetails,
        voiceLanguage,
        subtitleLanguage,
        transcriptLanguage,
        generateAvatar,
        generateSubtitles,
        fileName: file?.name || null,
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
    transcriptLanguage,
    isResumingTask,
    file,
  ]);

  // Poll for status updates when processing via React Query
  const progressQuery = useQuery({
    queryKey: ['progress', taskId],
    queryFn: () => apiGetProgress<ProcessingDetails>(taskId as string),
    enabled: status === 'processing' && Boolean(taskId),
    refetchInterval: 3000,
    refetchOnWindowFocus: false,
  });
  useEffect(() => {
    const resp = progressQuery.data as any;
    if (!resp || !resp.data) return;
    const data = resp.data;
    setProcessingDetails(resp as ProcessingDetails);
    if (data.status === 'completed') {
      setStatus('completed'); setUploading(false); setProgress(100);
    } else if (data.status === 'processing' || data.status === 'uploaded') {
      setStatus('processing'); setProgress(data.progress);
    } else if (data.status === 'cancelled') {
      setUploading(false); setTaskId(null); setFileId(null); setFile(null); setProcessingDetails(null); setProgress(0); localStorageUtils.clearTaskState(); setStatus('idle');
    } else if (data.status === 'failed') {
      setStatus('error'); setUploading(false); setTaskId(null); localStorageUtils.clearTaskState();
    } else {
      setStatus('error'); setUploading(false); setTaskId(null); localStorageUtils.clearTaskState();
    }
  }, [progressQuery.data]);

  // Ensure taskId is populated in completed view (fallback via stats search)
  useEffect(() => {
    const hydrateTaskId = async () => {
      if (status === "completed" && fileId && (!taskId || taskId === "null")) {
        try {
          const { searchTasks } = await import('./services/client');
          const res = await searchTasks(fileId);
          const tasks = Array.isArray(res?.tasks) ? res.tasks : [];
          const match = tasks.find(
            (t: any) =>
              t?.file_id === fileId &&
              typeof t?.task_id === "string" &&
              !t.task_id.startsWith("state_"),
          );
          if (match?.task_id) {
            setTaskId(match.task_id);
          }
        } catch (e) {
          console.warn("Failed to hydrate taskId for completed view", e);
        }
      }
    };
    hydrateTaskId();
  }, [status, fileId, taskId]);

  // Ensure taskId is populated during processing view as well
  useEffect(() => {
    const hydrateTaskIdWhileProcessing = async () => {
      if (
        (status === "processing" || status === "uploading") &&
        fileId &&
        (!taskId || taskId === "null")
      ) {
        try {
          const { searchTasks } = await import('./services/client');
          const res = await searchTasks(fileId);
          const tasks = Array.isArray(res?.tasks) ? res.tasks : [];
          const match = tasks.find(
            (t: any) =>
              t?.file_id === fileId &&
              typeof t?.task_id === "string" &&
              !t.task_id.startsWith("state_"),
          );
          if (match?.task_id) {
            setTaskId(match.task_id);
          }
        } catch (e) {
          console.warn("Failed to hydrate taskId for processing view", e);
        }
      }
    };
    hydrateTaskIdWhileProcessing();
  }, [status, fileId, taskId]);

  // Add subtitle tracks when video is loaded
  useEffect(() => {
    if (
      status === "completed" &&
      generateSubtitles &&
      taskId &&
      videoRef.current
    ) {
      const addSubtitles = () => {
        if (videoRef.current) {
          // Remove existing tracks
          const existingTracks = videoRef.current.querySelectorAll("track");
          existingTracks.forEach((track) => track.remove());

          // Ensure video has loaded metadata before adding track
          if (videoRef.current.readyState === 0) {
            console.log("Video not ready, waiting for metadata...");
            return;
          }

          // Skip dynamic track injection in Completed view; a static <track> is rendered there
          if (status === 'completed') {
            return;
          }

          // Add VTT subtitle track if subtitles are enabled (used during processing)
          const track = document.createElement("track");
          track.kind = "subtitles";
          // Always use absolute URL with explicit language to avoid mismatches
          track.src = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
          track.setAttribute(
            "srclang",
            subtitleLanguage === "simplified_chinese"
              ? "zh-Hans"
              : subtitleLanguage === "traditional_chinese"
                ? "zh-Hant"
                : subtitleLanguage === "japanese"
                  ? "ja"
                  : subtitleLanguage === "korean"
                    ? "ko"
                    : subtitleLanguage === "thai"
                      ? "th"
                      : "en",
          );
          track.label = getLanguageDisplayName(subtitleLanguage);
          track.default = true;

          track.addEventListener("load", () => {
            console.log("Subtitle track loaded successfully");
            if (videoRef.current && videoRef.current.textTracks.length > 0) {
              const textTrack = videoRef.current.textTracks[0];
              textTrack.mode = "showing";
              console.log("Subtitles are now showing");
            }
          });

          track.addEventListener("error", (e) => {
            console.error("Subtitle track loading error:", e);
            // Fallback: try without explicit language (server infers from state)
            const fallbackUrl = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt`;
            console.log("Trying fallback URL:", fallbackUrl);
            track.src = fallbackUrl;
          });

          videoRef.current.appendChild(track);

          // Force reload if track fails
          setTimeout(() => {
            if (videoRef.current && videoRef.current.textTracks.length === 0) {
              console.log("Retrying subtitle loading...");
              const retryTrack = document.createElement("track");
              retryTrack.kind = "subtitles";
              retryTrack.src = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
              retryTrack.setAttribute(
                "srclang",
                subtitleLanguage === "simplified_chinese"
                  ? "zh-Hans"
                  : subtitleLanguage === "traditional_chinese"
                    ? "zh-Hant"
                    : subtitleLanguage === "japanese"
                      ? "ja"
                      : subtitleLanguage === "korean"
                        ? "ko"
                        : subtitleLanguage === "thai"
                          ? "th"
                          : "en",
              );
              retryTrack.label = "Subtitles";
              retryTrack.default = true;
              videoRef.current.appendChild(retryTrack);
            }
          }, 1000);
        }
      };

      // Wait for video to be fully loaded
      const handleLoadedMetadata = () => {
        console.log("Video metadata loaded, adding subtitles...");
        addSubtitles();
      };

      if (videoRef.current.readyState >= 1) {
        // Metadata already loaded
        addSubtitles();
      } else {
        // Wait for metadata to load
        videoRef.current.addEventListener(
          "loadedmetadata",
          handleLoadedMetadata,
          { once: true },
        );
        videoRef.current.addEventListener("loadeddata", addSubtitles, {
          once: true,
        });
      }
    }
  }, [status, generateSubtitles, subtitleLanguage, taskId]);

  const formatStepName = (step: string): string => getStepLabel(step);

  const formatStepNameWithLanguages = (
    step: string,
    voiceLang: string,
    subtitleLang?: string,
  ): string => {
    const vl = (voiceLang || "english").toLowerCase();
    const sl = (subtitleLang || vl).toLowerCase();
    const same = vl === sl;
    if (
      same &&
      (step === "translate_voice_transcripts" ||
        step === "translate_subtitle_transcripts")
    ) {
      return "Translating Transcripts";
    }
    return formatStepName(step);
  };

  const getLanguageDisplayName = (languageCode: string): string => {
    const languageNames: Record<string, string> = {
      english: "English",
      simplified_chinese: "简体中文",
      traditional_chinese: "繁體中文",
      japanese: "日本語",
      korean: "한국어",
      thai: "ไทย",
    };
    return languageNames[languageCode] || languageCode;
  };

  // Removed unused getProcessingStatusMessage; ProcessingView shows progress and step names directly

  // Removed legacy isPdfFile helper; UI now uses backend file_ext

  const getFileTypeHint = (filename: string): JSX.Element => {
    const ext = filename.toLowerCase().split(".").pop();

    if (ext === "pdf") {
      return (
        <div className="file-type-hint pdf">
          <span className="file-type-badge pdf">PDF</span>
          <div className="file-type-description">
            AI will analyze and convert your PDF into engaging video chapters
            with AI narration and subtitles.
          </div>
        </div>
      );
    } else if (ext === "pptx" || ext === "ppt") {
      return (
        <div className="file-type-hint ppt">
          <span className="file-type-badge ppt">PPT</span>
          <div className="file-type-description">
            AI will convert your slides into a video with AI narration and
            optional avatar presenter.
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
            <div
              className="view-toggle"
              role="tablist"
              aria-label="View Toggle"
            >
              <button
                onClick={() => setShowTaskMonitor(false)}
                className={`toggle-btn ${!showTaskMonitor ? "active" : ""}`}
                title="Studio"
                role="tab"
                aria-selected={!showTaskMonitor}
                aria-controls="studio-panel"
                id="studio-tab"
              >
                <span className="toggle-icon" aria-hidden="true">
                  ▶
                </span>
                <span className="toggle-text">Studio</span>
              </button>
              <button
                onClick={() => setShowTaskMonitor(true)}
                className={`toggle-btn ${showTaskMonitor ? "active" : ""}`}
                title="Task Monitor"
                role="tab"
                aria-selected={showTaskMonitor}
                aria-controls="monitor-panel"
                id="monitor-tab"
              >
                <span className="toggle-icon" aria-hidden="true">
                  📊
                </span>
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
              <div
                className={`content-card ${status === "completed" ? "wide" : ""}`}
              >
                {/* Upload box visible only in idle */}
                {status === 'idle' && (
                  <UploadPanel
                    uploadMode={uploadMode}
                    setUploadMode={setUploadMode}
                    pdfOutputMode={pdfOutputMode}
                    setPdfOutputMode={setPdfOutputMode}
                    isResumingTask={isResumingTask}
                    file={file}
                    onFileChange={handleFileChange}
                    voiceLanguage={voiceLanguage}
                    setVoiceLanguage={setVoiceLanguage}
                    subtitleLanguage={subtitleLanguage}
                    setSubtitleLanguage={setSubtitleLanguage}
                    transcriptLanguage={transcriptLanguage}
                    setTranscriptLanguage={setTranscriptLanguage}
                    setTranscriptLangTouched={setTranscriptLangTouched}
                    videoResolution={videoResolution}
                    setVideoResolution={setVideoResolution}
                    uploading={uploading}
                    onCreate={handleUpload}
                    getFileTypeHint={getFileTypeHint}
                  />
                )}

                

                {/* Show Create button only when idle and after file selected */}
                

                {/* Below: Non-idle status panels remain visible below the upload box */}
                {status === "uploading" && (
                  <div className="upload-view">
                    {/* Entry mode toggle: Slides vs PDF are processed differently */}
                    <div
                      className="mode-toggle"
                      role="tablist"
                      aria-label="Entry Mode"
                    >
                      <button
                        type="button"
                        className={`toggle-btn ${uploadMode === "slides" ? "active" : ""}`}
                        onClick={() => setUploadMode("slides")}
                        role="tab"
                        aria-selected={uploadMode === "slides"}
                        aria-controls="slides-mode-panel"
                      >
                        🖼️ Slides
                      </button>
                      <button
                        type="button"
                        className={`toggle-btn ${uploadMode === "pdf" ? "active" : ""}`}
                        onClick={() => setUploadMode("pdf")}
                        role="tab"
                        aria-selected={uploadMode === "pdf"}
                        aria-controls="pdf-mode-panel"
                      >
                        📄 PDF
                      </button>
                    </div>
                    <div className="mode-explainer" aria-live="polite">
                      {uploadMode === "slides" ? (
                        <>
                          <strong>Slides Mode:</strong> Processes each slide
                          individually for transcripts, audio, subtitles, and
                          composes a final video.
                        </>
                      ) : (
                        <>
                          <strong>PDF Mode:</strong> Segments the document into
                          chapters, then you can generate either a video (with
                          audio + subtitles) or a 2‑person podcast (MP3).
                        </>
                      )}
                    </div>
                    {uploadMode === "pdf" && (
                      <div
                        className="mode-toggle"
                        role="tablist"
                        aria-label="PDF Output"
                      >
                        <button
                          type="button"
                          className={`toggle-btn ${pdfOutputMode === "video" ? "active" : ""}`}
                          onClick={() => setPdfOutputMode("video")}
                          role="tab"
                          aria-selected={pdfOutputMode === "video"}
                          aria-controls="pdf-output-video"
                        >
                          🎬 Video
                        </button>
                        <button
                          type="button"
                          className={`toggle-btn ${pdfOutputMode === "podcast" ? "active" : ""}`}
                          onClick={() => setPdfOutputMode("podcast")}
                          role="tab"
                          aria-selected={pdfOutputMode === "podcast"}
                          aria-controls="pdf-output-podcast"
                        >
                          🎧 Podcast
                        </button>
                      </div>
                    )}
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
                        accept={uploadMode === "pdf" ? ".pdf" : ".pptx,.ppt"}
                        onChange={handleFileChange}
                        className="file-input"
                        disabled={isResumingTask}
                      />
                      <label
                        htmlFor="file-upload"
                        className={`file-upload-label ${isResumingTask ? "disabled" : ""}`}
                      >
                        <div className="upload-icon">📄</div>
                        <div className="upload-text">
                          {file
                            ? file.name
                            : uploadMode === "pdf"
                              ? "Choose a PDF file"
                              : "Choose a PPTX/PPT file"}
                        </div>
                        <div className="upload-hint">
                          {file
                            ? getFileTypeHint(file.name)
                            : uploadMode === "pdf"
                              ? "PDF will be processed as chapters for video + audio + subtitles"
                              : "Slides will be processed per slide for video + audio + subtitles"}
                        </div>
                      </label>
                    </div>

                    <div className="video-options-section">
                      <div className="video-options-grid">
                        <div className="video-option-card">
                          <div className="video-option-header">
                            <span className="video-option-icon">🔊</span>
                            <span className="video-option-title">AUDIO LANGUAGE</span>
                          </div>
                          <select
                            id="language-select"
                            value={voiceLanguage}
                            onChange={(e) => setVoiceLanguage(e.target.value)}
                            className="video-option-select"
                          >
                            <option value="english">English</option>
                            <option value="simplified_chinese">简体中文</option>
                            <option value="traditional_chinese">
                              繁體中文
                            </option>
                            <option value="japanese">日本語</option>
                            <option value="korean">한국어</option>
                            <option value="thai">ไทย</option>
                          </select>
                        </div>

                        <div className="video-option-card">
                          <div className="video-option-header">
                            <span className="video-option-icon">📝</span>
                            <span className="video-option-title">
                              {uploadMode === 'pdf' && pdfOutputMode === 'podcast' ? 'Transcript Language' : 'Subtitles Language'}
                            </span>
                          </div>
                          <select
                            id="subtitle-language-select"
                            value={uploadMode === 'pdf' && pdfOutputMode === 'podcast' ? transcriptLanguage : subtitleLanguage}
                            onChange={(e) => {
                              const v = e.target.value;
                              if (uploadMode === 'pdf' && pdfOutputMode === 'podcast') { setTranscriptLanguage(v); setTranscriptLangTouched(true); }
                              else setSubtitleLanguage(v);
                            }}
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

                        {(uploadMode !== "pdf" ||
                          pdfOutputMode === "video") && (
                          <div className="video-option-card">
                            <div className="video-option-header">
                              <span className="video-option-icon">📺</span>
                              <span className="video-option-title">
                                Quality
                              </span>
                            </div>
                            <select
                              id="video-resolution-select"
                              value={videoResolution}
                              onChange={(e) =>
                                setVideoResolution(e.target.value)
                              }
                              className="video-option-select"
                            >
                              <option value="sd">SD (640×480)</option>
                              <option value="hd">HD (1280×720)</option>
                              <option value="fullhd">
                                Full HD (1920×1080)
                              </option>
                            </select>
                          </div>
                        )}
                      </div>
                    </div>

                    {uploadMode !== "pdf" && (
                      <div className="option-item minimal">
                        <input
                          type="checkbox"
                          id="generate-avatar"
                          checked={generateAvatar}
                          onChange={(e) => setGenerateAvatar(e.target.checked)}
                          disabled
                          title="AI Avatar is not available yet"
                        />
                        <label
                          htmlFor="generate-avatar"
                          className="minimal-label"
                        >
                          AI Avatar
                        </label>
                      </div>
                    )}

                    {/* Subtle AI Disclaimer in Upload View */}
                    <div className="ai-notice-subtle">
                      AI-generated content may contain inaccuracies. Review
                      carefully.
                    </div>

                    {file && (
                      <button
                        onClick={handleUpload}
                        className="primary-btn"
                        disabled={uploading}
                      >
                        {uploadMode === "pdf"
                          ? pdfOutputMode === "podcast"
                            ? "Create Podcast"
                            : "Create Video"
                          : "Create Video"}
                      </button>
                    )}
                  </div>
                )}

                {status === "uploading" && (
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

                {status === "processing" && processingDetails && (
                  <ProcessingView
                    apiBaseUrl={API_BASE_URL}
                    taskId={taskId}
                    fileId={fileId}
                    fileName={processingDetails?.filename || file?.name || null}
                    progress={progress}
                    onStop={handleStopProcessing}
                    processingDetails={processingDetails}
                    processingPreviewMode={processingPreviewMode}
                    setProcessingPreviewMode={setProcessingPreviewMode}
                    videoRef={videoRef}
                    audioRef={audioRef}
                    formatStepNameWithLanguages={formatStepNameWithLanguages}
                  />
                )}

                {status === "completed" && processingDetails && taskId && (
                  <CompletedView
                    apiBaseUrl={API_BASE_URL}
                    taskId={taskId}
                    processingDetails={processingDetails}
                    hasVideoAsset={hasVideoAsset}
                    completedTranscriptMd={completedTranscriptMd}
                    subtitleLanguageCode={subtitleLanguageCode}
                    subtitleLocale={subtitleLocale}
                    vttUrl={vttUrl}
                    completedMedia={completedMedia}
                    setCompletedMedia={setCompletedMedia}
                    completedMediaPinnedRef={completedMediaPinnedRef}
                    showCompletedBanner={showCompletedBanner}
                    setShowCompletedBanner={setShowCompletedBanner}
                    onResetForm={resetForm}
                  />
                )}

                

                {status === "error" && (
                  <div className="error-view">
                    <div className="error-icon">⚠️</div>
                    <h3>Processing Failed</h3>
                    <p className="error-message">
                      Something went wrong during video generation. Please try
                      again with a different file.
                    </p>
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
          <p className="footer-note">
            Powered by SlideSpeaker AI • Where presentations become your
            masterpiece
          </p>
          <div className="footer-right">
            <div
              className="health-indicator"
              role="status"
              aria-live="polite"
              title={queueUnavailable ? 'Queue unavailable' : (redisLatencyMs != null ? `Queue OK • ${redisLatencyMs}ms` : 'Queue OK')}
            >
              <span className={`dot ${queueUnavailable ? 'down' : 'ok'}`} aria-hidden />
              <span className="label">{queueUnavailable ? 'Queue: Unavailable' : 'Queue: OK'}</span>
            </div>
            <div
              className="view-toggle theme-toggle"
              role="tablist"
              aria-label="Theme Toggle"
            >
            <button
              onClick={() => setUiTheme("classic")}
              className={`toggle-btn ${uiTheme === "classic" ? "active" : ""}`}
              title="Classic Theme"
              role="tab"
              aria-selected={uiTheme === "classic"}
              aria-controls="classic-theme-panel"
            >
              <span className="toggle-text">Classic</span>
            </button>
            <button
              onClick={() => setUiTheme("flat")}
              className={`toggle-btn ${uiTheme === "flat" ? "active" : ""}`}
              title="Flat Theme"
              role="tab"
              aria-selected={uiTheme === "flat"}
              aria-controls="flat-theme-panel"
            >
              <span className="toggle-text">Flat</span>
            </button>
            <button
              onClick={() => setUiTheme("material")}
              className={`toggle-btn ${uiTheme === "material" ? "active" : ""}`}
              title="Material Theme"
              role="tab"
              aria-selected={uiTheme === "material"}
              aria-controls="material-theme-panel"
            >
              <span className="toggle-text">Material</span>
            </button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

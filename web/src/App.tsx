import React, { useState, useRef, useEffect, useMemo } from "react";
import axios from "axios";
import "./App.scss";
// Ultra-flat design styles
import "./styles/ultra-flat-overrides.scss";
import "./styles/subtle-material-overrides.scss";
import TaskMonitor from "./components/TaskMonitor";
import { getStepLabel } from './utils/stepLabels';
import PodcastTranscript from './components/PodcastTranscript';

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

  // Apply/remove ultra-flat class based on theme
  useEffect(() => {
    const isFlat = uiTheme === "flat";
    const isMaterial = uiTheme === "material";
    document.body.classList.toggle("ultra-flat", isFlat);
    document.body.classList.toggle("subtle-material", isMaterial);
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
  const [showTaskMonitor, setShowTaskMonitor] = useState<boolean>(false);
  const [uploadMode, setUploadMode] = useState<"slides" | "pdf">("slides");
  const [pdfOutputMode, setPdfOutputMode] = useState<"video" | "podcast">(
    "video",
  );
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [completedVideoLoading, setCompletedVideoLoading] = useState<boolean>(false);
  const [completedAudioLoading, setCompletedAudioLoading] = useState<boolean>(false);
  type Cue = { start: number; end: number; text: string };
  const [audioCues, setAudioCues] = useState<Cue[]>([]);
  const [activeAudioCueIdx, setActiveAudioCueIdx] = useState<number | null>(
    null,
  );
  const audioTranscriptRef = useRef<HTMLDivElement>(null);
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
  // Global health (footer indicator)
  const [queueUnavailable, setQueueUnavailable] = useState<boolean>(false);
  const [redisLatencyMs, setRedisLatencyMs] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/api/health`, { headers: { Accept: 'application/json' } });
        if (!resp.ok) throw new Error('health not ok');
        const data = await resp.json();
        if (!cancelled) {
          const ok = data?.redis?.ok === true;
          setQueueUnavailable(!ok);
          const lat = typeof data?.redis?.latency_ms === 'number' ? data.redis.latency_ms : null;
          setRedisLatencyMs(lat !== null ? Math.round(lat) : null);
        }
      } catch {
        if (!cancelled) {
          setQueueUnavailable(true);
          setRedisLatencyMs(null);
        }
      }
    };
    check();
    const id = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);
  const [showAudioTranscript, setShowAudioTranscript] =
    useState<boolean>(false);
  const [audioCuesLoaded, setAudioCuesLoaded] = useState<boolean>(false);
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
  // Completed view: subtitles (VTT) under audio (reuse global Cue/audioCues/activeAudioCueIdx)
  // Removed unused completedTranscriptRef

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
      const response = await axios.post(
        "/api/upload",
        {
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
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total,
              );
              setProgress(percentCompleted);
            }
          },
        },
      );

      setFileId(response.data.file_id);
      setTaskId(response.data.task_id);
      setStatus("processing");
      setProgress(0);
    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload failed. Please try again.");
      setUploading(false);
      setStatus("idle");
    }
  };

  const handleStopProcessing = async () => {
    if (!taskId) return;

    try {
      const response = await axios.post<{ message: string }>(
        `/api/task/${taskId}/cancel`,
      );
      console.log("Stop processing response:", response.data);

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

  // Fetch VTT and build cues for Completed view audio transcript when user plays audio
  useEffect(() => {
    const loadVtt = async () => {
      if (
        status !== "completed" ||
        !taskId ||
        !showAudioTranscript ||
        audioCuesLoaded
      )
        return;
      {
        const tt = ((((processingDetails as any)?.task_type) || '').toLowerCase());
        const isPodcast = ["podcast", "both"].includes(tt);
        if (isPodcast) return; // podcast has no VTT
      }
      try {
        const lang =
          processingDetails?.subtitle_language ||
          subtitleLanguage ||
          voiceLanguage ||
          "english";
        const resp = await fetch(
          `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(lang)}`,
          { headers: { Accept: "text/vtt,*/*" } },
        );
        if (!resp.ok) return;
        const text = await resp.text();
        // Parse WebVTT into cues
        const lines = text.split(/\r?\n/);
        const parsed: Cue[] = [];
        let i = 0;
        const timeRe =
          /(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})\.(\d{3})/;
        while (i < lines.length) {
          const line = lines[i].trim();
          if (!line) {
            i++;
            continue;
          }
          if (line.toUpperCase() === "WEBVTT" || /^\d+$/.test(line)) {
            i++;
            continue;
          }
          const m = line.match(timeRe);
          if (m) {
            const toSec = (h: string, m: string, s: string, ms: string) =>
              parseInt(h, 10) * 3600 +
              parseInt(m, 10) * 60 +
              parseInt(s, 10) +
              parseInt(ms, 10) / 1000;
            const start = toSec(m[1], m[2], m[3], m[4]);
            const end = toSec(m[5], m[6], m[7], m[8]);

            // Validate timing and prepare to split overly long cues for better UX
            const duration = end - start;
            // Only warn for extremely long cues to avoid noisy logs
            if (duration > 30) {
              console.warn(
                `Unusually long subtitle duration detected: ${duration.toFixed(2)}s`,
                { start, end, text: lines[i + 1] },
              );
            }

            // Ensure end time is after start time
            if (end <= start) {
              console.warn("Invalid subtitle timing detected", { start, end });
              i++;
              continue;
            }

            i++;
            const textLines: string[] = [];
            while (i < lines.length && lines[i].trim() !== "") {
              textLines.push(lines[i]);
              i++;
            }
            const cueText = textLines.join("\n");

            // Split long cues by punctuation and allocate time proportionally for transcript sync
            // Video track remains unchanged; this only impacts the audio transcript pane.
            // Language-aware cap per segment (Medium profile)
            const langKey = (lang || "").toLowerCase();
            const MAX_SEGMENT =
              langKey === "simplified_chinese" ||
              langKey === "traditional_chinese" ||
              langKey === "japanese" ||
              langKey === "korean"
                ? 5.5
                : langKey === "thai"
                  ? 6.0
                  : 7.0;
            if (duration > MAX_SEGMENT + 0.01) {
              // Try punctuation-aware splitting first
              const parts = cueText
                .split(/(?<=[。！？；.!?;])\s+|(?<=[，、,])\s+/)
                .map((p) => p.trim())
                .filter(Boolean);
              if (parts.length > 1) {
                // Weight by non-space length
                const lens = parts.map(
                  (p) => p.replace(/\s+/g, "").length || 1,
                );
                const total = lens.reduce((a, b) => a + b, 0) || 1;
                let cursor = start;
                const localSegs: {
                  start: number;
                  end: number;
                  text: string;
                }[] = [];
                const MIN_CUE = 0.9;
                for (let idx = 0; idx < parts.length; idx++) {
                  const weight = lens[idx] / total;
                  let dur = duration * weight;
                  // Cap by MAX_SEGMENT and spill into multiple slices if needed
                  while (dur > MAX_SEGMENT + 1e-6) {
                    const segEnd = Math.min(end, cursor + MAX_SEGMENT);
                    localSegs.push({
                      start: cursor,
                      end: segEnd,
                      text: parts[idx],
                    });
                    cursor = segEnd;
                    dur -= MAX_SEGMENT;
                  }
                  if (dur > 1e-3) {
                    let segEnd = Math.min(end, cursor + dur);
                    // If this last slice would be ultra-short next to previous, merge into previous
                    if (localSegs.length > 0 && segEnd - cursor < MIN_CUE) {
                      const last = localSegs[localSegs.length - 1];
                      // Extend previous end
                      last.end = segEnd;
                      // Join text
                      last.text = `${last.text} ${parts[idx]}`.trim();
                    } else {
                      localSegs.push({
                        start: cursor,
                        end: segEnd,
                        text: parts[idx],
                      });
                    }
                    cursor = segEnd;
                  }
                }
                // Also merge any internal ultra-short segments
                const merged: typeof localSegs = [];
                for (const seg of localSegs) {
                  if (merged.length > 0 && seg.end - seg.start < MIN_CUE) {
                    const last = merged[merged.length - 1];
                    last.end = seg.end;
                    last.text = `${last.text} ${seg.text}`.trim();
                  } else {
                    merged.push(seg);
                  }
                }
                for (const seg of merged) parsed.push(seg);
              } else {
                // Fallback to equal time slices with repeated text
                const segments = Math.max(2, Math.ceil(duration / MAX_SEGMENT));
                const segLen = duration / segments;
                for (let s = 0; s < segments; s++) {
                  const segStart = start + s * segLen;
                  const segEnd = Math.min(end, segStart + segLen);
                  parsed.push({ start: segStart, end: segEnd, text: cueText });
                }
              }
            } else {
              parsed.push({ start, end, text: cueText });
            }
          } else {
            i++;
          }
        }
        // Deduplicate and merge adjacent cues with identical text
        const round = (x: number) => Math.round(x * 1000) / 1000; // 1ms precision
        const seen = new Set<string>();
        const unique: Cue[] = [];
        for (const c of parsed) {
          const key = `${round(c.start)}|${round(c.end)}|${c.text}`;
          if (!seen.has(key)) {
            seen.add(key);
            unique.push({ start: c.start, end: c.end, text: c.text });
          }
        }
        unique.sort((a, b) => a.start - b.start || a.end - b.end);
        const merged: Cue[] = [];
        const EPS = 0.1; // merge gap <=100ms
        for (const c of unique) {
          const last = merged[merged.length - 1];
          if (last && last.text === c.text && c.start - last.end <= EPS) {
            last.end = Math.max(last.end, c.end);
          } else {
            merged.push({ ...c });
          }
        }
        setAudioCues(merged);
        setAudioCuesLoaded(true);
      } catch (error) {
        console.error("Error loading VTT file:", error);
      }
    };
    loadVtt();
  }, [
    status,
    taskId,
    processingDetails,
    subtitleLanguage,
    voiceLanguage,
    showAudioTranscript,
    audioCuesLoaded,
  ]);

  // Reset transcript state when task/status changes
  useEffect(() => {
    setShowAudioTranscript(false);
    setAudioCuesLoaded(false);
    setAudioCues([]);
    setActiveAudioCueIdx(null);
    // Show banner on transition to completed unless user dismissed it previously
    if (status === "completed") {
      try {
        const flag = localStorage.getItem("ss_show_completed_banner");
        setShowCompletedBanner(flag !== "0");
      } catch {}
    }
    // Completed view initializes subtitles from processing details only (not editable)
  }, [taskId, status]);

  // Only show transcript after user initiates audio playback
  useEffect(() => {
    if (status !== "completed") return;
    const el = audioRef.current;
    if (!el) return;
    const onPlay = () => {
      setShowAudioTranscript(true);
      // Auto-hide banner on first media interaction
      if (showCompletedBanner) {
        setShowCompletedBanner(false);
        try {
          localStorage.setItem("ss_show_completed_banner", "0");
        } catch {}
      }
    };
    el.addEventListener("play", onPlay);
    return () => {
      el.removeEventListener("play", onPlay);
    };
  }, [status, taskId, showCompletedBanner, completedMedia, audioRef]);

  // Detect actual video availability via HEAD for Completed view (covers legacy tasks)
  const [hasVideoAsset, setHasVideoAsset] = useState<boolean>(false);
  useEffect(() => {
    if (status !== 'completed' || !taskId) { setHasVideoAsset(false); return; }
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/video`, { method: 'HEAD' });
        if (!cancelled) setHasVideoAsset(resp.ok);
      } catch {
        if (!cancelled) setHasVideoAsset(false);
      }
    })();
    return () => { cancelled = true; };
  }, [status, taskId]);

  // Stable task type for dependency-light effects
  const taskType = useMemo(() => {
    return ((((processingDetails as any)?.task_type) || '').toLowerCase());
  }, [processingDetails]);

  // Fetch conversation transcript for Completed view when podcast is generated
  const [completedTranscriptMd, setCompletedTranscriptMd] = useState<string | null>(null);
  useEffect(() => {
    const fetchCompletedTranscript = async () => {
      if (status !== 'completed' || !taskId) { setCompletedTranscriptMd(null); return; }
      if (!(["podcast","both"].includes(taskType))) { setCompletedTranscriptMd(null); return; }
      try {
        const resp = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/transcripts/markdown`, { headers: { Accept: 'text/markdown' } });
        if (resp.ok) {
          const text = await resp.text();
          setCompletedTranscriptMd(text);
        } else {
          setCompletedTranscriptMd(null);
        }
      } catch {
        setCompletedTranscriptMd(null);
      }
    };
    fetchCompletedTranscript();
  }, [status, taskId, taskType]);

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

  // When user switches to Video tab, show loading until the video is ready
  useEffect(() => {
    if (status !== 'completed') return;
    if (completedMedia === 'video') {
      setCompletedVideoLoading(true);
    }
  }, [status, completedMedia]);

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

  // Load VTT cues for Completed view when on Audio tab and not a podcast
  useEffect(() => {
    if (status !== 'completed' || completedMedia !== 'audio' || !taskId) { setAudioCues([]); return; }
    const isPodcast = (taskType === 'podcast');
    if (isPodcast) { setAudioCues([]); return; }
    const lang = (processingDetails as any)?.subtitle_language || subtitleLanguage || voiceLanguage || 'english';
    const urlWithLang = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(lang)}`;
    const urlNoLang = `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt`;
    let cancelled = false;
    (async () => {
      try {
        let resp = await fetch(urlWithLang, { headers: { Accept: 'text/vtt,*/*' } });
        if (!resp.ok) resp = await fetch(urlNoLang, { headers: { Accept: 'text/vtt,*/*' } });
        if (cancelled) return;
        if (!resp.ok) { setAudioCues([]); return; }
        const text = await resp.text();
        const lines = text.split(/\r?\n/);
        const cues: any[] = [];
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
      } catch { setAudioCues([]); }
    })();
    return () => { cancelled = true; };
  }, [status, completedMedia, taskType, taskId, processingDetails, subtitleLanguage, voiceLanguage]);

  // Sync active cue with audio time and auto-scroll (Completed view)
  useEffect(() => {
    if (status !== 'completed' || completedMedia !== 'audio' || audioCues.length === 0) return;
    const audio = audioRef.current;
    if (!audio) return;
    const EPS = 0.03;
    const findIdx = (t: number): number | null => {
      let lo = 0, hi = audioCues.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const c = audioCues[mid];
        if (t < c.start - EPS) hi = mid - 1; else if (t > c.end + EPS) lo = mid + 1; else return mid;
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
    const onSeeked = () => { const t = audio.currentTime; const idx = findIdx(t); setActiveAudioCueIdx(idx); };
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
  }, [status, completedMedia, audioCues]);

  // Sync active cue with audio time (RAF-driven for smoothness)
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || audioCues.length === 0) return;

    const EPS = 0.03;
    const findIdx = (t: number): number | null => {
      // Binary search on sorted cues
      let lo = 0,
        hi = audioCues.length - 1;
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

    const start = () => {
      if (rafId == null) rafId = requestAnimationFrame(tick);
    };
    const stop = () => {
      if (rafId != null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    };
    const onPlay = () => start();
    const onPause = () => stop();
    const onEnded = () => stop();
    const onSeeked = () => {
      const idx = findIdx(audio.currentTime);
      setActiveAudioCueIdx(idx);
    };

    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("seeked", onSeeked);
    // Kick once in case we're already playing
    if (!audio.paused) start();
    else onSeeked();
    return () => {
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("seeked", onSeeked);
      stop();
    };
  }, [audioCues]);

  // Auto-scroll transcript to active cue
  useEffect(() => {
    if (activeAudioCueIdx === null) return;
    const container = audioTranscriptRef.current;
    if (!container) return;
    const el = container.querySelector(
      `#audio-cue-${activeAudioCueIdx}`,
    ) as HTMLElement | null;
    if (!el) return;
    try {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
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

  // Poll for status updates when processing
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    if (status === "processing" && taskId) {
      const checkStatus = async () => {
        try {
          const response = await axios.get<ProcessingDetails>(
            `/api/tasks/${taskId}/progress`,
          );
          setProcessingDetails(response.data);

          if (response.data.status === "completed") {
            setStatus("completed");
            setUploading(false);
            setProgress(100);
            // Preserve taskId so task-based endpoints remain valid in the completed view
            // Do not clear local storage here to keep task metadata available
          } else if (
            response.data.status === "processing" ||
            response.data.status === "uploaded"
          ) {
            setStatus("processing");
            setProgress(response.data.progress);
          } else if (response.data.status === "cancelled") {
            // Move back to upload view on cancellation
            setUploading(false);
            setTaskId(null);
            setFileId(null);
            setFile(null);
            setProcessingDetails(null);
            setProgress(0);
            localStorageUtils.clearTaskState();
            setStatus("idle");
          } else if (response.data.status === "failed") {
            setStatus("error");
            setUploading(false);
            setTaskId(null);

            // Clear local storage when failed
            localStorageUtils.clearTaskState();
          } else {
            setStatus("error");
            setUploading(false);
            setTaskId(null);

            // Clear local storage when error
            localStorageUtils.clearTaskState();
          }
        } catch (error) {
          // Avoid forcing error state on transient issues; keep polling.
          console.warn("Status check error (transient, will retry):", error);
        }
      };

      // Check status immediately
      checkStatus();

      // Set up interval to check status frequently for better sync
      intervalId = setInterval(checkStatus, 3000);
    }

    // Cleanup function to clear interval
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [status, taskId]);

  // Ensure taskId is populated in completed view (fallback via stats search)
  useEffect(() => {
    const hydrateTaskId = async () => {
      if (status === "completed" && fileId && (!taskId || taskId === "null")) {
        try {
          const res = await axios.get(
            `/api/tasks/search?query=${encodeURIComponent(fileId)}`,
          );
          const tasks = Array.isArray(res.data?.tasks) ? res.data.tasks : [];
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
          const res = await axios.get(
            `/api/tasks/search?query=${encodeURIComponent(fileId)}`,
          );
          const tasks = Array.isArray(res.data?.tasks) ? res.data.tasks : [];
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

  const getProcessingStatusMessage = (): string => {
    if (!processingDetails) {
      const name = (file?.name || "").toLowerCase();
      const isPdf = name.endsWith(".pdf");
      return isPdf
        ? "Bringing Your PDF to Life"
        : "Bringing Your Presentation to Life";
    }

    const activeSteps = Object.entries(processingDetails.steps || {}).filter(
      ([_, step]) =>
        step.status === "in_progress" || step.status === "processing",
    );

    const isPdf = ((processingDetails as any)?.file_ext || file?.name || "")
      .toLowerCase()
      .endsWith(".pdf");
    const fileTypeText = isPdf ? "PDF" : "PPT";

    if (activeSteps.length > 0) {
      const currentStepKey = activeSteps[0][0];
      const stepName = formatStepNameWithLanguages(
        currentStepKey,
        processingDetails.voice_language || "english",
        processingDetails.subtitle_language ||
          processingDetails.voice_language ||
          "english",
      );
      const statusMessages: Record<string, string> = {
        // Common messages for all file types
        "Extracting Slides": `Analyzing your ${fileTypeText} structure...`,
        "Analyzing Content": `Examining ${fileTypeText} content...`,
        "Generating Transcripts": "Generating transcripts...",
        "Revising Transcripts": "Polishing transcripts for delivery...",
        "Translating Voice Transcripts": "Translating transcripts...",
        "Translating Subtitle Transcripts": "Translating transcripts...",
        "Translating Transcripts": "Translating transcripts...",
        "Generating Subtitle Transcripts": "Generating subtitle transcripts...",
        "Reviewing Subtitles": "Perfecting subtitle timing and accuracy...",
        "Generating Audio": "Creating natural voice narration...",
        "Creating Avatar": "Bringing AI presenter to life...",
        "Converting Slides": `Preparing ${fileTypeText} for video composition...`,
        "Creating Video Frames": isPdf
          ? "Creating visual representations for chapters..."
          : "Creating visual representations for slides...",
        "Composing Video": "Bringing all elements together...",
        // Podcast messages
        "Generating Podcast Script": "Drafting a two-person conversation...",
        "Translating Podcast Script": "Translating podcast dialogue...",
        "Generating Podcast Audio": "Recording multi-voice podcast...",
        "Composing Podcast": "Mixing podcast audio...",
      };
      return statusMessages[stepName] || `Working on: ${stepName}`;
    }

    return isPdf
      ? "Bringing Your PDF to Life"
      : "Bringing Your Presentation to Life";
  };

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
                            ? "PDF will be processed into a video or podcast"
                            : "Slides will be processed into a narrated video"}
                      </div>
                    </label>

                    {/* Options */}
                    <div className="options-panel">
                      <div className="video-option-card">
                        <div className="video-option-header">
                          <span className="video-option-icon">🌐</span>
                          <span className="video-option-title">AUDIO LANGUAGE</span>
                        </div>
                        <select
                          id="voice-language-select"
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

                      {(uploadMode !== "pdf" || pdfOutputMode === "video") && (
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
                      )}
                    </div>
                  </div>

                  {/* Subtle AI Disclaimer in Upload View */}
                  <div className="ai-notice-subtle">
                    AI-generated content may contain inaccuracies. Review carefully.
                  </div>

                </div>
                )}

                {/* Show Create button only when idle and after file selected */}
                {status === 'idle' && file && (
                  <button
                    onClick={handleUpload}
                    className="primary-btn"
                    disabled={uploading}
                  >
                    {uploadMode === 'pdf'
                      ? (pdfOutputMode === 'podcast' ? 'Create Podcast' : 'Create Video')
                      : 'Create Video'}
                  </button>
                )}

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

                {status === "processing" && (
                  <div className="processing-view">
                    <div className="spinner"></div>
                    <h3>{getProcessingStatusMessage()}</h3>
                    {/* Meta header: filename + task id */}
                    <div
                      className="processing-meta"
                      role="group"
                      aria-label="Task Meta"
                    >
                      <div
                        className="meta-card file"
                        title={
                          processingDetails?.filename ||
                          file?.name ||
                          fileId ||
                          ""
                        }
                      >
                        <div className="meta-title">
                          <span className="meta-icon">📄</span>
                          <span className="meta-text">
                            {processingDetails?.filename ||
                              file?.name ||
                              "Untitled"}
                          </span>
                        </div>
                        <div className="meta-badge">
                          {(
                            (processingDetails as any)?.file_ext ||
                            file?.name ||
                            ""
                          )
                            .toLowerCase()
                            .endsWith(".pdf") ? (
                            <span className="file-type-badge pdf">PDF</span>
                          ) : (
                            <span className="file-type-badge ppt">PPT</span>
                          )}
                        </div>
                      </div>
                      <div
                        className="meta-card task"
                        title={taskId || fileId || ""}
                      >
                        <div className="meta-title">
                          <span className="meta-icon">🆔</span>
                        </div>
                        <div className="meta-actions">
                          <code
                            className={`meta-code ${taskId ? "clickable" : ""}`}
                            aria-label={`Task ID: ${taskId || "locating"} (press Enter to copy)`}
                            role="button"
                            tabIndex={taskId ? 0 : -1}
                            onClick={() => {
                              if (taskId) {
                                navigator.clipboard.writeText(taskId);
                                alert("Task ID copied!");
                              }
                            }}
                            onKeyDown={(e) => {
                              if (!taskId) return;
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                try {
                                  navigator.clipboard.writeText(taskId);
                                  alert("Task ID copied!");
                                } catch (err) {
                                  console.error("Failed to copy task id", err);
                                }
                              }
                            }}
                            title={taskId || undefined}
                          >
                            {taskId || "(locating…)"}
                          </code>
                          {!taskId && (
                            <span className="meta-hint">
                              from file {fileId?.slice(0, 8) || "…"}
                            </span>
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
                        <h4>
                          <span className="steps-title">🌟 Crafting Your Masterpiece</span>
                          <span className="output-badges">
                            {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); const v = ["video","both"].includes(tt); return v; })() && (
                              <span className="output-pill video" title="Video generation enabled">🎬 Video</span>
                            )}
                            {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); const p = ["podcast","both"].includes(tt); return p; })() && (
                              <span className="output-pill podcast" title="Podcast generation enabled">🎧 Podcast</span>
                            )}
                          </span>
                        </h4>
                        {/* Meta moved into header */}
                        <div className="steps-grid">
                          {(
                            (processingDetails as any)?.file_ext ||
                            file?.name ||
                            ""
                          )
                            .toLowerCase()
                            .endsWith(".pdf")
                            ? (() => {
                                const vl = (
                                  processingDetails.voice_language || "english"
                                ).toLowerCase();
                                const sl = (
                                  processingDetails.subtitle_language || vl
                                ).toLowerCase();
                                const same = vl === sl;
                                const tt = (((processingDetails as any)?.task_type)||'').toLowerCase();
                                const genVideo = ["video","both"].includes(tt);
                                const genPodcast = ["podcast","both"].includes(tt);
                                const showSectionHeaders = genVideo && genPodcast;
                                const base: string[] = [
                                  "segment_pdf_content",
                                ];
                                // Video-only preparation steps (not used by podcast pipeline)
                                const videoPrep: string[] = [
                                  "revise_pdf_transcripts",
                                  "translate_voice_transcripts",
                                  "translate_subtitle_transcripts",
                                ];
                                const videoSteps = genVideo
                                  ? [
                                      "generate_pdf_chapter_images",
                                      "generate_pdf_audio",
                                      "generate_pdf_subtitles",
                                      "compose_video",
                                    ]
                                  : [];
                                const podcastSteps = genPodcast
                                  ? [
                                      "generate_podcast_script",
                                      "translate_podcast_script",
                                      "generate_podcast_audio",
                                      "compose_podcast",
                                    ]
                                  : [];

                                const renderStep = (stepName: string) => {
                                  const stepData =
                                    processingDetails.steps[stepName];
                                  if (
                                    !stepData ||
                                    stepData.status === "skipped"
                                  )
                                    return null;
                                  if (
                                    same &&
                                    stepName ===
                                      "translate_subtitle_transcripts"
                                  )
                                    return null;
                                  return (
                                    <div
                                      key={stepName}
                                      className={`step-item ${stepData.status}`}
                                    >
                                      <span className="step-icon">
                                        {stepData.status === "completed"
                                          ? "✓"
                                          : stepData.status === "processing" ||
                                              stepData.status === "in_progress"
                                            ? "⏳"
                                            : stepData.status === "failed"
                                              ? "✗"
                                              : "○"}
                                      </span>
                                      <span className="step-name">
                                        {formatStepNameWithLanguages(
                                          stepName,
                                          vl,
                                          sl,
                                        )}
                                      </span>
                                    </div>
                                  );
                                };

                                return (
                                  <>
                                    {/* Base steps */}
                                    {base.map(renderStep)}
                                    {/* Video preparation steps */}
                                    {genVideo && videoPrep.map(renderStep)}
                                    {/* Video pipeline steps */}
                                    {videoSteps.length > 0 && (
                                      <>
                                        {showSectionHeaders && (
                                          <div className="steps-subtitle">🎬 Video Generation</div>
                                        )}
                                        {videoSteps.map(renderStep)}
                                      </>
                                    )}
                                    {/* Podcast pipeline steps */}
                                    {podcastSteps.length > 0 && (
                                      <>
                                        {showSectionHeaders && (
                                          <div className="steps-subtitle">🎧 Podcast Generation</div>
                                        )}
                                        {podcastSteps.map(renderStep)}
                                      </>
                                    )}
                                  </>
                                );
                              })()
                            : // PPT/PPTX-specific steps with translation steps
                              [
                                "extract_slides",
                                "convert_slides_to_images",
                                "analyze_slide_images",
                                "generate_transcripts",
                                "revise_transcripts",
                                "translate_voice_transcripts",
                                "translate_subtitle_transcripts",
                                "generate_audio",
                                "generate_avatar_videos",
                                "generate_subtitles",
                                "compose_video",
                              ]
                                .map((stepName) => {
                                  const stepData =
                                    processingDetails.steps[stepName];
                                  // Hide steps that are not present or explicitly skipped
                                  if (
                                    !stepData ||
                                    stepData.status === "skipped"
                                  ) {
                                    return null;
                                  }
                                  const vl = (
                                    processingDetails.voice_language ||
                                    "english"
                                  ).toLowerCase();
                                  const sl = (
                                    processingDetails.subtitle_language || vl
                                  ).toLowerCase();
                                  const same = vl === sl;
                                  if (
                                    same &&
                                    stepName ===
                                      "translate_subtitle_transcripts"
                                  ) {
                                    return null; // collapse duplicate translate step
                                  }
                                  return (
                                    <div
                                      key={stepName}
                                      className={`step-item ${stepData.status}`}
                                    >
                                      <span className="step-icon">
                                        {stepData.status === "completed"
                                          ? "✓"
                                          : stepData.status === "processing" ||
                                              stepData.status === "in_progress"
                                            ? "⏳"
                                            : stepData.status === "failed"
                                              ? "✗"
                                              : "○"}
                                      </span>
                                      <span className="step-name">
                                        {formatStepNameWithLanguages(
                                          stepName,
                                          vl,
                                          sl,
                                        )}
                                      </span>
                                    </div>
                                  );
                                })
                                .filter(Boolean)}
                        </div>
                        {(() => {
                          const steps = (processingDetails as any)?.steps || {};
                          const hasVideoReady = Boolean(steps['compose_video']?.status === 'completed');
                          const hasPodcastReady = Boolean(steps['compose_podcast']?.status === 'completed');
                          if (!hasVideoReady && !hasPodcastReady) return null;
                          const mode = hasVideoReady ? (processingPreviewMode || 'video') : 'audio';
                          return (
                            <div className="preview-block">
                              {hasVideoReady && mode !== 'video' && (
                                <div className="preview-toggle">
                                  <button type="button" className={`toggle-btn`} onClick={() => setProcessingPreviewMode('video')}>
                                    ▶️ Watch
                                  </button>
                                </div>
                              )}
                              {mode === 'video' && hasVideoReady && (
                                <div className="video-preview-block" style={{ marginBottom: 12 }}>
                                  <video
                                    ref={videoRef}
                                    controls
                                    playsInline
                                    preload="metadata"
                                    crossOrigin="anonymous"
                                    src={`${API_BASE_URL}/api/tasks/${taskId}/video`}
                                    style={{ width: '100%', borderRadius: 8 }}
                                    aria-label={`Video preview for task ${taskId}`}
                                  />
                                </div>
                              )}
                              {mode === 'audio' && (
                                <div className="audio-preview-block">
                                  <audio
                                    ref={audioRef}
                                    controls
                                    preload="auto"
                                    src={`${API_BASE_URL}/api/tasks/${taskId}/${(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); const p = ["podcast","both"].includes(tt); return p ? 'podcast' : 'audio'; })()}`}
                                    crossOrigin="anonymous"
                                    aria-label="Audio narration preview"
                                  />
                                </div>
                              )}
                            </div>
                          );
                        })()}

                        {processingDetails.errors &&
                          processingDetails.errors.length > 0 && (
                            <div className="error-section">
                              <h4>Errors Encountered</h4>
                              <div className="error-list">
                                {processingDetails.errors.map(
                                  (error, index) => {
                                    const vl = (
                                      processingDetails.voice_language ||
                                      "english"
                                    ).toLowerCase();
                                    const sl = (
                                      processingDetails.subtitle_language || vl
                                    ).toLowerCase();
                                    return (
                                      <div key={index} className="error-item">
                                        <strong>
                                          {formatStepNameWithLanguages(
                                            error.step,
                                            vl,
                                            sl,
                                          )}
                                          :
                                        </strong>{" "}
                                        {error.error}
                                      </div>
                                    );
                                  },
                                )}
                              </div>
                            </div>
                          )}
                      </div>
                    )}

                    {/* Processing transcript preview intentionally hidden to avoid duplicate/early transcript view */}
                  </div>
                )}

                {status === "completed" && (
                  <div className="completed-view">
                    {showCompletedBanner && (
                      <div className="completed-banner">
                        <div className="success-icon">✓</div>
                        <h3>
                          Your Masterpiece is Ready!
                          <span
                            style={{ marginLeft: "8px" }}
                            className="output-badges"
                            aria-label="Outputs included"
                          >
                            {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); return ["video","both"].includes(tt); })() && (
                              <span
                                className="output-pill video"
                                title="Includes video"
                              >
                                🎬 Video
                              </span>
                            )}
                            {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); return ["podcast","both"].includes(tt); })() && (
                              <span
                                className="output-pill podcast"
                                title="Includes podcast"
                              >
                                🎧 Podcast
                              </span>
                            )}
                          </span>
                        </h3>
                        <p className="success-message">
                          Congratulations! Your presentation has been
                          transformed into an engaging AI-powered video.
                        </p>
                        <button
                          type="button"
                          className="banner-dismiss"
                          aria-label="Dismiss banner"
                          onClick={() => {
                            setShowCompletedBanner(false);
                            try {
                              localStorage.setItem(
                                "ss_show_completed_banner",
                                "0",
                              );
                            } catch {}
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    )}

                    {/* Tabs for switching media mode - placed at the top for better visibility */}
                    <div className="mode-toggle-container">
                      {/* Echo output badges near mode toggle for clarity */}
                      <div
                        className="mode-toggle-header"
                        style={{
                          display: "flex",
                          justifyContent: "flex-end",
                          marginBottom: "8px",
                        }}
                      >
                        {/* legacy output badges block removed */}
                      </div>
                      <div className="mode-toggle compact">
                        {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); return ["video","both"].includes(tt) || hasVideoAsset; })() && (
                          <button
                            type="button"
                            className={`toggle-btn ${completedMedia === "video" ? "active" : ""}`}
                            onClick={() => { completedMediaPinnedRef.current = true; setCompletedMedia("video"); }}
                          >
                            🎬 Video
                          </button>
                        )}
                        <button
                          type="button"
                          className={`toggle-btn ${completedMedia === "audio" ? "active" : ""}`}
                          onClick={() => { completedMediaPinnedRef.current = true; setCompletedMedia("audio"); }}
                        >
                          {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); return ["podcast","both"].includes(tt); })()
                            ? "🎧 Podcast"
                            : "🎧 Audio"}
                        </button>
                      </div>
                    </div>

                    {/* Video area (shows only in Video mode) */}
                    {completedMedia === "video" &&
                      (() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); return ["video","both"].includes(tt) || hasVideoAsset; })() && (
                        <div className="media-section video-active">
                          <div className="video-wrapper">
                            <video
                              ref={videoRef}
                              controls
                              src={`${API_BASE_URL}/api/tasks/${taskId}/video`}
                              crossOrigin="anonymous"
                              className="preview-video-large"
                              onLoadStart={() => setCompletedVideoLoading(true)}
                              onLoadedMetadata={() => setCompletedVideoLoading(false)}
                              onLoadedData={() => setCompletedVideoLoading(false)}
                              onCanPlay={() => setCompletedVideoLoading(false)}
                              onPlaying={() => setCompletedVideoLoading(false)}
                              onWaiting={() => setCompletedVideoLoading(true)}
                            >
                              {/* Always include a subtitles track for the completed view */}
                              <track
                                kind="subtitles"
                                src={vttUrl}
                                srcLang={subtitleLocale}
                                label={getLanguageDisplayName(subtitleLanguageCode)}
                                default
                              />
                            </video>
                            {completedVideoLoading && (
                              <div className="video-status-overlay loading" role="status" aria-live="polite">
                                <div className="spinner" aria-hidden></div>
                                <span className="loading-text">Loading video…</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                    {/* Audio area (shows only in Audio mode) */}
                    {completedMedia === "audio" && (
                      <div className="media-section audio-active">
                        <div className="audio-section" style={{ position: 'relative' }}>
                          {/* Inline audio player for quick listening */}
                          <div className="audio-player-inline">
                          <audio
                            ref={audioRef}
                            controls
                            preload="auto"
                            src={`${API_BASE_URL}/api/tasks/${taskId}/${(() => { const tt = ((((processingDetails as any)?.task_type)||'').toLowerCase()); return (tt === 'podcast') ? 'podcast' : 'audio'; })()}`}
                            crossOrigin="anonymous"
                            aria-label="Audio narration preview"
                            onLoadStart={() => setCompletedAudioLoading(true)}
                            onLoadedData={() => setCompletedAudioLoading(false)}
                            onCanPlay={() => setCompletedAudioLoading(false)}
                            onPlaying={() => setCompletedAudioLoading(false)}
                            onWaiting={() => setCompletedAudioLoading(true)}
                            onError={() => {
                              try {
                                const el = audioRef.current;
                                if (!el) return;
                                const isAudio = /\/audio$/.test(el.src);
                                const alt = isAudio ? el.src.replace(/\/audio$/, '/podcast') : el.src.replace(/\/podcast$/, '/audio');
                                // Only flip once per mount
                                if ((el as any)._altTried) return;
                                (el as any)._altTried = true;
                                setCompletedAudioLoading(true);
                                el.src = alt;
                                el.load();
                                el.play().catch(() => {});
                              } catch {}
                              setCompletedAudioLoading(false);
                            }}
                          >
                              Your browser does not support the audio element.
                            </audio>
                            {completedAudioLoading && (
                              <div className="video-status-overlay loading" role="status" aria-live="polite">
                                <div className="spinner" aria-hidden></div>
                                <span className="loading-text">Loading audio…</span>
                              </div>
                            )}
                          </div>
                          {(() => { const tt = ((((processingDetails as any)?.task_type)||'').toLowerCase()); return (["podcast","both"].includes(tt)) && completedTranscriptMd; })() && (
                            <div style={{ marginTop: '12px' }}>
                              <h4>Transcript (Conversation)</h4>
                              <PodcastTranscript audioRef={audioRef} markdown={completedTranscriptMd ?? ''} />
                            </div>
                          )}
                          {(() => { const tt = ((((processingDetails as any)?.task_type)||'').toLowerCase()); return !(["podcast","both"].includes(tt)); })() &&
                            showAudioTranscript &&
                            audioCues.length > 0 && (
                              <div
                                className="audio-transcript-pane"
                                ref={audioTranscriptRef}
                                aria-label="Audio captions"
                              >
                                {audioCues.map((cue, idx) => (
                                  <div
                                    key={idx}
                                    id={`audio-cue-${idx}`}
                                    className={`cue ${activeAudioCueIdx === idx ? "active" : ""}`}
                                    onClick={() => {
                                      const a = audioRef.current;
                                      if (!a) return;
                                      const target = Math.max(
                                        0,
                                        Math.min(
                                          isFinite(a.duration)
                                            ? a.duration - 0.05
                                            : cue.start + 0.01,
                                          cue.start + 0.01,
                                        ),
                                      );
                                      const doPlay = () =>
                                        a.play().catch(() => {});
                                      const doSeekReady = () => {
                                        try {
                                          const onSeeked = () => {
                                            a.removeEventListener(
                                              "seeked",
                                              onSeeked,
                                            );
                                            doPlay();
                                          };
                                          a.addEventListener(
                                            "seeked",
                                            onSeeked,
                                            { once: true },
                                          );
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
                                      else
                                        a.addEventListener(
                                          "loadedmetadata",
                                          doSeekReady,
                                          { once: true },
                                        );
                                    }}
                                    role="button"
                                    tabIndex={0}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter" || e.key === " ") {
                                        e.preventDefault();
                                        const a = audioRef.current;
                                        if (!a) return;
                                        const target = Math.max(
                                          0,
                                          Math.min(
                                            isFinite(a.duration)
                                              ? a.duration - 0.05
                                              : cue.start + 0.01,
                                            cue.start + 0.01,
                                          ),
                                        );
                                        const doPlay = () =>
                                          a.play().catch(() => {});
                                        const doSeekReady = () => {
                                          try {
                                            const onSeeked = () => {
                                              a.removeEventListener(
                                                "seeked",
                                                onSeeked,
                                              );
                                              doPlay();
                                            };
                                            a.addEventListener(
                                              "seeked",
                                              onSeeked,
                                              { once: true },
                                            );
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
                                        else
                                          a.addEventListener(
                                            "loadedmetadata",
                                            doSeekReady,
                                            { once: true },
                                          );
                                      }
                                    }}
                                  >
                                    <div className="t-time">
                                      {Math.floor(cue.start / 60)}:
                                      {String(
                                        Math.floor(cue.start % 60),
                                      ).padStart(2, "0")}
                                    </div>
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
                          <span className="info-value">
                            {processingDetails?.voice_language
                              ? getLanguageDisplayName(
                                  processingDetails.voice_language,
                                )
                              : "English"}
                          </span>
                        </div>
                        <div className="info-item">
                          <span className="info-label">Subtitle Language:</span>
                          <span className="info-value">
                            {processingDetails?.subtitle_language
                              ? getLanguageDisplayName(
                                  processingDetails.subtitle_language,
                                )
                              : getLanguageDisplayName(subtitleLanguage)}
                          </span>
                        </div>
                        {(
                          (processingDetails as any)?.file_ext ||
                          file?.name ||
                          ""
                        )
                          .toLowerCase()
                          .endsWith(".pdf") ? null : (
                          <div className="info-item">
                            <span className="info-label disabled">
                              AI Avatar:
                            </span>
                            <span className="info-value">
                              {generateAvatar ? "✓ Generated" : "✗ Disabled"}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Resource URLs */}
                    <div className="resource-links">
                      {/* Video */}
                      {(() => { const tt = ((((processingDetails as any)?.task_type)||'').toLowerCase()); return ["video","both"].includes(tt); })() && (
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
                              navigator.clipboard.writeText(
                                `${API_BASE_URL}/api/tasks/${taskId}/video`,
                              );
                              alert("Video URL copied!");
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>
                      )}

                      {/* Audio/Podcast */}
                      <div className="url-copy-row">
                        <span className="resource-label-inline">
                          {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); return ["podcast","both"].includes(tt) ? 'Podcast' : 'Audio'; })()}
                        </span>
                        <input
                          type="text"
                          value={`${API_BASE_URL}/api/tasks/${taskId}/${(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); return ["podcast","both"].includes(tt) ? 'podcast' : 'audio'; })()}`}
                          readOnly
                          className="url-input-enhanced"
                        />
                        <button
                          onClick={() => {
                            const tt = ((((processingDetails as any)?.task_type)||'').toLowerCase());
                            const isPod = ["podcast","both"].includes(tt);
                            navigator.clipboard.writeText(
                              `${API_BASE_URL}/api/tasks/${taskId}/${isPod ? 'podcast' : 'audio'}`,
                            );
                            alert(`${isPod ? 'Podcast' : 'Audio'} URL copied!`);
                          }}
                          className="copy-btn-enhanced"
                        >
                          Copy
                        </button>
                      </div>

                      {/* Transcript */}
                      {fileId && (
                        <div className="url-copy-row">
                          <span className="resource-label-inline">
                            Transcript
                          </span>
                          <input
                            type="text"
                            value={`${API_BASE_URL}/api/tasks/${taskId}/transcripts/markdown`}
                            readOnly
                            className="url-input-enhanced"
                          />
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(
                                `${API_BASE_URL}/api/tasks/${taskId}/transcripts/markdown`,
                              );
                              alert("Transcript URL copied!");
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>
                      )}

                      {/* VTT (hide for podcast-only) */}
                      {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); const v = ["video","both"].includes(tt); const p = ["podcast","both"].includes(tt); return v && !p; })() && (
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
                                navigator.clipboard.writeText(
                                  `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt`,
                                );
                                alert("VTT URL copied!");
                              }}
                              className="copy-btn-enhanced"
                            >
                              Copy
                            </button>
                          </div>
                        )}
                      {/* SRT (hide for podcast-only) */}
                      {(() => { const tt = (((processingDetails as any)?.task_type)||'').toLowerCase(); const v = ["video","both"].includes(tt); const p = ["podcast","both"].includes(tt); return v && !p; })() &&
                        generateSubtitles &&
                        fileId && (
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
                                navigator.clipboard.writeText(
                                  `${API_BASE_URL}/api/tasks/${taskId}/subtitles/srt`,
                                );
                                alert("SRT URL copied!");
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
                      <button
                        onClick={resetForm}
                        className="primary-btn"
                        type="button"
                      >
                        Create Another Project
                      </button>
                    </div>
                  </div>
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

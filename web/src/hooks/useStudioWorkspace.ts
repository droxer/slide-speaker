import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useI18n } from '@/i18n/hooks';
import { useRouter } from '@/navigation';

// Define TypeScript types
type AppStatus =
  | 'idle'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'error'
  | 'cancelled';

type UploadMode = 'slides' | 'pdf';
type PdfOutputMode = 'video' | 'podcast';
type VideoPreviewMode = 'video' | 'audio';

// Define interfaces
interface StepDetails {
  status: string;
  data?: unknown;
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
  transcript_language?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Custom hook for managing the studio workspace state and business logic
 */
export function useStudioWorkspace() {
  const router = useRouter();
  const { t, locale } = useI18n();
  const queryClient = useQueryClient();

  // State management
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [processingDetails, setProcessingDetails] = useState<ProcessingDetails | null>(null);
  const [voiceLanguage, setVoiceLanguage] = useState('english');
  const [subtitleLanguage, setSubtitleLanguage] = useState('english');
  const [transcriptLanguage, setTranscriptLanguage] = useState('english');
  const [transcriptLangTouched, setTranscriptLangTouched] = useState(false);
  const [videoResolution, setVideoResolution] = useState('hd');
  const [generateAvatar, setGenerateAvatar] = useState(false);
  const [generateSubtitles, setGenerateSubtitles] = useState(true);
  const [uploadMode, setUploadMode] = useState<UploadMode>('slides');
  const [pdfOutputMode, setPdfOutputMode] = useState<PdfOutputMode>('video');
  const [processingPreviewMode, setProcessingPreviewMode] = useState<VideoPreviewMode>('video');
  
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const uploadProgressTimerRef = useRef<number | null>(null);
  const processingSubtitleCleanupRef = useRef<(() => void) | null>(null);
  const completionRedirectRef = useRef(false);

  // Memoized functions
  const getLanguageDisplayName = useCallback(
    (languageCode: string): string => {
      const languageKeyMap: Record<string, string> = {
        english: 'language.english',
        simplified_chinese: 'language.simplified',
        traditional_chinese: 'language.traditional',
        japanese: 'language.japanese',
        korean: 'language.korean',
        thai: 'language.thai',
      };

      const normalized = (languageCode || '').toLowerCase();
      const key = languageKeyMap[normalized];
      if (key) {
        return t(key, undefined, languageCode);
      }

      return languageCode;
    },
    [t],
  );

  const resetForm = useCallback(() => {
    setFile(null);
    setUploadId(null);
    setTaskId(null);
    setStatus('idle');
    setUploading(false);
    setProgress(0);
    setProcessingDetails(null);
    setVoiceLanguage('english');
    setSubtitleLanguage('english');
    setTranscriptLanguage('english');
    setTranscriptLangTouched(false);
    setVideoResolution('hd');
    setGenerateAvatar(false);
    setGenerateSubtitles(true);
    setUploadMode('slides');
    setPdfOutputMode('video');
    setProcessingPreviewMode('video');
    completionRedirectRef.current = false;
  }, []);

  // Return state and actions
  return {
    // State
    file,
    uploading,
    uploadId,
    taskId,
    status,
    progress,
    processingDetails,
    voiceLanguage,
    subtitleLanguage,
    transcriptLanguage,
    transcriptLangTouched,
    videoResolution,
    generateAvatar,
    generateSubtitles,
    uploadMode,
    pdfOutputMode,
    processingPreviewMode,
    videoRef,
    audioRef,
    uploadProgressTimerRef,
    processingSubtitleCleanupRef,
    completionRedirectRef,
    
    // Actions
    setFile,
    setUploading,
    setUploadId,
    setTaskId,
    setStatus,
    setProgress,
    setProcessingDetails,
    setVoiceLanguage,
    setSubtitleLanguage,
    setTranscriptLanguage,
    setTranscriptLangTouched,
    setVideoResolution,
    setGenerateAvatar,
    setGenerateSubtitles,
    setUploadMode,
    setPdfOutputMode,
    setProcessingPreviewMode,
    resetForm,
    getLanguageDisplayName,
    queryClient,
    t,
    locale,
    router,
  };
}
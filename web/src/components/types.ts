// Types for StudioWorkspace component

export interface StepDetails {
  status: string;
  data?: unknown;
}

export interface ProcessingError {
  step: string;
  error: string;
  timestamp: string;
}

export interface ProcessingDetails {
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

export type AppStatus =
  | 'idle'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'error'
  | 'cancelled';

export interface UploadConfigurationProps {
  uploadMode: 'slides' | 'pdf';
  setUploadMode: (mode: 'slides' | 'pdf') => void;
  pdfOutputMode: 'video' | 'podcast';
  setPdfOutputMode: (mode: 'video' | 'podcast') => void;
  file: File | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  voiceLanguage: string;
  setVoiceLanguage: (language: string) => void;
  subtitleLanguage: string;
  setSubtitleLanguage: (language: string) => void;
  transcriptLanguage: string;
  setTranscriptLanguage: (language: string) => void;
  setTranscriptLangTouched: (touched: boolean) => void;
  videoResolution: string;
  setVideoResolution: (resolution: string) => void;
  uploading: boolean;
  onCreate: () => void;
  getFileTypeHint: (filename: string) => JSX.Element;
}

export interface FileUploadingStageProps {
  progress: number;
  fileName: string | null;
  fileSize: number | null;
  summaryItems: { key: string; label: string; value: string }[];
  outputs: { key: string; label: string; value: string }[];
}

export interface TaskProcessingStageProps {
  taskId: string | null;
  uploadId: string | null;
  fileName: string | null;
  progress: number;
  onStop: () => void;
  processingDetails: ProcessingDetails;
  formatStepNameWithLanguages: (step: string, voiceLang: string, subtitleLang?: string) => string;
  apiBaseUrl?: string;
  processingPreviewMode?: 'video' | 'audio';
  setProcessingPreviewMode?: (mode: 'video' | 'audio') => void;
  videoRef?: React.RefObject<HTMLVideoElement>;
  audioRef?: React.RefObject<HTMLAudioElement>;
}

export interface ErrorStageProps {
  onResetForm: () => void;
}

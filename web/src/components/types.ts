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

export interface ErrorStageProps {
  onResetForm: () => void;
}

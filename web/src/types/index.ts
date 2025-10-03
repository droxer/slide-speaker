export interface TaskState {
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
  steps?: Record<string, { status?: string; data?: any }>;
}

export interface Task {
  id?: string;
  task_id: string;
  file_id: string;
  task_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  owner_id?: string | null;
  // Optional DB-surfaced language hints
  voice_language?: string;
  subtitle_language?: string;
  kwargs: {
    file_id: string;
    file_ext: string;
    filename?: string;
    voice_language: string;
    subtitle_language?: string;
    transcript_language?: string;
    video_resolution?: string;
    generate_avatar: boolean;
    generate_subtitles: boolean;
  };
  state?: TaskState;
  detailed_state?: any;
  completion_percentage?: number;
}

export interface DownloadItem {
  type: string;
  url: string;
  download_url?: string;
}

export interface DownloadsResponse {
  items: DownloadItem[];
}

export type {UserProfile, ProfileResponse} from './user';

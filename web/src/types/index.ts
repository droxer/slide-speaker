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
  file_ext?: string;
  file_path?: string;
}

export interface Task {
  id?: string;
  task_id: string;
  upload_id: string;
  task_type: string;
  filename?: string;
  file_ext?: string;
  status: string;
  created_at: string;
  updated_at: string;
  user_id?: string | null;
  // Optional DB-surfaced language hints
  voice_language?: string;
  subtitle_language?: string;
  transcript_language?: string;
  steps?: Record<string, { status?: string; data?: any }>;
  progress?: number;
  kwargs: {
    upload_id: string;
    file_ext: string;
    filename?: string;
    voice_language: string;
    subtitle_language?: string;
    transcript_language?: string;
    video_resolution?: string;
    generate_avatar: boolean;
    generate_subtitles: boolean;
    generate_video?: boolean;
    generate_podcast?: boolean;
    source_type?: string;
  };
  state?: TaskState;
  detailed_state?: any;
  completion_percentage?: number;
  upload?: {
    id: string;
    user_id?: string | null;
    filename?: string | null;
    file_ext?: string | null;
    source_type?: string | null;
    content_type?: string | null;
    checksum?: string | null;
    size_bytes?: number | null;
    storage_path?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
  };
  _uploadOnly?: boolean;
}

export interface DownloadItem {
  type: string;
  url: string;
  download_url?: string;
}

export interface DownloadsResponse {
  items: DownloadItem[];
}

export interface PodcastScriptLine {
  speaker: string;
  text: string;
}

export interface PodcastScriptResponse {
  dialogue: PodcastScriptLine[];
  host_voice?: string | null;
  guest_voice?: string | null;
  language?: string | null;
  source?: string | null;
}

export type {UserProfile, ProfileResponse} from './user';

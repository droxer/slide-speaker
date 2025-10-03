'use client';

import React, {
  useState,
  useRef,
  useEffect,
  useMemo,
  useCallback,
} from 'react';
import {
  upload as apiUpload,
  cancelRun as apiCancel,
  getTaskProgress as apiGetProgress,
} from '@/services/client';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import ProcessingView from '@/components/ProcessingView';
import UploadPanel from '@/components/UploadPanel';
import ErrorView from '@/components/ErrorView';
import UploadingView from '@/components/UploadingView';
import {getStepLabel} from '@/utils/stepLabels';
import {resolveApiBaseUrl} from '@/utils/apiBaseUrl';
import {useI18n} from '@/i18n/hooks';
import {useRouter} from '@/navigation';

const API_BASE_URL = resolveApiBaseUrl();

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
  created_at: string;
  updated_at: string;
}

type AppStatus =
  | 'idle'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'error'
  | 'cancelled';

export function StudioWorkspace() {
  const router = useRouter();
  const {t, locale} = useI18n();
  const queryClient = useQueryClient();

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [fileId, setFileId] = useState<string | null>(null);
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
  const [uploadMode, setUploadMode] = useState<'slides' | 'pdf'>('slides');
  const [pdfOutputMode, setPdfOutputMode] = useState<'video' | 'podcast'>('video');
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const uploadProgressTimerRef = useRef<number | null>(null);
  const processingSubtitleCleanupRef = useRef<(() => void) | null>(null);
  const completionRedirectRef = useRef(false);
  const [processingPreviewMode, setProcessingPreviewMode] = useState<'video' | 'audio'>('video');

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
    setFileId(null);
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
    completionRedirectRef.current = false;
  }, []);

  const formatFileSize = useCallback((size: number | null | undefined) => {
    if (!size || size <= 0) {
      return t('common.unknown', undefined, 'Unknown');
    }
    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
    const value = size / 1024 ** exponent;
    return `${value.toFixed(1)} ${units[exponent]}`;
  }, [t]);

  const uploadingSummaryItems = useMemo(() => {
    if (!file) return [] as {key: string; label: string; value: string}[];

    const items = [
      {
        key: 'filename',
        label: t('upload.summary.file', undefined, 'File'),
        value: file.name,
      },
      {
        key: 'filesize',
        label: t('upload.summary.size', undefined, 'Size'),
        value: formatFileSize(file.size),
      },
    ];

    if (uploadMode === 'pdf') {
      items.push({
        key: 'outputMode',
        label: t('upload.summary.output', undefined, 'Output'),
        value: pdfOutputMode === 'video' ? t('actions.generateVideo', undefined, 'Generate Video') : t('actions.generatePodcast', undefined, 'Generate Podcast'),
      });
    }

    return items;
  }, [file, formatFileSize, t, uploadMode, pdfOutputMode]);

  const uploadingOutputs = useMemo(() => {
    const outputs: {key: string; label: string; value: string}[] = [];

    if (uploadMode === 'slides' || (uploadMode === 'pdf' && pdfOutputMode === 'video')) {
      outputs.push({
        key: 'video',
        label: t('task.list.videoLabel', undefined, 'Video'),
        value: t('task.list.videoLabel', undefined, 'Video'),
      });
    }

    if (uploadMode === 'pdf' && pdfOutputMode === 'podcast') {
      outputs.push({
        key: 'podcast',
        label: t('task.list.podcastLabel', undefined, 'Podcast'),
        value: t('task.list.podcastLabel', undefined, 'Podcast'),
      });
    }

    outputs.push({
      key: 'audio',
      label: t('task.list.audioLabel', undefined, 'Audio'),
      value: t('task.list.audioLabel', undefined, 'Audio'),
    });

    if (generateSubtitles) {
      outputs.push({
        key: 'subtitles',
        label: t('task.detail.subtitles', undefined, 'Subtitles'),
        value: t('task.detail.subtitles', undefined, 'Subtitles'),
      });
    }

    return outputs;
  }, [t, uploadMode, pdfOutputMode, generateSubtitles]);

  const summaryItems = useMemo(() => {
    if (!file) return [] as {key: string; label: string; value: string}[];

    const items: {key: string; label: string; value: string}[] = [
      {
        key: 'filename',
        label: t('upload.summary.file', undefined, 'File'),
        value: file.name,
      },
    ];

    if (file.size) {
      items.push({
        key: 'size',
        label: t('upload.summary.size', undefined, 'Size'),
        value: formatFileSize(file.size),
      });
    }

    items.push({
      key: 'voice',
      label: t('runTask.voiceLanguage', undefined, 'Voice language'),
      value: getLanguageDisplayName(voiceLanguage),
    });

    const subtitlesValue = generateSubtitles
      ? getLanguageDisplayName(subtitleLanguage)
      : t('common.disabled', undefined, 'Disabled');

    items.push({
      key: 'subtitles',
      label: t('task.detail.subtitles'),
      value: subtitlesValue,
    });

    if (transcriptLanguage) {
      items.push({
        key: 'transcript',
        label: t('task.detail.transcript'),
        value: getLanguageDisplayName(transcriptLanguage),
      });
    }

    const hasVideo = uploadMode === 'slides' || (uploadMode === 'pdf' && pdfOutputMode === 'video');
    if (hasVideo) {
      const resolutionKey = `runTask.resolution.${videoResolution}` as const;
      items.push({
        key: 'resolution',
        label: t('runTask.videoResolution', undefined, 'Video resolution'),
        value: t(resolutionKey, undefined, videoResolution.toUpperCase()),
      });
    }

    return items;
  }, [
    file,
    formatFileSize,
    generateSubtitles,
    getLanguageDisplayName,
    pdfOutputMode,
    subtitleLanguage,
    t,
    transcriptLanguage,
    uploadMode,
    videoResolution,
    voiceLanguage,
  ]);

  useEffect(() => {
    if (uploadMode === 'pdf' && pdfOutputMode === 'podcast' && !transcriptLangTouched) {
      setTranscriptLanguage(voiceLanguage);
    }
  }, [uploadMode, pdfOutputMode, voiceLanguage, transcriptLangTouched]);

  useEffect(() => {
    if (uploadMode === 'pdf' && pdfOutputMode === 'podcast') {
      setTranscriptLangTouched(false);
    }
  }, [uploadMode, pdfOutputMode]);

  const uploadMutation = useMutation({
    mutationFn: apiUpload,
    onSettled: async () => {
      try {
        await queryClient.invalidateQueries({queryKey: ['tasks']});
        await queryClient.invalidateQueries({queryKey: ['tasksSearch']});
      } catch {}
    },
  });

  const clearUploadProgressTimer = useCallback(() => {
    if (uploadProgressTimerRef.current !== null) {
      window.clearInterval(uploadProgressTimerRef.current);
      uploadProgressTimerRef.current = null;
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;

    setUploading(true);
    setStatus('uploading');
    setProgress(0);
    clearUploadProgressTimer();

    uploadProgressTimerRef.current = window.setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          return prev;
        }
        return prev + 5;
      });
    }, 200);

    try {
      const taskType = uploadMode === 'pdf'
        ? (pdfOutputMode === 'video' ? 'video' : 'podcast')
        : 'video';
      const sourceType = uploadMode === 'pdf' ? 'pdf' : 'slides';

      const base64File = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          const base64Data = result.includes(',') ? result.split(',')[1] : result;
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const payload: Record<string, unknown> = {
        filename: file.name,
        file_data: base64File,
        voice_language: voiceLanguage,
        video_resolution: videoResolution,
        generate_avatar: generateAvatar,
        generate_subtitles: generateSubtitles,
        task_type: taskType,
        source_type: sourceType,
        generate_video: taskType !== 'podcast',
        generate_podcast: taskType !== 'video',
      };

      if (subtitleLanguage) {
        payload.subtitle_language = subtitleLanguage;
      }

      if (taskType === 'podcast' && transcriptLanguage) {
        payload.transcript_language = transcriptLanguage;
      }

      const response = await uploadMutation.mutateAsync(payload);

      setFileId(response.file_id);
      setTaskId(response.task_id);
      clearUploadProgressTimer();
      setProgress(100);
      await new Promise((resolve) => setTimeout(resolve, 150));
      setStatus('processing');
      setUploading(false);
      setProgress(0);
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
      setUploading(false);
      setStatus('idle');
      clearUploadProgressTimer();
      setProgress(0);
    }
  }, [
    clearUploadProgressTimer,
    file,
    generateAvatar,
    generateSubtitles,
    pdfOutputMode,
    subtitleLanguage,
    transcriptLanguage,
    uploadMode,
    uploadMutation,
    videoResolution,
    voiceLanguage,
  ]);

  const cancelMutation = useMutation({
    mutationFn: (id: string) => apiCancel(id),
    onSettled: async () => {
      try {
        await queryClient.invalidateQueries({queryKey: ['progress']});
        await queryClient.invalidateQueries({queryKey: ['tasks']});
      } catch {}
    },
  });

  const handleStopProcessing = useCallback(async () => {
    if (!taskId) return;
    try {
      await cancelMutation.mutateAsync(taskId);
    } catch (error) {
      console.error('Failed to cancel task', error);
      alert('Failed to cancel task. Please try again.');
    }
  }, [cancelMutation, taskId]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
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
      } else {
        alert('Please select a PDF or PowerPoint file');
      }
    }
  }, [uploadMode]);

  useEffect(() => {
    if (status !== 'processing') {
      return;
    }

    const previousCleanup = processingSubtitleCleanupRef.current;
    if (previousCleanup) {
      previousCleanup();
      processingSubtitleCleanupRef.current = null;
    }

    const video = videoRef.current;
    if (!generateSubtitles || !taskId || !video || status !== 'processing') {
      return;
    }

    const resolveSrclang = (lang: string) => {
      switch (lang) {
        case 'simplified_chinese':
          return 'zh-Hans';
        case 'traditional_chinese':
          return 'zh-Hant';
        case 'japanese':
          return 'ja';
        case 'korean':
          return 'ko';
        case 'thai':
          return 'th';
        default:
          return 'en';
      }
    };

    let activeTrack: HTMLTrackElement | null = null;
    let loadHandler: ((event: Event) => void) | null = null;
    let errorHandler: ((event: Event) => void) | null = null;
    let retryTimeout: ReturnType<typeof globalThis.setTimeout> | null = null;

    const detachActiveTrack = () => {
      if (activeTrack) {
        if (loadHandler) activeTrack.removeEventListener('load', loadHandler);
        if (errorHandler) activeTrack.removeEventListener('error', errorHandler);
        if (activeTrack.parentNode === video) {
          video.removeChild(activeTrack);
        }
      }
      activeTrack = null;
      loadHandler = null;
      errorHandler = null;
    };

    const attachTrack = (useFallbackSrc = false) => {
      detachActiveTrack();
      if (retryTimeout) {
        globalThis.clearTimeout(retryTimeout);
        retryTimeout = null;
      }

      const track = document.createElement('track');
      track.kind = 'subtitles';
      track.dataset.processingTrack = 'true';
      track.src = useFallbackSrc
        ? `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt`
        : `${API_BASE_URL}/api/tasks/${taskId}/subtitles/vtt?language=${encodeURIComponent(subtitleLanguage)}`;
      track.setAttribute('srclang', resolveSrclang(subtitleLanguage));
      track.label = getLanguageDisplayName(subtitleLanguage);
      track.default = true;

      loadHandler = () => {
        if (!video || video.textTracks.length === 0) return;
        const textTrack = video.textTracks[0];
        textTrack.mode = 'showing';
      };

      errorHandler = (event: Event) => {
        console.error('Subtitle track loading error:', event);
        if (!useFallbackSrc) {
          attachTrack(true);
        }
      };

      track.addEventListener('load', loadHandler);
      track.addEventListener('error', errorHandler);
      video.appendChild(track);
      activeTrack = track;

      if (!useFallbackSrc) {
        retryTimeout = globalThis.setTimeout(() => {
          if (video && video.textTracks.length === 0) {
            attachTrack(true);
          }
        }, 1200);
      }
    };

    const ensureTrack = () => {
      if (!video || video.readyState === 0) {
        return;
      }
      attachTrack(false);
    };

    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
      ensureTrack();
    }

    const onLoadedMetadata = () => {
      ensureTrack();
    };

    const onLoadedData = () => {
      ensureTrack();
    };

    if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
      video.addEventListener('loadedmetadata', onLoadedMetadata, {once: true});
      video.addEventListener('loadeddata', onLoadedData, {once: true});
    }

    const cleanup = () => {
      if (retryTimeout) {
        globalThis.clearTimeout(retryTimeout);
      }
      detachActiveTrack();
      video.removeEventListener('loadedmetadata', onLoadedMetadata);
      video.removeEventListener('loadeddata', onLoadedData);
    };

    processingSubtitleCleanupRef.current = cleanup;

    return () => {
      cleanup();
      processingSubtitleCleanupRef.current = null;
    };
  }, [
    generateSubtitles,
    getLanguageDisplayName,
    status,
    subtitleLanguage,
    taskId,
  ]);

  useEffect(() => {
    return () => {
      clearUploadProgressTimer();
    };
  }, [clearUploadProgressTimer]);

  const formatStepName = useCallback((step: string): string => getStepLabel(step, t), [t]);

  const formatStepNameWithLanguages = useCallback(
    (step: string, voiceLang: string, subtitleLang?: string): string => {
      const vl = (voiceLang || 'english').toLowerCase();
      const sl = (subtitleLang || vl).toLowerCase();
      const same = vl === sl;
      if (
        same &&
        (step === 'translate_voice_transcripts' || step === 'translate_subtitle_transcripts')
      ) {
        return t('processing.step.translatingTranscripts', undefined, 'Translating Transcripts');
      }
      return formatStepName(step);
    },
    [formatStepName, t],
  );

  const progressQuery = useQuery({
    queryKey: ['progress', taskId],
    queryFn: () => apiGetProgress<ProcessingDetails>(taskId as string),
    enabled: status === 'processing' && Boolean(taskId),
    refetchInterval: 3000,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    const resp = progressQuery.data as any;
    if (!resp) return;

    const data = resp?.data ?? resp;
    if (!data) return;

    setProcessingDetails(data as ProcessingDetails);

    const rawProgress = typeof data.progress === 'number' ? data.progress : 0;
    const normalizedProgress = Number.isFinite(rawProgress)
      ? (rawProgress > 1 ? Math.min(100, rawProgress) : Math.min(100, Math.round(rawProgress * 100)))
      : 0;

    if (data.status === 'completed') {
      setStatus('completed');
      setUploading(false);
      setProgress(100);
    } else if (data.status === 'processing' || data.status === 'uploaded') {
      setStatus('processing');
      setUploading(false);
      setProgress(normalizedProgress);
    } else if (data.status === 'cancelled') {
      setUploading(false);
      setTaskId(null);
      setFileId(null);
      setFile(null);
      setProcessingDetails(null);
      setProgress(0);
      setStatus('idle');
    } else if (data.status === 'failed') {
      setStatus('error');
      setUploading(false);
      setTaskId(null);
    } else {
      setStatus('error');
      setUploading(false);
      setTaskId(null);
    }
  }, [progressQuery.data]);

  useEffect(() => {
    if (status === 'completed' && taskId && !completionRedirectRef.current) {
      completionRedirectRef.current = true;
      router.push(`/tasks/${taskId}`, {locale});
    }
  }, [status, taskId, router, locale]);

  useEffect(() => {
    const hydrateTaskId = async () => {
      if (status === 'completed' && fileId && (!taskId || taskId === 'null')) {
        try {
          const {searchTasks} = await import('@/services/client');
          const res = await searchTasks(fileId);
          const tasks = Array.isArray(res?.tasks) ? res.tasks : [];
          const match = tasks.find(
            (t: any) =>
              t?.file_id === fileId &&
              typeof t?.task_id === 'string' &&
              !t.task_id.startsWith('state_'),
          );
          if (match?.task_id) {
            setTaskId(match.task_id);
          }
        } catch (e) {
          console.warn('Failed to hydrate taskId for completed view', e);
        }
      }
    };

    hydrateTaskId();
  }, [fileId, status, taskId]);

  const getFileTypeHint = useCallback((filename: string): JSX.Element => {
    const ext = filename.toLowerCase().split('.').pop();

    if (ext === 'pdf') {
      return (
        <div className="file-type-hint pdf">
          <span className="file-type-badge pdf">{t('upload.file.pdfBadge', undefined, 'PDF')}</span>
          <div className="file-type-description">
            {t(
              'upload.file.pdfDescription',
              undefined,
              'AI will analyze and convert your PDF into engaging video chapters with narration and subtitles.',
            )}
          </div>
        </div>
      );
    }

    if (ext === 'pptx' || ext === 'ppt') {
      return (
        <div className="file-type-hint ppt">
          <span className="file-type-badge ppt">{t('upload.file.pptBadge', undefined, 'PPT')}</span>
          <div className="file-type-description">
            {t('upload.file.pptDescription', undefined, 'AI will convert your slides into a narrated video.')}
          </div>
        </div>
      );
    }

    return (
      <div className="file-type-hint">
        <span className="file-type-badge">{t('upload.file.supportedBadge', undefined, 'Supported File')}</span>
        <div className="file-type-description">
          {t('upload.file.supportedDescription', undefined, 'Supports PDF, PPTX, and PPT files')}
        </div>
      </div>
    );
  }, [t]);

  return (
    <div id="studio-panel" role="tabpanel" aria-labelledby="studio-tab">
      <div className="card-container">
        <div className={`content-card ${status === 'completed' ? 'wide' : ''}`}>
          {status === 'idle' && (
            <UploadPanel
              uploadMode={uploadMode}
              setUploadMode={setUploadMode}
              pdfOutputMode={pdfOutputMode}
              setPdfOutputMode={setPdfOutputMode}
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

          {status === 'uploading' && (
            <UploadingView
              progress={progress}
              fileName={file?.name || null}
              fileSize={file?.size ?? null}
              summaryItems={uploadingSummaryItems}
              outputs={uploadingOutputs}
            />
          )}

          {status === 'processing' && processingDetails && (
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

          {status === 'completed' && taskId && !completionRedirectRef.current && (
            <div className="processing-view redirecting-view" role="status" aria-live="polite">
              <div className="spinner" aria-hidden></div>
              <h3>{t('completed.redirecting', undefined, 'Opening task details…')}</h3>
            </div>
          )}

          {status === 'error' && <ErrorView onResetForm={resetForm} />}
        </div>
      </div>
    </div>
  );
}

export default StudioWorkspace;

'use client';

import React, {
  useState,
  useRef,
  useEffect,
  useMemo,
  useCallback,
} from 'react';
import {
  api as apiClient,
  upload as apiUpload,
  cancelRun as apiCancel,
  getTaskProgress as apiGetProgress,
  type UploadPayload,
} from '@/services/client';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import { prefetchTaskDetail } from '@/services/queries';
import dynamic from 'next/dynamic';

import LoadingPlaceholder from '@/components/LoadingPlaceholder';

const UploadPanel = dynamic(() => import('@/components/UploadPanel'), {
  ssr: false,
  loading: () => <LoadingPlaceholder type="card" message="Loading upload panel..." />
});

const FileUploadingView = dynamic(() => import('@/components/FileUploadingView'), {
  ssr: false,
  loading: () => <LoadingPlaceholder type="card" message="Loading upload view..." />
});

const TaskProcessingSteps = dynamic(() => import('@/components/TaskProcessingSteps'), {
  ssr: false,
  loading: () => <LoadingPlaceholder type="card" message="Loading processing steps..." />
});

const ErrorDisplay = dynamic(() => import('@/components/ErrorDisplay'), {
  ssr: false,
  loading: () => <LoadingPlaceholder type="card" message="Loading error display..." />
});
import { showErrorToast } from '@/utils/toast';
import { validateFile, getFileType, formatFileSize as formatFileSizeUtil } from '@/utils/fileValidation';
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
  const [uploadMode, setUploadMode] = useState<'slides' | 'pdf'>('slides');
  const [pdfOutputMode, setPdfOutputMode] = useState<'video' | 'podcast'>('video');
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const uploadProgressTimerRef = useRef<number | null>(null);
  const processingSubtitleCleanupRef = useRef<(() => void) | null>(null);
  const completionRedirectRef = useRef(false);
  const [processingPreviewMode, setProcessingPreviewMode] = useState<'video' | 'audio'>('video');
  const subtitleObjectUrlRef = useRef<string | null>(null);

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
    // Keep the current language and mode settings when resetting
    // setVoiceLanguage('english');
    // setSubtitleLanguage('english');
    // setTranscriptLanguage('english');
    setTranscriptLangTouched(false);
    // setVideoResolution('hd');
    // setGenerateAvatar(false);
    // setGenerateSubtitles(true);
    // setUploadMode('slides');
    // setPdfOutputMode('video');
    completionRedirectRef.current = false;
  }, []);

  const formatFileSize = useCallback((size: number | null | undefined) => {
    if (!size || size <= 0) {
      return t('common.unknown', undefined, 'Unknown');
    }
    // Use the utility function for better formatting
    return formatFileSizeUtil(size);
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
      {
        key: 'filetype',
        label: t('upload.summary.type', undefined, 'Type'),
        value: uploadMode === 'pdf' ? 'PDF Document' : 'Presentation Slides',
      },
    ];

    return items;
  }, [file, formatFileSize, t, uploadMode]);

  const uploadingOutputs = useMemo(() => {
    const outputs: {key: string; label: string; value: string}[] = [];

    // Only show file-related information, not task outputs
    outputs.push({
      key: 'status',
      label: t('upload.summary.status', undefined, 'Status'),
      value: t('upload.summary.uploading', undefined, 'Uploading'),
    });

    return outputs;
  }, [t]);

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

    // Add file type information only
    items.push({
      key: 'type',
      label: t('upload.summary.documentType', undefined, 'Document Type'),
      value: uploadMode === 'pdf' ? 'PDF Document' : 'PowerPoint Presentation',
    });

    return items;
  }, [
    file,
    formatFileSize,
    uploadMode,
    t,
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

      let payload: FormData | UploadPayload;

      if (typeof FormData !== 'undefined') {
        const formData = new FormData();
        formData.append('file', file, file.name);
        formData.append('filename', file.name);
        formData.append('voice_language', voiceLanguage);
        formData.append('video_resolution', videoResolution);
        formData.append('generate_avatar', String(generateAvatar));
        formData.append('generate_subtitles', String(generateSubtitles));
        formData.append('generate_podcast', String(taskType !== 'video'));
        formData.append('generate_video', String(taskType !== 'podcast'));
        formData.append('task_type', taskType);
        formData.append('source_type', sourceType);

        if (subtitleLanguage) {
          formData.append('subtitle_language', subtitleLanguage);
        }
        if (taskType === 'podcast' && transcriptLanguage) {
          formData.append('transcript_language', transcriptLanguage);
        }

        payload = formData;
      } else {
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

        const jsonPayload: UploadPayload = {
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
          jsonPayload.subtitle_language = subtitleLanguage;
        }

        if (taskType === 'podcast' && transcriptLanguage) {
          jsonPayload.transcript_language = transcriptLanguage;
        }

        payload = jsonPayload;
      }

      const response = await uploadMutation.mutateAsync(payload);

      if (response.upload_id) {
        setUploadId(response.upload_id);
      }
      if (response.task_id) {
        setTaskId(response.task_id);
        // Prefetch task details for better performance when user navigates to task detail page
        prefetchTaskDetail(queryClient, response.task_id);
      }
      clearUploadProgressTimer();
      setProgress(100);
      await new Promise((resolve) => setTimeout(resolve, 150));
      setStatus('processing');
      setUploading(false);
      setProgress(0);
    } catch (error) {
      console.error('Upload error:', error);
      showErrorToast(t('upload.error.failed', undefined, 'Upload failed. Please try again.'));
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
    t,
    queryClient,
  ]);

  const cancelMutation = useMutation({
    mutationFn: (id: string) => apiCancel(id),
    onSettled: async (_data, _error, cancelledTaskId) => {
      try {
        if (cancelledTaskId) {
          await queryClient.invalidateQueries({queryKey: ['progress', cancelledTaskId]});
        } else {
          await queryClient.invalidateQueries({queryKey: ['progress']});
        }
        await queryClient.invalidateQueries({queryKey: ['tasks']});
      } catch {}
    },
  });

  const handleStopProcessing = useCallback(async () => {
    if (!taskId) return;
    try {
      await cancelMutation.mutateAsync(taskId);
      setStatus('cancelled');
      setUploading(false);
      setProgress(0);
      setProcessingDetails((prev) =>
        prev ? {...prev, status: 'cancelled', progress: 0} : prev,
      );
      // Prefetch task details for better performance when user navigates to task detail page
      prefetchTaskDetail(queryClient, taskId);
    } catch (error) {
      console.error('Failed to cancel task', error);
      showErrorToast(
        t('task.error.cancelFailed', undefined, 'Failed to cancel task. Please try again.'),
      );
    }
  }, [cancelMutation, taskId, t, queryClient]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file based on upload mode
      const expectedFileType = uploadMode === 'pdf' ? 'pdf' : 'slides';
      const validation = validateFile(selectedFile, expectedFileType);
      
      if (!validation.isValid) {
        showErrorToast(validation.errorMessage || 'Invalid file selection.');
        return;
      }
      
      setFile(selectedFile);
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

    if (!video || !taskId || !subtitleLanguage) {
      return () => {
        if (subtitleObjectUrlRef.current) {
          URL.revokeObjectURL(subtitleObjectUrlRef.current);
          subtitleObjectUrlRef.current = null;
        }
      };
    }

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
      if (subtitleObjectUrlRef.current) {
        URL.revokeObjectURL(subtitleObjectUrlRef.current);
        subtitleObjectUrlRef.current = null;
      }
      activeTrack = null;
      loadHandler = null;
      errorHandler = null;
    };

    const buildCandidatePaths = (languageValue: string | undefined): string[] => {
      const basePath = `/api/tasks/${taskId}/subtitles/vtt`;
      if (languageValue) {
        return [
          `${basePath}?language=${encodeURIComponent(languageValue)}`,
          basePath,
        ];
      }
      return [basePath];
    };

    const attachTrack = async (useFallbackSrc = false) => {
      detachActiveTrack();
      if (retryTimeout) {
        globalThis.clearTimeout(retryTimeout);
        retryTimeout = null;
      }

      const track = document.createElement('track');
      track.kind = 'subtitles';
      track.dataset.processingTrack = 'true';
      track.setAttribute('srclang', resolveSrclang(subtitleLanguage));
      track.label = getLanguageDisplayName(subtitleLanguage);
      track.default = true;

      try {
        const languageParam = useFallbackSrc ? undefined : subtitleLanguage;
        const candidatePaths = buildCandidatePaths(languageParam);
        let objectUrl: string | null = null;
        let lastError: unknown = null;

        for (const candidatePath of candidatePaths) {
          try {
            const response = await apiClient.get(candidatePath, {
              headers: { Accept: 'text/vtt,*/*' },
              responseType: 'blob',
              withCredentials: true,
            });
            const blob = response.data as Blob;
            if (!blob || blob.size === 0) continue;
            objectUrl = URL.createObjectURL(blob);
            subtitleObjectUrlRef.current = objectUrl;
            track.src = objectUrl;
            break;
          } catch (candidateError) {
            lastError = candidateError;
          }
        }

        if (!objectUrl) {
          throw lastError ?? new Error('Unable to fetch subtitles');
        }
      } catch (error) {
        console.error('Subtitle fetch error:', error);
        if (!useFallbackSrc) {
          await attachTrack(true);
        }
        return;
      }

      loadHandler = () => {
        if (!video || video.textTracks.length === 0) return;
        const textTrack = video.textTracks[0];
        textTrack.mode = 'showing';
      };

      errorHandler = (event: Event) => {
        console.error('Subtitle track loading error:', event);
        if (!useFallbackSrc) {
          void attachTrack(true);
        }
      };

      track.addEventListener('load', loadHandler);
      track.addEventListener('error', errorHandler);
      video.appendChild(track);
      activeTrack = track;

      if (!useFallbackSrc) {
        retryTimeout = globalThis.setTimeout(() => {
          if (video && video.textTracks.length === 0) {
            void attachTrack(true);
          }
        }, 1200);
      }
    };

    const ensureTrack = () => {
      if (!video || video.readyState === 0) {
        return;
      }
      void attachTrack(false);
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
    // Disable polling when page is not visible to enable bfcache
    refetchIntervalInBackground: false,
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
      setProgress(0);
      setStatus('cancelled');
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
      // Prefetch task details for better performance when user navigates to task detail page
      prefetchTaskDetail(queryClient, taskId);
      router.push(`/tasks/${taskId}`, {locale});
    }
  }, [status, taskId, router, locale, queryClient]);

  useEffect(() => {
    const hydrateTaskId = async () => {
      if (status === 'completed' && uploadId && (!taskId || taskId === 'null')) {
        try {
          const {searchTasks} = await import('@/services/client');
          const res = await searchTasks(uploadId);
          const tasks = Array.isArray(res?.tasks) ? res.tasks : [];
          const match = tasks.find(
            (t: any) =>
              t?.upload_id === uploadId &&
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
  }, [uploadId, status, taskId]);

  const getFileTypeHint = useCallback((filename: string): React.JSX.Element => {
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
            <FileUploadingView
              progress={progress}
              fileName={file?.name || null}
              fileSize={file?.size ?? null}
              summaryItems={uploadingSummaryItems}
              outputs={uploadingOutputs}
            />
          )}

          {status === 'processing' && processingDetails && (
            <TaskProcessingSteps
              taskId={taskId}
              uploadId={uploadId}
              fileName={processingDetails?.filename || file?.name || null}
              progress={progress}
              onStop={handleStopProcessing}
              processingDetails={processingDetails}
              formatStepNameWithLanguages={formatStepNameWithLanguages}
            />
          )}

          {status === 'completed' && taskId && !completionRedirectRef.current && (
            <div className="processing-view redirecting-view" role="status" aria-live="polite">
              <div className="spinner" aria-hidden="true"></div>
              <h3>{t('completed.redirecting', undefined, 'Opening task details…')}</h3>
            </div>
          )}

          {status === 'cancelled' && (
            <div className="processing-view cancelled-view" role="status" aria-live="polite">
              <div className="status-icon cancelled" aria-hidden="true">🚫</div>
              <h3>{t('task.status.cancelled', undefined, 'Task Cancelled')}</h3>
              <p>{t('task.cancelled.description', undefined, 'The task has been successfully cancelled.')}</p>
              <button onClick={resetForm} className="primary-btn">
                {t('actions.createAnother', undefined, 'Create Another')}
              </button>
            </div>
          )}

          {status === 'error' && <ErrorDisplay onResetForm={resetForm} />}
        </div>
      </div>
    </div>
  );
}

export default StudioWorkspace;

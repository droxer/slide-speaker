import React, { useEffect, useState } from 'react';
import { api as apiClient } from '@/services/client';
import { useI18n } from '@/i18n/hooks';

type VideoPlayerProps = {
  src: string;
  trackUrl?: string;
  trackLang?: string;
  trackLabel?: string;
  autoPlay?: boolean;
  controls?: boolean;
  className?: string;
  onReady?: () => void;
  onError?: (e: any) => void;
};

const VideoPlayer = ({
  src,
  trackUrl,
  trackLang,
  trackLabel,
  autoPlay = true,
  controls = true,
  className,
  onReady,
  onError,
}: VideoPlayerProps) => {
  const { t } = useI18n();
  const [subtitleSrc, setSubtitleSrc] = useState<string | undefined>(trackUrl);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    const run = async () => {
      if (!trackUrl) {
        setSubtitleSrc(undefined);
        return;
      }
      try {
        const base = apiClient.defaults.baseURL || '';
        const resolved = base ? new URL(trackUrl, base).toString() : trackUrl;
        const response = await apiClient.get(resolved, {
          headers: { Accept: 'text/vtt,*/*' },
          responseType: 'blob',
          withCredentials: true,
        });
        const blob = response.data as Blob;
        if (!blob || blob.size === 0) {
          setSubtitleSrc(undefined);
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        if (!cancelled) {
          setSubtitleSrc(objectUrl);
        }
      } catch (error) {
        console.warn('Failed to load subtitle track', error);
        if (!cancelled) {
          setSubtitleSrc(undefined);
        }
      }
    };

    void run();

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [trackUrl]);

  return (
    <video
      className={className}
      src={src}
      controls={controls}
      autoPlay={autoPlay}
      playsInline
      preload="auto"
      crossOrigin="use-credentials"
      onCanPlay={onReady}
      onError={onError}
    >
      {subtitleSrc && (
        <track kind="subtitles" src={subtitleSrc} srcLang={trackLang} label={trackLabel} default />
      )}
      {t('videoPlayer.noSupport', undefined, 'Your browser does not support the video tag.')}
    </video>
  );
};

export default VideoPlayer;

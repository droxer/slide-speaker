import React from 'react';

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

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  trackUrl,
  trackLang,
  trackLabel,
  autoPlay = true,
  controls = true,
  className,
  onReady,
  onError,
}) => {
  return (
    <video
      className={className}
      src={src}
      controls={controls}
      autoPlay={autoPlay}
      playsInline
      preload="auto"
      crossOrigin="anonymous"
      onCanPlay={onReady}
      onError={onError}
    >
      {trackUrl && (
        <track kind="subtitles" src={trackUrl} srcLang={trackLang} label={trackLabel} default />
      )}
      Your browser does not support the video tag.
    </video>
  );
};

export default VideoPlayer;


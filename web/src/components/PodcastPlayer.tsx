import React from 'react';
import PodcastTranscript from './PodcastTranscript';

type PodcastPlayerProps = {
  src: string;
  transcriptMarkdown?: string;
  className?: string;
};

const PodcastPlayer: React.FC<PodcastPlayerProps> = ({ src, transcriptMarkdown, className }) => {
  const audioRef = React.useRef<HTMLAudioElement | null>(null);
  return (
    <div className={className} style={{ width: '100%' }}>
      <audio
        ref={audioRef}
        controls
        preload="auto"
        src={src}
        crossOrigin="anonymous"
        style={{ width: '100%', maxWidth: '100%', display: 'block' }}
      />
      {transcriptMarkdown && (
        <div className="audio-transcript" style={{ marginTop: 8 }}>
          <PodcastTranscript audioRef={audioRef} markdown={transcriptMarkdown} />
        </div>
      )}
    </div>
  );
};

export default PodcastPlayer;

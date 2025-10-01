import React from 'react';
import { useMemo } from 'react';
import AudioPlayer from '@/components/AudioPlayer';
import { buildCuesFromMarkdown } from '@/utils/transcript';

type PodcastPlayerProps = {
  src: string;
  transcriptMarkdown?: string;
  className?: string;
};

const PodcastPlayer: React.FC<PodcastPlayerProps> = ({ src, transcriptMarkdown, className }) => {
  const cues = useMemo(() => {
    if (!transcriptMarkdown) return undefined;
    return buildCuesFromMarkdown(transcriptMarkdown);
  }, [transcriptMarkdown]);
  return (
    <AudioPlayer src={src} initialCues={cues} showTranscript className={className} />
  );
};

export default PodcastPlayer;

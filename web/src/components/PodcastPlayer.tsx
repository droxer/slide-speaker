import React, { useMemo } from 'react';
import AudioPlayer from '@/components/AudioPlayer';
import { buildCuesFromPodcastDialogue } from '@/utils/transcript';
import type { PodcastScriptResponse } from '@/types';

type PodcastPlayerProps = {
  src: string;
  script?: PodcastScriptResponse | null;
  className?: string;
};

const PodcastPlayer = ({ src, script, className }: PodcastPlayerProps) => {
  const cues = useMemo(() => {
    const dialogue = script?.dialogue;
    if (!Array.isArray(dialogue) || dialogue.length === 0) return undefined;
    return buildCuesFromPodcastDialogue(
      dialogue,
      5, // segmentSeconds
      script?.host_voice,
      script?.guest_voice
    );
  }, [script]);

  return <AudioPlayer src={src} initialCues={cues} showTranscript className={className} />;
};

export default PodcastPlayer;

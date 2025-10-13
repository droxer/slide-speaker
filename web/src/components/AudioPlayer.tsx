import React, { useEffect, useRef, useState } from 'react';
import TranscriptList, { Cue } from './TranscriptList';
import { api as apiClient } from '@/services/client';

type AudioPlayerProps = {
  src: string;
  vttUrl?: string; // if provided, auto-fetch cues
  initialCues?: Cue[]; // alternatively pass pre-parsed cues
  showTranscript?: boolean;
  onReady?: () => void;
  onError?: (e: any) => void;
  className?: string;
};

const AudioPlayer = ({
  src,
  vttUrl,
  initialCues,
  showTranscript = true,
  onReady,
  onError,
  className,
}: AudioPlayerProps) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [cues, setCues] = useState<Cue[]>(initialCues || []);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  // Refresh cues if transcript props arrive after mount (e.g., fetched markdown)
  useEffect(() => {
    if (Array.isArray(initialCues)) {
      setCues(initialCues);
    }
  }, [initialCues]);

  // Fetch and parse VTT when vttUrl provided
  useEffect(() => {
    if (!vttUrl) return;
    let cancelled = false;
    (async () => {
      try {
        const base = apiClient.defaults.baseURL || '';
        const resolvedUrl = base ? new URL(vttUrl, base).toString() : vttUrl;
        const resp = await apiClient.get(resolvedUrl, {
          headers: { Accept: 'text/vtt,*/*' },
          responseType: 'text',
          withCredentials: true,
        });
        const text = resp.data as string;
        const lines = text.split(/\r?\n/);
        const parsed: Cue[] = [];
        let i = 0;
        const timeRe = /(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})\.(\d{3})/;
        // Parse WebVTT content
        while (i < lines.length) {
          const line = lines[i++].trim();
          // Skip empty lines, WEBVTT header, and sequence numbers
          if (!line || line.toUpperCase() === 'WEBVTT' || /^\d+$/.test(line)) continue;
          
          // Check if this is a time format line (e.g., "00:00:01.000 --> 00:00:04.000")
          const m = line.match(timeRe);
          if (m) {
            const start = (Number(m[1])*3600 + Number(m[2])*60 + Number(m[3]) + Number(m[4])/1000);
            const end = (Number(m[5])*3600 + Number(m[6])*60 + Number(m[7]) + Number(m[8])/1000);
            
            // Collect all text lines for this cue until we hit an empty line or another time format
            const textLines: string[] = [];
            while (i < lines.length) {
              const textLine = lines[i].trim();
              // Stop if we encounter an empty line or the start of the next cue
              if (!textLine || timeRe.test(textLine)) break;
              textLines.push(textLine);
              i++;
            }
            
            parsed.push({ start, end, text: textLines.join('\n') });
            
            // If we broke from the inner loop because we hit another timing line,
            // we need to step back so the outer loop can process that timing line
            if (i < lines.length && timeRe.test(lines[i].trim())) {
              i--; // Decrement to re-process the timing line in the outer loop
            }
          }
          // If line doesn't match time format, it's ignored (e.g., malformed lines)
        }
        if (!cancelled) setCues(parsed);
      } catch {}
    })();
    return () => { cancelled = true; };
  }, [vttUrl]);

  // Sync active cue using timeupdate/seeked
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || cues.length === 0) return;
    const EPS = 0.03;
    const findIdx = (t: number): number | null => {
      let lo = 0, hi = cues.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const c = cues[mid];
        if (t < c.start - EPS) hi = mid - 1;
        else if (t > c.end + EPS) lo = mid + 1;
        else return mid;
      }
      return null;
    };
    const onTime = () => {
      const idx = findIdx(audio.currentTime);
      setActiveIdx(prev => prev !== idx ? idx : prev);
    };
    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('seeked', onTime);
    onTime();
    return () => {
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('seeked', onTime);
    };
  }, [cues]);

  const handleSeek = (time: number) => {
    const a = audioRef.current;
    if (!a) return;
    const target = Math.max(0, Math.min(isFinite(a.duration) ? a.duration - 0.05 : time, time));
    const onSeeked = () => { a.removeEventListener('seeked', onSeeked); a.play().catch(()=>{}); };
    a.addEventListener('seeked', onSeeked, { once: true });
    a.currentTime = target;
  };

  const rootClasses = ['audio-player'];
  if (className) rootClasses.push(className);

  return (
    <div className={rootClasses.join(' ')}>
      <audio
        ref={audioRef}
        controls
        preload="auto"
        src={src}
        crossOrigin="use-credentials"
        onCanPlay={onReady}
        onError={onError}
        className="audio-player__native"
      />
      {showTranscript && (
        <div>
          {cues.length > 0 && (
            <TranscriptList cues={cues} activeIdx={activeIdx} onSeek={handleSeek} />
          )}
        </div>
      )}
    </div>
  );
};

export default AudioPlayer;

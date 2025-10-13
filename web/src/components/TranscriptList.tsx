import React, { useEffect, useRef } from 'react';

export type Cue = { start: number; end: number; text: string };

type TranscriptListProps = {
  cues: Cue[];
  activeIdx: number | null;
  onSeek?: (time: number) => void;
  showTimestamps?: boolean;
};

const formatTS = (t: number): string => {
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const s = Math.floor(t % 60);
  return h > 0
    ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    : `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
};

export const TranscriptList = ({ cues, activeIdx, onSeek, showTimestamps = true }: TranscriptListProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (activeIdx == null) return;
    const container = containerRef.current;
    if (!container) return;
    const el = container.querySelector(`#audio-cue-${activeIdx}`) as HTMLElement | null;
    if (!el) return;
    try {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    } catch {
      const cRect = container.getBoundingClientRect();
      const eRect = el.getBoundingClientRect();
      container.scrollTop += (eRect.top - cRect.top - cRect.height / 2);
    }
  }, [activeIdx]);

  // Keyboard shortcut: press 'c' when the transcript has focus to center on current line
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'c') {
        e.preventDefault();
        if (activeIdx == null) return;
        const el = container.querySelector(`#audio-cue-${activeIdx}`) as HTMLElement | null;
        if (!el) return;
        try {
          el.scrollIntoView({ block: 'center', behavior: 'smooth' });
        } catch {
          const cRect = container.getBoundingClientRect();
          const eRect = el.getBoundingClientRect();
          container.scrollTop += (eRect.top - cRect.top - cRect.height / 2);
        }
      }
    };
    container.addEventListener('keydown', onKey);
    return () => container.removeEventListener('keydown', onKey);
  }, [activeIdx]);

  return (
    <div
      className="audio-transcript"
      ref={containerRef}
      aria-label="Audio captions"
      tabIndex={0}
      role="list"
    >
      {cues.map((c, idx) => (
        <div
          key={idx}
          id={`audio-cue-${idx}`}
          className={`audio-transcript-row ${idx === activeIdx ? 'active' : ''}`}
          onClick={() => onSeek && onSeek(Math.max(0, c.start + 0.01))}
          role="listitem"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onSeek && onSeek(Math.max(0, c.start + 0.01));
            }
          }}
          aria-current={idx === activeIdx ? 'true' : undefined}
        >
          {showTimestamps && (
            <span className="audio-transcript-ts" aria-hidden="true">[{formatTS(c.start)}]</span>
          )}
          <span className="audio-transcript-text">
            {String(c.text)
              .split(/\r?\n/)
              .map((line, i) => (
                <React.Fragment key={i}>
                  {line}
                  {i < String(c.text).split(/\r?\n/).length - 1 ? <br /> : null}
                </React.Fragment>
              ))}
          </span>
        </div>
      ))}
    </div>
  );
};

export default TranscriptList;

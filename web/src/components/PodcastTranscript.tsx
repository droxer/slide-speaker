import React, { useEffect, useMemo, useRef, useState } from 'react';

type Line = { speaker: string; text: string };

function parseConversation(md: string): Line[] {
  const lines: Line[] = [];
  const re = /^\*\*(.+?):\*\*\s*(.+)$/; // **Speaker:** text
  for (const raw of md.split(/\r?\n/)) {
    const s = raw.trim();
    if (!s) continue;
    const m = s.match(re);
    if (m) {
      lines.push({ speaker: m[1].trim(), text: m[2].trim() });
    }
  }
  return lines;
}

export default function PodcastTranscript({
  audioRef,
  markdown,
}: {
  audioRef: React.RefObject<HTMLAudioElement>;
  markdown: string;
}) {
  const lines = useMemo(() => parseConversation(markdown), [markdown]);
  const [activeIdx, setActiveIdx] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    const el = audioRef.current;
    if (!el || lines.length === 0) return;
    let raf: number | null = null;
    const compute = () => {
      const dur = isFinite(el.duration) && el.duration > 0 ? el.duration : 0;
      const cur = el.currentTime || 0;
      const n = Math.max(1, lines.length);
      if (dur <= 0) {
        setActiveIdx(-1);
      } else {
        const idx = Math.min(n - 1, Math.max(0, Math.floor((cur / dur) * n)));
        setActiveIdx(idx);
      }
      raf = requestAnimationFrame(compute);
    };
    raf = requestAnimationFrame(compute);
    return () => {
      if (raf != null) cancelAnimationFrame(raf);
    };
  }, [audioRef, lines.length]);

  useEffect(() => {
    if (activeIdx < 0) return;
    const node = itemRefs.current[activeIdx];
    const container = containerRef.current;
    if (node && container) {
      const parentTop = container.scrollTop;
      const parentBottom = parentTop + container.clientHeight;
      const top = node.offsetTop - container.offsetTop;
      const bottom = top + node.clientHeight;
      if (top < parentTop + 24 || bottom > parentBottom - 24) {
        container.scrollTo({ top: Math.max(0, top - 24), behavior: 'smooth' });
      }
    }
  }, [activeIdx]);

  const onActivate = (i: number) => {
    const el = audioRef.current;
    if (!el || lines.length === 0) return;
    const dur = isFinite(el.duration) && el.duration > 0 ? el.duration : 0;
    if (dur <= 0) return;
    const slice = dur / lines.length;
    const target = Math.max(0, Math.min(dur - 0.05, i * slice + 0.01));
    try {
      if ((el as any).fastSeek) {
        (el as any).fastSeek(target);
      } else {
        el.currentTime = target;
      }
      void el.play().catch(() => {});
    } catch {
      el.currentTime = target;
      void el.play().catch(() => {});
    }
  };

  return (
    <div className="podcast-transcript" ref={containerRef} aria-label="Podcast transcript" role="region">
      {lines.map((ln, i) => (
        <div
          key={i}
          ref={(el) => {
            itemRefs.current[i] = el;
          }}
          className={`conv-line ${i === activeIdx ? 'active' : ''}`}
          role="button"
          tabIndex={0}
          onClick={() => onActivate(i)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onActivate(i);
            }
          }}
          aria-label={`${ln.speaker}: ${ln.text}`}
        >
          <span className="conv-speaker">{ln.speaker}:</span>
          <span className="conv-text">{ln.text}</span>
        </div>
      ))}
      {lines.length === 0 && (
        <div className="conv-empty">No transcript available.</div>
      )}
    </div>
  );
}

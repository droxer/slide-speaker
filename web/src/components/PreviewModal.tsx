import React, { useEffect } from 'react';

type PreviewMode = 'video' | 'audio';

type PreviewModalProps = {
  open: boolean;
  mode: PreviewMode;
  onClose: () => void;
  header: React.ReactNode;
  children: React.ReactNode;
};

const PreviewModal: React.FC<PreviewModalProps> = ({ open, mode, onClose, header, children }) => {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || (e as any).keyCode === 27) {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="video-preview-modal" data-mode={mode} onClick={onClose} role="dialog" aria-modal="true">
      <div className="video-preview-content" data-mode={mode} onClick={(e) => e.stopPropagation()} role="document">
        {header}
        <div className="video-player-container">
          {children}
        </div>
      </div>
    </div>
  );
};

export default PreviewModal;


import React from 'react';

type UploadingViewProps = {
  progress: number;
  fileName?: string | null;
};

const UploadingView: React.FC<UploadingViewProps> = ({ progress, fileName }) => {
  const displayName = typeof fileName === 'string' && fileName.trim().length > 0 ? fileName.trim() : null;
  return (
    <div className="processing-view">
      <div className="spinner"></div>
      <h3>Uploading Your Presentation</h3>
      {displayName && (
        <p className="uploading-file" title={displayName}>
          <span className="uploading-file__icon" aria-hidden>📄</span>
          <span className="uploading-file__text">{displayName}</span>
        </p>
      )}
      <div className="progress-container">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        <p className="progress-text">{progress}% Uploaded</p>
        <p className="processing-status">
          Preparing your content for AI transformation...
        </p>
      </div>
    </div>
  );
};

export default UploadingView;

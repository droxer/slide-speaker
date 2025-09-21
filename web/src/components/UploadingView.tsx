import React from 'react';

type UploadingViewProps = {
  progress: number;
};

const UploadingView: React.FC<UploadingViewProps> = ({ progress }) => {
  return (
    <div className="processing-view">
      <div className="spinner"></div>
      <h3>Uploading Your Presentation</h3>
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
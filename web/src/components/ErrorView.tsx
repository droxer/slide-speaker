import React from 'react';

type ErrorViewProps = {
  onResetForm: () => void;
};

const ErrorView: React.FC<ErrorViewProps> = ({ onResetForm }) => {
  return (
    <div className="error-view">
      <div className="error-icon">⚠️</div>
      <h3>Processing Failed</h3>
      <p className="error-message">
        Something went wrong during video generation. Please try
        again with a different file.
      </p>
      <button onClick={onResetForm} className="primary-btn">
        Try Again
      </button>
    </div>
  );
};

export default ErrorView;
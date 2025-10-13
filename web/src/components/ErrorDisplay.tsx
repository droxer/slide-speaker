'use client';

import React from 'react';
import type { ErrorStageProps } from './types';

const ErrorDisplay = ({ onResetForm }: ErrorStageProps) => {
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

export default ErrorDisplay;
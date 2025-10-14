'use client';

import React from 'react';
import { useI18n } from '@/i18n/hooks';
import type { ErrorStageProps } from './types';

const ErrorDisplay = ({ onResetForm }: ErrorStageProps) => {
  const { t } = useI18n();

  return (
    <div className="error-view">
      <div className="error-icon">⚠️</div>
      <h3>{t('errorDisplay.processingFailed', undefined, 'Processing Failed')}</h3>
      <p className="error-message">
        {t('errorDisplay.processingError', undefined, 'Something went wrong during video generation. Please try again with a different file.')}
      </p>
      <button onClick={onResetForm} className="primary-btn">
        {t('errorDisplay.tryAgain', undefined, 'Try Again')}
      </button>
    </div>
  );
};

export default ErrorDisplay;
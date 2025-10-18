'use client';

import React from 'react';
import { useI18n } from '@/i18n/hooks';

type LoadingPlaceholderProps = {
  type?: 'spinner' | 'card' | 'list' | 'dots' | 'bar' | 'wave';
  size?: 'sm' | 'md' | 'lg';
  message?: string;
  className?: string;
  progress?: number; // For progress bar type
};

const LoadingPlaceholder = ({
  type = 'spinner',
  size = 'md',
  message,
  className = '',
  progress = 0,
}: LoadingPlaceholderProps) => {
  const { t } = useI18n();

  const defaultMessage = message || t('common.loading', undefined, 'Loading...');

  const sizeClass = `spinner-${size}`;

  // Enhanced spinner with multiple animation variants
  if (type === 'spinner') {
    return (
      <div className={`loading-spinner ${className}`} role="status" aria-live="polite">
        <div className={`spinner ${sizeClass}`} aria-hidden="true" />
        <p className="loading-message">{defaultMessage}</p>
      </div>
    );
  }

  // Enhanced card skeleton with more detailed structure
  if (type === 'card') {
    return (
      <div className={`loading-card ${className}`} role="status" aria-live="polite">
        <div className="loading-header">
          <div className="loading-avatar" />
          <div className="loading-title">
            <div className="loading-line" />
            <div className="loading-line" style={{ width: '70%' }} />
          </div>
        </div>
        <div className="loading-content">
          <div className="loading-text" />
          <div className="loading-text" style={{ width: '90%' }} />
          <div className="loading-text" style={{ width: '80%' }} />
          <div className="loading-text" style={{ width: '60%' }} />
        </div>
        <div className="loading-footer">
          <div className="loading-action" />
          <div className="loading-action" style={{ width: '60px' }} />
        </div>
      </div>
    );
  }

  // Enhanced list with more items and better structure
  if (type === 'list') {
    return (
      <div className={`loading-list ${className}`} role="status" aria-live="polite">
        {[...Array(5)].map((_, index) => (
          <div key={index} className="loading-list-item">
            <div className="loading-pulse line-sm" />
            <div className="loading-pulse line-xs" style={{ width: `${70 + (index % 3) * 10}%` }} />
            <div className="loading-pulse line-xs" style={{ width: `${50 + (index % 2) * 20}%` }} />
          </div>
        ))}
      </div>
    );
  }

  // Enhanced dots with better animation and message positioning
  if (type === 'dots') {
    return (
      <div className={`loading-dots ${className}`} role="status" aria-live="polite">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        {message && <span className="loading-message">{defaultMessage}</span>}
      </div>
    );
  }

  // New progress bar type
  if (type === 'bar') {
    const clampedProgress = Math.min(100, Math.max(0, progress));
    return (
      <div className={`loading-bar ${className}`} role="status" aria-live="polite">
        <div className="loading-progress" style={{ width: `${clampedProgress}%` }}>
          <div className="loading-shimmer" />
        </div>
        {message && <p className="loading-message">{defaultMessage}</p>}
      </div>
    );
  }

  // New wave animation type
  if (type === 'wave') {
    return (
      <div className={`loading-wave ${className}`} role="status" aria-live="polite">
        <div className="wave-container">
          {[...Array(5)].map((_, index) => (
            <div key={index} className="wave-bar" style={{ animationDelay: `${index * 0.1}s` }} />
          ))}
        </div>
        {message && <p className="loading-message">{defaultMessage}</p>}
      </div>
    );
  }

  // Default spinner as fallback
  return (
    <div className={`loading-spinner ${className}`} role="status" aria-live="polite">
      <div className={`spinner ${sizeClass}`} aria-hidden="true" />
      <p className="loading-message">{defaultMessage}</p>
    </div>
  );
};

export default LoadingPlaceholder;
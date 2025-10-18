'use client';

import React from 'react';
import { useI18n } from '@/i18n/hooks';
import { getFileTypeIcon } from '@/utils/fileIcons';

type UploadingSummaryItem = {
  key: string;
  label: string;
  value: string;
};

type UploadingOutput = {
  key: string;
  label: string;
  icon?: string;
};

type FileUploadingViewProps = {
  progress: number;
  fileName?: string | null;
  fileSize?: number | null;
  summaryItems?: UploadingSummaryItem[];
  outputs?: UploadingOutput[];
};

const FileUploadingView = ({
  progress,
  fileName,
  fileSize,
  summaryItems = [],
  outputs = [],
}: FileUploadingViewProps) => {
  const { t, locale } = useI18n();

  const displayName = typeof fileName === 'string' && fileName.trim().length > 0 ? fileName.trim() : null;
  const clampedProgress = Number.isFinite(progress)
    ? Math.max(0, Math.min(100, Math.round(progress)))
    : 0;
  const formattedFileSize = React.useMemo(() => {
    if (!Number.isFinite(fileSize ?? NaN) || (fileSize ?? 0) <= 0) return null;
    const size = fileSize as number;
    const units = ['B', 'KB', 'MB', 'GB'];
    let value = size;
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
      value /= 1024;
      index += 1;
    }
    const maximumFractionDigits = value >= 100 || index === 0 ? 0 : value < 10 ? 1 : 0;
    const formatter = new Intl.NumberFormat(locale, { maximumFractionDigits });
    return `${formatter.format(value)} ${units[index]}`;
  }, [fileSize, locale]);
  const hasSummary = summaryItems.length > 0 || outputs.length > 0;
  return (
    <div className="processing-view file-upload-view">
      <div className="file-upload-header">
        <div className="spinner"></div>
        <h3>{t('uploading.title')}</h3>
      </div>

      {displayName && (
        <div className="file-info-card">
          <div className="file-info-content">
            <p className="uploading-file" title={displayName}>
              <span className="file-info-icon">{getFileTypeIcon(displayName)}</span>
              <span className="uploading-file__text">{displayName}</span>
              {formattedFileSize && (
                <span className="uploading-file__meta">{formattedFileSize}</span>
              )}
            </p>
          </div>
        </div>
      )}

      <div
        className="progress-container file-upload-progress"
        role="group"
        aria-label={t('uploading.progressLabel', undefined, 'Upload progress')}
      >
        <div className="progress-header">
          <span className="progress-label">
            {t('uploading.progressLabel', undefined, 'Upload progress')}
          </span>
          <span className="progress-value">
            {clampedProgress}
            <span className="progress-value__suffix">%</span>
          </span>
        </div>
        <div
          className="progress-bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={clampedProgress}
        >
          <div
            className="progress-fill"
            style={{ width: `${clampedProgress}%` }}
          />
        </div>
        <p className="progress-status" aria-live="polite">
          {t('uploading.status', undefined, 'We are preparing your file…')}
        </p>
      </div>
      {hasSummary && (
        <section
          className="uploading-summary"
          role="group"
          aria-label={t('uploading.summaryLabel', undefined, 'Upload summary')}
        >
          {outputs.length > 0 && (
            <div className="uploading-summary__chips" aria-label={t('uploading.outputsLabel', undefined, 'Outputs')}>
              {outputs.map(({ key, label, icon }) => (
                <span key={key} className="uploading-summary__chip">
                  {icon && <span className="uploading-summary__chip-icon" aria-hidden="true">{icon}</span>}
                  <span className="uploading-summary__chip-text">{label}</span>
                </span>
              ))}
            </div>
          )}
          {summaryItems.length > 0 && (
            <dl className="uploading-summary__list">
              {summaryItems.map(({ key, label, value }) => (
                <div key={key} className="uploading-summary__item">
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}
    </div>
  );
};

export default FileUploadingView;

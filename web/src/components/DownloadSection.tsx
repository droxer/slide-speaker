import React from 'react';
import { useI18n } from '@/i18n/hooks';

export type DownloadLinkItem = {
  label: string;
  url: string;
  copyMessage?: string;
  copyLabel?: string;
  key?: string;
  hideInput?: boolean;
};

export type DownloadSectionProps = {
  links: DownloadLinkItem[];
  className?: string;
  id?: string;
};

const DownloadSection = ({ links, className, id }: DownloadSectionProps) => {
  const { t } = useI18n();

  if (!links || links.length === 0) {
    return null;
  }

  const handleCopy = async (item: DownloadLinkItem) => {
    try {
      await navigator.clipboard.writeText(item.url);
      if (item.copyMessage) {
        window.alert(item.copyMessage);
      }
    } catch (error) {
      console.warn('Failed to copy link to clipboard:', error);
    }
  };

  return (
    <div className={`resource-links${className ? ` ${className}` : ''}`} id={id}>
      {links.map((item) => (
        <div className="url-copy-row" key={item.key ?? `${item.label}-${item.url}`}
        >
          <span className="resource-label-inline">{item.label}</span>
          {!item.hideInput && (
            <input type="text" value={item.url} readOnly className="url-input-enhanced" />
          )}
          <button
            type="button"
            className="copy-btn-enhanced"
            onClick={() => handleCopy(item)}
          >
            {item.copyLabel ?? t('actions.copy')}
          </button>
        </div>
      ))}
    </div>
  );
};

export default DownloadSection;

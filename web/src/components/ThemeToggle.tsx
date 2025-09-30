'use client';

import React from 'react';
import {useI18n} from '@/i18n/hooks';
import {useTheme} from '@/theme/ThemeProvider';

type ThemeToggleProps = {
  className?: string;
  ariaLabel?: string;
};

const ThemeToggle: React.FC<ThemeToggleProps> = ({className = '', ariaLabel}) => {
  const {t} = useI18n();
  const {mode, theme, setTheme} = useTheme();

  const label = ariaLabel ?? t('footer.theme.toggleLabel', undefined, 'Theme toggle');
  const classNames = ['view-toggle', 'theme-toggle'];
  if (className) classNames.push(className);

  return (
    <div className={classNames.join(' ')} role="tablist" aria-label={label}>
      <button
        type="button"
        onClick={() => setTheme('auto')}
        className={`toggle-btn ${mode === 'auto' ? 'active' : ''}`}
        title={t('footer.theme.auto', undefined, 'Auto')}
        role="tab"
        aria-selected={mode === 'auto'}
        aria-controls="auto-theme-panel"
      >
        <span className="toggle-text">{t('footer.theme.auto')}</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme('light')}
        className={`toggle-btn ${mode === 'light' && theme === 'light' ? 'active' : ''}`}
        title={t('footer.theme.light', undefined, 'Light')}
        role="tab"
        aria-selected={mode === 'light'}
        aria-controls="light-theme-panel"
      >
        <span className="toggle-text">{t('footer.theme.light')}</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme('dark')}
        className={`toggle-btn ${mode === 'dark' && theme === 'dark' ? 'active' : ''}`}
        title={t('footer.theme.dark', undefined, 'Dark')}
        role="tab"
        aria-selected={mode === 'dark'}
        aria-controls="dark-theme-panel"
      >
        <span className="toggle-text">{t('footer.theme.dark')}</span>
      </button>
    </div>
  );
};

export default ThemeToggle;

'use client';

import React from 'react';
import {useI18n} from '@/i18n/hooks';
import {useTheme} from '@/theme/ThemeProvider';

type ThemeToggleProps = {
  className?: string;
  ariaLabel?: string;
};

const ThemeToggle = ({className = '', ariaLabel}: ThemeToggleProps) => {
  const {t} = useI18n();
  const {mode, theme, setTheme} = useTheme();
  const [hydrated, setHydrated] = React.useState(false);

  React.useEffect(() => {
    setHydrated(true);
  }, []);

  const label = ariaLabel ?? t('footer.theme.toggleLabel', undefined, 'Theme toggle');
  const classNames = ['view-toggle', 'theme-toggle'];
  if (className) classNames.push(className);

  return (
    <div className={classNames.join(' ')} role="tablist" aria-label={label}>
      <button
        type="button"
        onClick={() => setTheme('auto')}
        className={`toggle-btn ${hydrated && mode === 'auto' ? 'active' : ''}`}
        title={t('footer.theme.auto', undefined, 'Auto')}
        role="tab"
        aria-selected={hydrated ? mode === 'auto' : undefined}
        aria-controls="auto-theme-panel"
        suppressHydrationWarning
      >
        <span className="toggle-text">{t('footer.theme.auto')}</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme('light')}
        className={`toggle-btn ${hydrated && mode === 'light' && theme === 'light' ? 'active' : ''}`}
        title={t('footer.theme.light', undefined, 'Light')}
        role="tab"
        aria-selected={hydrated ? mode === 'light' : undefined}
        aria-controls="light-theme-panel"
        suppressHydrationWarning
      >
        <span className="toggle-text">{t('footer.theme.light')}</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme('dark')}
        className={`toggle-btn ${hydrated && mode === 'dark' && theme === 'dark' ? 'active' : ''}`}
        title={t('footer.theme.dark', undefined, 'Dark')}
        role="tab"
        aria-selected={hydrated ? mode === 'dark' : undefined}
        aria-controls="dark-theme-panel"
        suppressHydrationWarning
      >
        <span className="toggle-text">{t('footer.theme.dark')}</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme('high-contrast-light')}
        className={`toggle-btn ${hydrated && mode === 'high-contrast-light' ? 'active' : ''}`}
        title={t('footer.theme.highContrast', undefined, 'High Contrast (Light)')}
        role="tab"
        aria-selected={hydrated ? mode === 'high-contrast-light' : undefined}
        aria-controls="high-contrast-light-theme-panel"
        suppressHydrationWarning
      >
        <span className="toggle-text">{t('footer.theme.highContrast', undefined, 'High Contrast')}</span>
      </button>
      <button
        type="button"
        onClick={() => setTheme('high-contrast-dark')}
        className={`toggle-btn ${hydrated && mode === 'high-contrast-dark' ? 'active' : ''}`}
        title={t('footer.theme.highContrastDark', undefined, 'High Contrast (Dark)')}
        role="tab"
        aria-selected={hydrated ? mode === 'high-contrast-dark' : undefined}
        aria-controls="high-contrast-dark-theme-panel"
        suppressHydrationWarning
      >
        <span className="toggle-text">{t('footer.theme.highContrastDark', undefined, 'HC Dark')}</span>
      </button>
    </div>
  );
};

export default ThemeToggle;

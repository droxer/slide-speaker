import React from 'react';
import { useI18n } from '@/i18n/hooks';

const SkipLinks = () => {
  const { t } = useI18n();

  return (
    <div className="skip-links">
      <a
        href="#main-content"
        className="skip-link"
      >
        {t('accessibility.skipToMain', undefined, 'Skip to main content')}
      </a>
      <a
        href="#navigation"
        className="skip-link"
      >
        {t('accessibility.skipToNavigation', undefined, 'Skip to navigation')}
      </a>
    </div>
  );
};

export default SkipLinks;
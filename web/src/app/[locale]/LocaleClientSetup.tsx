'use client';

import {useEffect} from 'react';

interface LocaleClientSetupProps {
  locale: string;
}

export function LocaleClientSetup({locale}: LocaleClientSetupProps) {
  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }
    document.documentElement.lang = locale;
  }, [locale]);

  return null;
}

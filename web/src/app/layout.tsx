import type {Metadata} from 'next';
import type {ReactNode} from 'react';
import {cookies, headers} from 'next/headers';
import {defaultLocale, locales, type Locale} from '@/i18n/config';
import './globals.scss';
import '@/styles/app.scss';
import '@/styles/dark-theme.scss';
import '@/styles/TaskMonitor.scss';

const themeInitScript = `(() => {
  try {
    const storageKey = 'slidespeaker_ui_theme';
    const stored = window.localStorage.getItem(storageKey);
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored === 'dark' || stored === 'light' ? stored : (prefersDark ? 'dark' : 'light');
    document.body.classList.toggle('dark-theme', theme === 'dark');
    document.body.classList.toggle('light-theme', theme !== 'dark');
  } catch (error) {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.body.classList.toggle('dark-theme', prefersDark);
    document.body.classList.toggle('light-theme', !prefersDark);
  }
})();`;

const deriveLocale = (): Locale => {
  const cookieLocale = cookies().get('NEXT_LOCALE')?.value;
  if (cookieLocale && (locales as ReadonlyArray<string>).includes(cookieLocale)) {
    return cookieLocale as Locale;
  }

  const requestPath = headers().get('next-url');
  if (requestPath) {
    const [, maybeLocale] = requestPath.split('/');
    if (maybeLocale && (locales as ReadonlyArray<string>).includes(maybeLocale)) {
      return maybeLocale as Locale;
    }
  }

  return defaultLocale;
};

export const metadata: Metadata = {
  title: 'SlideSpeaker',
  description: 'Transform presentations into rich multimedia experiences with SlideSpeaker.',
};

export default function RootLayout({children}: Readonly<{children: ReactNode}>) {
  const locale = deriveLocale();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body suppressHydrationWarning>
        <script dangerouslySetInnerHTML={{__html: themeInitScript}} />
        {children}
      </body>
    </html>
  );
}

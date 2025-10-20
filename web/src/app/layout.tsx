import type {Metadata} from 'next';
import type {ReactNode} from 'react';
import {cookies, headers} from 'next/headers';
import {Open_Sans} from 'next/font/google';
import {defaultLocale, locales, type Locale} from '@/i18n/config';
import './globals.scss';

const openSans = Open_Sans({
  subsets: ['latin'],
  display: 'swap',
  weight: ['300', '400', '600', '700'],
  style: ['normal', 'italic'],
});

const themeInitScript = `(() => {
  try {
    const storageKey = 'slidespeaker_ui_theme';
    const stored = window.localStorage.getItem(storageKey);
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const prefersHighContrast = window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches;

    let themeClass = 'theme-light';
    if (stored === 'dark' || stored === 'light' || stored === 'light-hc' || stored === 'dark-hc') {
      if (stored === 'dark') themeClass = 'theme-dark';
      else if (stored === 'light-hc') themeClass = 'theme-light-hc';
      else if (stored === 'dark-hc') themeClass = 'theme-dark-hc';
      else themeClass = 'theme-light'; // light
    } else if (prefersHighContrast) {
      themeClass = prefersDark ? 'theme-dark-hc' : 'theme-light-hc';
    } else {
      themeClass = prefersDark ? 'theme-dark' : 'theme-light';
    }

    const legacyClass = themeClass.includes('dark') ? 'dark-theme' : 'light-theme';
    document.body.classList.add(themeClass);
    document.body.classList.add(legacyClass);
  } catch (error) {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const prefersHighContrast = window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches;

    let themeClass = 'theme-light';
    if (prefersHighContrast) {
      themeClass = prefersDark ? 'theme-dark-hc' : 'theme-light-hc';
    } else {
      themeClass = prefersDark ? 'theme-dark' : 'theme-light';
    }

    const legacyClass = themeClass.includes('dark') ? 'dark-theme' : 'light-theme';
    document.body.classList.add(themeClass);
    document.body.classList.add(legacyClass);
  }
})();`;

const deriveLocale = async (): Promise<Locale> => {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get('NEXT_LOCALE')?.value;
  if (cookieLocale && (locales as ReadonlyArray<string>).includes(cookieLocale)) {
    return cookieLocale as Locale;
  }

  const headerStore = await headers();
  const requestPath = headerStore.get('next-url');
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

export default async function RootLayout({children}: Readonly<{children: ReactNode}>) {
  const locale = await deriveLocale();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={openSans.className} suppressHydrationWarning>
        <script dangerouslySetInnerHTML={{__html: themeInitScript}} />
        {children}
      </body>
    </html>
  );
}

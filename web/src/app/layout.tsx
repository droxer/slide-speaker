import type { Metadata } from 'next';
import type { ReactNode } from 'react';
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

export const metadata: Metadata = {
  title: 'SlideSpeaker',
  description: 'Transform presentations into rich multimedia experiences with SlideSpeaker.',
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{__html: themeInitScript}} />
        {children}
      </body>
    </html>
  );
}

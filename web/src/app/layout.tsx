import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.scss';
import '@/styles/app.scss';
import '@/styles/ultra-flat-overrides.scss';
import '@/styles/subtle-material-overrides.scss';
import '@/styles/classic-overrides.scss';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'SlideSpeaker',
  description: 'Transform presentations into rich multimedia experiences with SlideSpeaker.',
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

import {notFound} from 'next/navigation';
import {unstable_setRequestLocale, getMessages} from 'next-intl/server';
import {NextIntlClientProvider} from 'next-intl';
import type {ReactNode} from 'react';
import {Providers} from '../providers';
import {locales, type Locale} from '@/i18n/config';

export function generateStaticParams() {
  return locales.map((locale) => ({locale}));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: {locale: string};
}) {
  const {locale} = params;
  if (!locales.includes(locale as Locale)) {
    notFound();
  }
  unstable_setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

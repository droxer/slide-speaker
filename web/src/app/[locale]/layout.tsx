import {notFound} from 'next/navigation';
import {unstable_setRequestLocale, getMessages} from 'next-intl/server';
import {NextIntlClientProvider} from 'next-intl';
import type {ReactNode} from 'react';
import {getServerSession} from 'next-auth';
import {Providers} from '../providers';
import {LocaleClientSetup} from './LocaleClientSetup';
import {locales, type Locale} from '@/i18n/config';
import {authOptions} from '@/auth/options';

export function generateStaticParams() {
  return locales.map((locale) => ({locale}));
}

type LocaleLayoutProps = {
  children: ReactNode;
  params: Promise<{ locale: string }>;
};

export default async function LocaleLayout({
  children,
  params,
}: LocaleLayoutProps) {
  const {locale} = await params;
  if (!locales.includes(locale as Locale)) {
    notFound();
  }
  unstable_setRequestLocale(locale);
  const messages = await getMessages();
  const session = await getServerSession(authOptions);

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <Providers session={session}>
        <LocaleClientSetup locale={locale} />
        {children}
      </Providers>
    </NextIntlClientProvider>
  );
}

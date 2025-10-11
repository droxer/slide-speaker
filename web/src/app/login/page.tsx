import {redirect} from 'next/navigation';
import {defaultLocale} from '@/i18n/config';

type RedirectLoginProps = {
  searchParams?: Promise<{redirectTo?: string}>;
};

export default async function RedirectLogin({searchParams}: RedirectLoginProps) {
  const query = searchParams ? await searchParams : undefined;
  const redirectTo = typeof query?.redirectTo === 'string' ? query.redirectTo : undefined;
  const params = new URLSearchParams();
  if (redirectTo) {
    params.set('redirectTo', redirectTo);
  }

  const suffix = params.toString();
  const target = suffix.length > 0 ? `/${defaultLocale}/login?${suffix}` : `/${defaultLocale}/login`;
  redirect(target);
}

import {redirect} from 'next/navigation';
import {defaultLocale} from '@/i18n/config';

type RedirectLoginProps = {
  searchParams?: {redirectTo?: string};
};

export default function RedirectLogin({searchParams}: RedirectLoginProps) {
  const redirectTo = typeof searchParams?.redirectTo === 'string' ? searchParams.redirectTo : undefined;
  const params = new URLSearchParams();
  if (redirectTo) {
    params.set('redirectTo', redirectTo);
  }

  const suffix = params.toString();
  const target = suffix.length > 0 ? `/${defaultLocale}/login?${suffix}` : `/${defaultLocale}/login`;
  redirect(target);
}

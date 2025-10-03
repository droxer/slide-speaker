import {NextResponse} from 'next/server';
import type {NextRequest} from 'next/server';
import {getToken} from 'next-auth/jwt';
import createMiddleware from 'next-intl/middleware';
import {locales, defaultLocale} from './src/i18n/config';
import type {Locale} from './src/i18n/config';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
});

const LANGUAGE_TO_LOCALE: Record<string, Locale> = {
  english: 'en',
  'en': 'en',
  simplified_chinese: 'zh-CN',
  'zh-cn': 'zh-CN',
  traditional_chinese: 'zh-TW',
  'zh-tw': 'zh-TW',
};

const normalizePreferredLocale = (value: unknown): Locale | null => {
  if (typeof value !== 'string') {
    return null;
  }
  const key = value.trim().toLowerCase();
  const resolved = LANGUAGE_TO_LOCALE[key as keyof typeof LANGUAGE_TO_LOCALE];
  return resolved ?? null;
};

const PUBLIC_PATHS = new Set<string>([
  '/login',
  '/api/auth',
]);

const STATIC_PREFIXES = ['/_next', '/_vercel', '/favicon', '/robots.txt', '/sitemap', '/api/auth'];

const isLocale = (value: string): value is Locale =>
  (locales as ReadonlyArray<string>).includes(value);

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) {
    return true;
  }

  if (STATIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return true;
  }

  const segments = pathname.split('/').filter(Boolean);
  if (segments.length === 0) {
    return false;
  }

  const [first, second] = segments;
  if (isLocale(first) && (!second || second === 'login')) {
    return second === 'login';
  }

  return false;
}

export default async function middleware(request: NextRequest) {
  const localeResponse = intlMiddleware(request);

  const pathname = request.nextUrl.pathname;

  if (isPublicPath(pathname)) {
    return localeResponse;
  }

  const token = await getToken({req: request, secret: process.env.NEXTAUTH_SECRET});

  if (!token) {
    const redirectUrl = request.nextUrl.clone();
    const originalTarget = `${pathname}${request.nextUrl.search}`;

    redirectUrl.pathname = '/login';
    redirectUrl.hash = '';
    redirectUrl.search = '';

    if (originalTarget && originalTarget !== '/login') {
      redirectUrl.searchParams.set('redirectTo', originalTarget);
    }

    return NextResponse.redirect(redirectUrl);
  }

  if (pathname.startsWith('/api')) {
    return localeResponse;
  }

  const preferredLocale = normalizePreferredLocale((token as any)?.user?.preferred_language);
  if (preferredLocale) {
    const segments = pathname.split('/').filter(Boolean);
    const [firstSegment] = segments;
    const hasLocalePrefix = isLocale(firstSegment ?? '');

    if (!hasLocalePrefix || firstSegment !== preferredLocale) {
      const targetPathSegments = hasLocalePrefix ? segments.slice(1) : segments;
      const targetPath = targetPathSegments.length > 0 ? `/${targetPathSegments.join('/')}` : '';

      const redirectUrl = request.nextUrl.clone();
      redirectUrl.pathname = `/${preferredLocale}${targetPath}`;
      return NextResponse.redirect(redirectUrl);
    }
  }

  return localeResponse;
}

export const config = {
  matcher: ['/(.*)'],
};

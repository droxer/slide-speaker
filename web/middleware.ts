import {NextResponse} from 'next/server';
import type {NextRequest} from 'next/server';
import {getToken} from 'next-auth/jwt';
import createMiddleware from 'next-intl/middleware';
import {locales, defaultLocale} from './src/i18n/config';
import type {Locale} from './src/i18n/config';
import {normalizePreferredLocale} from './src/utils/localePreferences';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
});

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
  const pathname = request.nextUrl.pathname;

  // Skip locale handling for auth API routes to prevent loops
  if (pathname.startsWith('/api/auth')) {
    return undefined; // Allow NextAuth to handle authentication routes
  }

  if (isPublicPath(pathname)) {
    // For public paths, only run intl middleware (no auth check needed)
    return intlMiddleware(request);
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

  // Check the user's preferred locale  
  const preferredLocale = normalizePreferredLocale((token as any)?.user?.preferred_language);
  
  if (preferredLocale) {
    const segments = pathname.split('/').filter(Boolean);
    const [firstSegment] = segments;
    const hasLocalePrefix = isLocale(firstSegment ?? '');

    // Only redirect if the current path has a locale prefix that differs from the preferred locale
    // or if there's no locale prefix but the user has a preference
    if (!hasLocalePrefix || firstSegment !== preferredLocale) {
      const targetPathSegments = hasLocalePrefix ? segments.slice(1) : segments;
      const targetPath = targetPathSegments.length > 0 ? `/${targetPathSegments.join('/')}` : '';

      const redirectUrl = request.nextUrl.clone();
      redirectUrl.pathname = `/${preferredLocale}${targetPath}`;
      return NextResponse.redirect(redirectUrl);
    }
  }

  // Run the internationalization middleware for other routes
  return intlMiddleware(request);
}

export const config = {
  matcher: ['/(.*)'],
};

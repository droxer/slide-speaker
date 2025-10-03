const sanitizeBaseUrl = (value: string): string => value.replace(/\/+$/, '');

const DEV_FALLBACK = 'http://localhost:8000';

export const resolveApiBaseUrl = (): string => {
  const envValue = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.API_BASE_URL;
  if (envValue && envValue.length > 0) {
    return sanitizeBaseUrl(envValue);
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error('NEXT_PUBLIC_API_BASE_URL must be configured outside development environments.');
  }

  if (typeof window === 'undefined') {
    return DEV_FALLBACK;
  }

  const {protocol = 'http:', hostname = 'localhost'} = window.location ?? {};
  if (!hostname) {
    return DEV_FALLBACK;
  }

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return DEV_FALLBACK;
  }

  const origin = window.location.origin ?? `${protocol}//${hostname}`;
  return sanitizeBaseUrl(origin);
};

export default resolveApiBaseUrl;

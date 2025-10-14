const DEV_FALLBACK = 'http://localhost:8000';

const stripTrailingSlashes = (url: string): string => url.replace(/\/+$/, '');

export const resolveApiBaseUrl = (): string => {
  // Use environment variable if available
  const envValue = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.API_BASE_URL;
  if (envValue) {
    return stripTrailingSlashes(envValue);
  }

  // For production, require explicit configuration
  if (process.env.NODE_ENV === 'production') {
    throw new Error('NEXT_PUBLIC_API_BASE_URL must be configured in production.');
  }

  // Use localhost fallback in development
  if (typeof window === 'undefined' || !window.location.hostname) {
    return DEV_FALLBACK;
  }

  const { hostname } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return DEV_FALLBACK;
  }

  return stripTrailingSlashes(window.location.origin);
};

export default resolveApiBaseUrl;

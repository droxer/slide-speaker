const trimTrailingSlashes = (value: string): string => value.replace(/\/+$/, '');

const DEV_FALLBACK = 'http://localhost:8000';

export const resolveServerApiBaseUrl = (): string => {
  const envUrl = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl && envUrl.length > 0) {
    return trimTrailingSlashes(envUrl);
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error('API_BASE_URL (or NEXT_PUBLIC_API_BASE_URL) must be configured outside development environments.');
  }

  return DEV_FALLBACK;
};

export default resolveServerApiBaseUrl;

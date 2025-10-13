const stripTrailingSlashes = (url: string): string => url.replace(/\/+$/, '');

const DEV_FALLBACK = 'http://localhost:8000';

export const resolveServerApiBaseUrl = (): string => {
  const envValue = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envValue) {
    return stripTrailingSlashes(envValue);
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error('API_BASE_URL must be configured in production.');
  }

  return DEV_FALLBACK;
};

export default resolveServerApiBaseUrl;

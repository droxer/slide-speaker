const trimTrailingSlashes = (value: string): string => value.replace(/\/+$/, '');

export const resolveServerApiBaseUrl = (): string => {
  const envUrl = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl && envUrl.length > 0) {
    return trimTrailingSlashes(envUrl);
  }
  return 'http://localhost:8000';
};

export default resolveServerApiBaseUrl;

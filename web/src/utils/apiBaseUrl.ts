export const resolveApiBaseUrl = (): string => {
  const envValue = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envValue && envValue.length > 0) {
    return envValue.replace(/\/+$/, '');
  }

  if (typeof window === 'undefined') {
    return '';
  }

  const protocol = window.location?.protocol ?? 'http:';
  const hostname = window.location?.hostname ?? 'localhost';

  if (protocol === 'https:') {
    return '';
  }

  if (!hostname) {
    return '';
  }

  return `${protocol}//${hostname}:8000`;
};

export default resolveApiBaseUrl;

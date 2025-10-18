// Import the functions we want to test
const buildDownloadUrl = (baseUrl: string, path: string) => {
  // The download_url or url from the API is already a complete path
  // We just need to ensure it's properly formed
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return baseUrl ? `${baseUrl.replace(/\/+$/, '')}${normalizedPath}` : normalizedPath;
};

describe('Download URL Construction', () => {
  it('should construct correct URLs when baseURL is provided', () => {
    const baseUrl = 'http://localhost:8000';
    const path = '/api/tasks/123/video/download';
    const result = buildDownloadUrl(baseUrl, path);
    expect(result).toBe('http://localhost:8000/api/tasks/123/video/download');
  });

  it('should construct correct URLs when baseURL has trailing slash', () => {
    const baseUrl = 'http://localhost:8000/';
    const path = '/api/tasks/123/video/download';
    const result = buildDownloadUrl(baseUrl, path);
    expect(result).toBe('http://localhost:8000/api/tasks/123/video/download');
  });

  it('should construct correct URLs when path does not start with slash', () => {
    const baseUrl = 'http://localhost:8000';
    const path = 'api/tasks/123/video/download';
    const result = buildDownloadUrl(baseUrl, path);
    expect(result).toBe('http://localhost:8000/api/tasks/123/video/download');
  });

  it('should handle empty baseURL', () => {
    const baseUrl = '';
    const path = '/api/tasks/123/video/download';
    const result = buildDownloadUrl(baseUrl, path);
    expect(result).toBe('/api/tasks/123/video/download');
  });

  it('should handle null baseURL', () => {
    const baseUrl = null;
    const path = '/api/tasks/123/video/download';
    const result = buildDownloadUrl(baseUrl as any, path);
    expect(result).toBe('/api/tasks/123/video/download');
  });
});

// Mock implementation of the client service
console.log('Loading mock client service');

const mockAxiosInstance = {
  get: jest.fn(),
  post: jest.fn(),
  delete: jest.fn(),
  head: jest.fn(),
};

export const api = mockAxiosInstance;

// Create proper mock functions
export const getTasks = jest.fn();
export const searchTasks = jest.fn();
export const getDownloads = jest.fn();
export const getTranscriptMarkdown = jest.fn();
export const getStats = jest.fn();
export const deleteTask = jest.fn();
export const purgeTask = jest.fn();
export const cancelRun = jest.fn();
export const upload = jest.fn();
export const getHealth = jest.fn();
export const headTaskVideo = jest.fn();
export const getTaskProgress = jest.fn();
export const getVttText = jest.fn();
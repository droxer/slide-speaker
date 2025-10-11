// Lightweight stub for axios client mocks when Jest is not installed.
const notImplemented = async () => {
  throw new Error("Mock client function not implemented.");
};

export const api = {
  get: notImplemented,
  post: notImplemented,
  delete: notImplemented,
  head: notImplemented,
};

export const getTasks = notImplemented;
export const searchTasks = notImplemented;
export const getDownloads = notImplemented;
export const getTranscriptMarkdown = notImplemented;
export const getStats = notImplemented;
export const deleteTask = notImplemented;
export const purgeTask = notImplemented;
export const cancelRun = notImplemented;
export const upload = notImplemented;
export const getHealth = notImplemented;
export const headTaskVideo = notImplemented;
export const getTaskProgress = notImplemented;
export const getVttText = notImplemented;

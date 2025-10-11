// Jest mock placeholder removed as Jest is no longer in use.
// This stub allows existing import paths to resolve without bundling test helpers.
const notImplemented = async () => {
  throw new Error('Mocked client function not implemented.');
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

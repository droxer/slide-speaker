import type { Task } from '@/types';

const humanizeTaskTypeInternal = (value: string): string =>
  value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Task';

const coerceBoolean = (fallback: boolean, ...values: Array<unknown>): boolean => {
  for (const value of values) {
    if (typeof value === 'boolean') {
      return value;
    }
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase();
      if (normalized === 'true') return true;
      if (normalized === 'false') return false;
    }
  }
  return fallback;
};

export const resolveTaskType = (
  task?: Task | null,
  state?: Record<string, unknown> | null,
): { key: string; fallbackLabel: string } => {
  const taskType =
    (task?.task_type ?? state?.task_type ?? '')?.toString().toLowerCase() || '';
  if (taskType) {
    return { key: taskType, fallbackLabel: humanizeTaskTypeInternal(taskType) };
  }

  const videoFlag = coerceBoolean(
    true,
    (task as any)?.generate_video,
    task?.kwargs?.generate_video,
    state?.generate_video,
  );
  const podcastFlag = coerceBoolean(
    false,
    (task as any)?.generate_podcast,
    task?.kwargs?.generate_podcast,
    state?.generate_podcast,
  );
  const audioFlag = coerceBoolean(
    false,
    (task as any)?.generate_audio,
    (task?.kwargs as any)?.generate_audio,
    state?.generate_audio,
  );

  let key = 'unknown';
  if (podcastFlag && videoFlag) {
    key = 'both';
  } else if (podcastFlag) {
    key = 'podcast';
  } else if (videoFlag) {
    key = 'video';
  } else if (audioFlag) {
    key = 'audio';
  }

  return { key, fallbackLabel: humanizeTaskTypeInternal(key) };
};

export const humanizeTaskType = (value: string): string =>
  humanizeTaskTypeInternal(value);

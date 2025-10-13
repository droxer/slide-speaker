type TranslateFn = (key: string, vars?: Record<string, string | number>, fallback?: string) => string;

export type TaskStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'pending'
  | 'skipped'
  | string;

const STATUS_CLASS_MAP: Record<string, string> = {
  completed: 'status-completed',
  processing: 'status-processing',
  queued: 'status-queued',
  failed: 'status-failed',
  cancelled: 'status-cancelled',
  pending: 'status-queued',
  upload_only: 'status-default',
};

export const TASK_STATUS_ICONS: Record<string, string> = {
  completed: '✓',
  processing: '⏳',
  queued: '⏸️',
  failed: '❌',
  cancelled: '🚫',
  pending: '•',
  skipped: '⤼',
  upload_only: '⬆️',
};

export const normalizeTaskStatus = (status?: string | null): TaskStatus => {
  const normalized = String(status ?? '').toLowerCase().trim();
  if (!normalized) return 'unknown';
  switch (normalized) {
    case 'completed':
    case 'processing':
    case 'queued':
    case 'failed':
    case 'cancelled':
    case 'pending':
    case 'skipped':
      return normalized;
    default:
      return normalized;
  }
};

export const getTaskStatusClass = (status?: string | null): string => {
  const key = normalizeTaskStatus(status);
  return STATUS_CLASS_MAP[key] ?? 'status-default';
};

export const getTaskStatusIcon = (status?: string | null): string => {
  const key = normalizeTaskStatus(status);
  return TASK_STATUS_ICONS[key] ?? '•';
};

export const getTaskStatusLabel = (
  status: string | null | undefined,
  translate?: TranslateFn,
): string => {
  const key = normalizeTaskStatus(status);
  if (translate) {
    // Prefer existing translation key, fall back to capitalised status.
    return translate(`task.status.${key}`, undefined, capitalizeStatus(key));
  }
  return capitalizeStatus(key);
};

const capitalizeStatus = (status: string): string => {
  if (!status) return 'Unknown';
  if (status === 'unknown') return 'Unknown';
  return status
    .split(/[_-]/)
    .map((part) => (part ? part.charAt(0).toUpperCase() + part.slice(1) : ''))
    .join(' ');
};

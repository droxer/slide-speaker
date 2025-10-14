type TranslateFn = (key: string, vars?: Record<string, string | number>, fallback?: string) => string;

export type TaskStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'pending' | 'skipped' | string;

const STATUS_CLASSES: Record<string, string> = {
  completed: 'status-completed',
  processing: 'status-processing',
  queued: 'status-queued',
  failed: 'status-failed',
  cancelled: 'status-cancelled',
  pending: 'status-queued',
  upload_only: 'status-default',
};

export const STATUS_ICONS: Record<string, string> = {
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
  
  const validStatuses: TaskStatus[] = ['completed', 'processing', 'queued', 'failed', 'cancelled', 'pending', 'skipped'];
  return validStatuses.includes(normalized) ? normalized : normalized;
};

export const getTaskStatusClass = (status?: string | null): string => 
  STATUS_CLASSES[normalizeTaskStatus(status)] ?? 'status-default';

export const getTaskStatusIcon = (status?: string | null): string => 
  STATUS_ICONS[normalizeTaskStatus(status)] ?? '•';

export const getTaskStatusLabel = (status: string | null | undefined, translate?: TranslateFn): string => {
  const normalized = normalizeTaskStatus(status);
  
  if (translate) {
    return translate(`task.status.${normalized}`, undefined, formatStatus(normalized));
  }
  
  return formatStatus(normalized);
};

const formatStatus = (status: string): string => {
  if (!status || status === 'unknown') return 'Unknown';
  
  return status
    .split(/[_-]/)
    .map(part => part ? part.charAt(0).toUpperCase() + part.slice(1) : '')
    .join(' ');
};

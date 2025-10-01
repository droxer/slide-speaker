import resolveServerApiBaseUrl from '@/utils/serverApiBaseUrl';
import type { HealthStatus } from '@/types/health';

const HEALTH_REVALIDATE_SECONDS = 300;

export const healthRevalidate = HEALTH_REVALIDATE_SECONDS;

export async function loadInitialHealth(): Promise<HealthStatus | null> {
  try {
    const baseUrl = resolveServerApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/health`, {
      next: { revalidate: HEALTH_REVALIDATE_SECONDS },
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as HealthStatus;
  } catch (error) {
    console.warn('[loadInitialHealth] failed to prefetch health data:', error);
    return null;
  }
}

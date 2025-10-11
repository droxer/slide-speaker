import {cookies} from 'next/headers';
import resolveServerApiBaseUrl from '@/utils/serverApiBaseUrl';
import type { HealthStatus } from '@/types/health';

const HEALTH_REVALIDATE_SECONDS = 300;

export const healthRevalidate = HEALTH_REVALIDATE_SECONDS;

export async function loadInitialHealth(): Promise<HealthStatus | null> {
  try {
    const baseUrl = resolveServerApiBaseUrl();
    const cookieStore = await cookies();
    const cookieHeader = cookieStore
      .getAll()
      .map(({name, value}) => `${name}=${value}`)
      .join('; ');

    const headers: Record<string, string> = {Accept: 'application/json'};
    if (cookieHeader) {
      headers.Cookie = cookieHeader;
    }

    const response = await fetch(`${baseUrl}/api/health`, {
      next: {revalidate: HEALTH_REVALIDATE_SECONDS},
      headers,
      credentials: 'include',
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

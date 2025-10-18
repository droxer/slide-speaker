import {useMemo} from 'react';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {getHealth as apiHealth} from '@/services/client';
import type {HealthStatus} from '@/types/health';

export type UseHealthStatusOptions = {
  initialHealth?: HealthStatus | null;
};

// Prefetch health status for better performance
export const prefetchHealthStatus = async (queryClient: any) => {
  await queryClient.prefetchQuery({
    queryKey: ['health'],
    queryFn: apiHealth,
    staleTime: 300_000, // 5 minutes
  });
};

export function useHealthStatus({initialHealth = null}: UseHealthStatusOptions) {
  const queryClient = useQueryClient();

  const healthQuery = useQuery<HealthStatus | null>({
    queryKey: ['health'],
    queryFn: apiHealth,
    refetchInterval: 300_000,
    refetchOnWindowFocus: false,
    staleTime: 300_000,
    initialData: initialHealth ?? undefined,
    // Disable polling when page is not visible to enable bfcache
    refetchIntervalInBackground: false,
  });

  // Prefetch health status when the hook is used
  useMemo(() => {
    prefetchHealthStatus(queryClient).catch(console.warn);
  }, [queryClient]);

  const health = healthQuery.data ?? null;

  const queueUnavailable = useMemo(() => !(health?.redis?.ok === true), [health?.redis?.ok]);

  const redisLatencyMs = useMemo(() => {
    const latency = health?.redis?.latency_ms;
    return typeof latency === 'number' ? Math.round(latency) : null;
  }, [health?.redis?.latency_ms]);

  return {
    health,
    queueUnavailable,
    redisLatencyMs,
  };
}

export default useHealthStatus;

import {useMemo} from 'react';
import {useQuery} from '@tanstack/react-query';
import {getHealth as apiHealth} from '@/services/client';
import type {HealthStatus} from '@/types/health';

export type UseHealthStatusOptions = {
  initialHealth?: HealthStatus | null;
};

export function useHealthStatus({initialHealth = null}: UseHealthStatusOptions) {
  const healthQuery = useQuery<HealthStatus | null>({
    queryKey: ['health'],
    queryFn: apiHealth,
    refetchInterval: 300_000,
    refetchOnWindowFocus: false,
    staleTime: 300_000,
    initialData: initialHealth ?? undefined,
  });

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

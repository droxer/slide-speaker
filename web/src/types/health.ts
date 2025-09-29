export type HealthStatus = {
  status: 'ok' | 'degraded' | 'down' | (string & {});
  redis: {
    ok: boolean;
    latency_ms?: number;
    error?: string;
  } & Record<string, unknown>;
  db: {
    ok: boolean;
    latency_ms?: number;
    error?: string;
  } & Record<string, unknown>;
  [key: string]: unknown;
};

export default HealthStatus;

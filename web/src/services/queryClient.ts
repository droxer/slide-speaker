import { QueryClient, QueryCache } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // More intelligent retry logic
        if (failureCount > 2) return false;
        // Don't retry on 4xx errors
        if ((error as any)?.response?.status >= 400 && (error as any)?.response?.status < 500) {
          return false;
        }
        return true;
      },
      staleTime: 30_000, // Increase to 30 seconds for better performance
      gcTime: 5 * 60_000, // Keep 5 minutes
    },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      console.warn('Query error:', query.queryKey, error);
    },
  }),
});

export default queryClient;


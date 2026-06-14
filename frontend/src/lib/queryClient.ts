import { QueryClient } from '@tanstack/react-query'

// staleTime alto en lo pasivo; sin polling global (AGENTS §8). El auto-refresh
// acotado ("modo en vivo") se hace por-vista, no aquí.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

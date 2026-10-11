import { useQuery } from '@tanstack/vue-query'
import { loadCases } from './experiments'

/** Shared live registry; availability is always supplied by the backend. */
export function useCaseRegistry() {
  return useQuery({
    queryKey: ['v2', 'case-registry'],
    queryFn: ({ signal }) => loadCases(signal),
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: false,
  })
}

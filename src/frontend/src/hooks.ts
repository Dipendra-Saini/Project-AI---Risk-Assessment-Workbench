import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type CaseDetail, type Chunk } from "./api";

export function useCase(id: number) {
  return useQuery({
    queryKey: ["case", id],
    queryFn: () => api<CaseDetail>(`/cases/${id}`),
    refetchInterval: (q) => (q.state.data?.pipeline_state === "running" ? 1200 : false),
  });
}

/** Run an action that returns the updated case and write it straight into the cache. */
export function useCaseAction(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fn: () => Promise<CaseDetail>) => fn(),
    onSuccess: (data) => {
      qc.setQueryData(["case", id], data);
      qc.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useChunk(id: string | null) {
  return useQuery({
    queryKey: ["chunk", id],
    queryFn: () => api<Chunk>(`/policy/chunks/${encodeURIComponent(id!)}`),
    enabled: Boolean(id),
    staleTime: Infinity,
  });
}

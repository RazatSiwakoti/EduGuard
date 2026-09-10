import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { watchlistService } from "../services/watchlistService";

export const WATCHLIST_KEY = ["lecturer-watchlist"];

export function useWatchlist() {
  return useQuery({ queryKey: WATCHLIST_KEY, queryFn: watchlistService.list, staleTime: 60_000 });
}

export function useToggleWatchlist() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ studentId, unitId, watching }: { studentId: number; unitId: number; watching: boolean }) => {
      if (watching) await watchlistService.remove(studentId, unitId);
      else await watchlistService.add(studentId, unitId);
    },
    onSuccess: () => client.invalidateQueries({ queryKey: WATCHLIST_KEY }),
  });
}

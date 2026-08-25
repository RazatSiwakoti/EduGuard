import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "../services/dashboardService";

const KEY = ["lecturer-dashboard"];

/**
 * Loads the lecturer's full dashboard payload.
 *
 * No mutations live here on purpose: the dashboard is read-only, and
 * recomputing risk stays on the existing "Run Analysis" endpoint. That
 * means simply opening or refreshing this page can never kick off an
 * expensive ML run by accident.
 *
 * staleTime is 60s because risk scores only change when a lecturer
 * uploads data or explicitly re-runs the analysis — not continuously.
 * Refetching on every window focus would be pure noise.
 */
export function useLecturerDashboard(checkpointWeek = 8) {
  return useQuery({
    queryKey: [...KEY, checkpointWeek],
    queryFn: () => dashboardService.get(checkpointWeek),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}
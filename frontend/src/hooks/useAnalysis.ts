import { useMutation, useQueryClient } from "@tanstack/react-query";
import { analysisService } from "../services/analysisService";

/**
 * Running an analysis changes EVERY number on EVERY screen.
 *
 * Risk tiers, the dashboard's charts, the students table, the alert
 * queue, the reports, the Needs Review list — all of them are views of
 * the verdict tables this mutation rewrites. Invalidating only the page
 * the button happens to sit on is how a lecturer ends up looking at a
 * dashboard that contradicts the summary they were just shown.
 *
 * So this clears the lot. The cost is a handful of refetches; the
 * alternative is a UI that quietly disagrees with itself.
 */
export function useRunAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vars: { unitId?: number | null; checkpointWeek?: number | null }) =>
      analysisService.run(vars.unitId, vars.checkpointWeek),
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });
}
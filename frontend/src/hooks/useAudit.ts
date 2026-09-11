import { useQuery } from "@tanstack/react-query";
import { auditService } from "../services/auditService";
import type { AuditQuery } from "../types/audit";

const ACTIONS_KEY = ["admin-audit-actions"];
const EVENTS_KEY = ["admin-audit-events"];

/** The action vocabulary is a closed set that changes only when the code does. */
export function useAuditActions() {
  return useQuery({ queryKey: ACTIONS_KEY, queryFn: auditService.getActions, staleTime: Infinity });
}

export function useAuditEvents(query: AuditQuery) {
  return useQuery({
    queryKey: [...EVENTS_KEY, query.action, query.search, query.days, query.page],
    queryFn: () => auditService.getEvents(query),
    staleTime: 10_000,
    // Keeps the previous page on screen while the next one loads, so
    // paging through a log does not flash empty between clicks.
    placeholderData: (previous) => previous,
  });
}
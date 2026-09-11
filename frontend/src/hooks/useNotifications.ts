

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationService } from "../services/notificationService";
import type { NotificationKind } from "../types/notifications";

const KEY = ["notifications"];

/**
 * The bell's feed.
 *
 * POLLED, not pushed. Everything here is derived from tables the app
 * already writes to, so the only way the browser learns that a student
 * opened their alert is to ask again. Sixty seconds is chosen against
 * what actually changes: the outbox drains on a one-minute cron
 * (scheduler.py), so a faster poll cannot surface a send any sooner and
 * would only multiply a four-table query across every open tab.
 *
 * refetchOnWindowFocus is ON here, deliberately against the pattern
 * every other hook in this project follows. The dashboard turns it off
 * because risk scores only move when someone runs an analysis. A
 * notification feed is the one surface where returning to the tab is
 * exactly the moment you want fresh data.
 */
export function useNotifications(limit = 6, kind?: NotificationKind) {
  return useQuery({
    queryKey: [...KEY, limit, kind],
    queryFn: () => notificationService.getFeed({ limit, kind }),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

export function useNotificationKinds() {
  return useQuery({
    queryKey: [...KEY, "kinds"],
    queryFn: notificationService.getKinds,
    staleTime: Infinity,
  });
}

export function useMarkNotificationsSeen() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: notificationService.markSeen,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
    },
  });
}
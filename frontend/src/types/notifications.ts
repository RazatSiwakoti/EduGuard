export type NotificationKind = "alert_acknowledged" | "alert_failed" | "sweep_summary" |
  "review_pending" | "missing_data" | "import_complete" | "criteria_changed" |
  "verdict_overridden" | "unit_unassigned" | "unit_unconfigured" | "follow_up_due";

export type Severity = "info" | "success" | "warning" | "critical";

export interface NotificationKindOption {
  key: NotificationKind;
  label: string;
}

export interface NotificationItem {
  id: string;
  kind: NotificationKind;
  severity: Severity;
  title: string;
  detail: string | null;
  occurred_at: string;
  link: string | null;
  unread: boolean;
}

export interface NotificationFeed {
  items: NotificationItem[];
  unread_count: number;
  seen_at: string | null;
}

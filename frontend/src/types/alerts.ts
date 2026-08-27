/** Types for the Alerts page (Phase 7.8). */

import type { RiskTier } from "./dashboard";

export type AlertStatus = "queued" | "sent" | "failed";

export interface AlertCounters {
  total: number;
  sent: number;
  failed: number;
  queued: number;
}

export interface AlertSummary {
  counters: AlertCounters;
  unit_count: number;
  checkpoint_week: number;
  dry_run: boolean;
  outbox_path: string | null;
}

export interface QueueItem {
  student_id: number;
  student_number: string;
  name: string;
  email: string | null;
  unit_id: number;
  unit_code: string;
  risk_tier: RiskTier | null;
  eligible: boolean;
  blocked_reason: string | null;
  blocked_detail: string | null;
  last_alert_at: string | null;
  last_alert_status: AlertStatus | null;
}

export interface AlertQueue {
  ready: QueueItem[];
  blocked: QueueItem[];
}

export interface AlertLogItem {
  id: number;
  kind: "student_alert" | "lecturer_summary";
  student_id: number | null;
  student_name: string | null;
  student_number: string | null;
  unit_code: string | null;
  recipient_email: string;
  subject: string;
  body: string;
  template_name: string | null;
  risk_tier: RiskTier | null;
  trigger: "automatic" | "manual";
  status: AlertStatus;
  error: string | null;
  attempts: number;
  queued_at: string | null;
  sent_at: string | null;
}

export interface AlertLogPage {
  items: AlertLogItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmailTemplate {
  id: number;
  name: string;
  risk_tier: RiskTier;
  subject: string;
  body: string;
  is_system: boolean;
  updated_at: string | null;
}

export interface TemplateSave {
  name: string;
  risk_tier: RiskTier;
  subject: string;
  body: string;
}

export interface Placeholder {
  key: string;
  description: string;
}

export interface SendRequest {
  student_id: number;
  unit_id: number;
  template_id?: number;
}

export interface AlertPreview {
  student_id: number;
  unit_id: number;
  recipient_email: string | null;
  recipient_name: string | null;
  subject: string;
  body: string;
  template_id: number | null;
  template_name: string | null;
  eligible: boolean;
  blocked_reason: string | null;
  blocked_detail: string | null;
}

export interface SendResult {
  queued: number;
  sent: number;
  failed: number;
  skipped: Record<string, number>;
}

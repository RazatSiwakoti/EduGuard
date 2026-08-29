/** Types for the admin audit log. */

export interface AuditAction {
  key: string;
  label: string;
  description: string;
}

export interface AuditEvent {
  id: number;
  occurred_at: string | null;
  action: string;
  /** Resolved server-side, so renaming an action never rewrites history. */
  action_label: string;

  /** Null once the account is deleted. The captured name and email below survive that. */
  actor_id: number | null;
  actor_name: string | null;
  actor_email: string | null;
  actor_role: string | null;

  unit_id: number | null;
  unit_code: string | null;
  student_id: number | null;
  student_name: string | null;

  entity_type: string | null;
  entity_id: number | null;

  /** A finished sentence written where the change happened. Print it; don't rebuild it. */
  summary: string;
  /** Raw JSON text, shown only when a row is expanded. */
  before_state: string | null;
  after_state: string | null;

  ip_address: string | null;
  user_agent: string | null;
}

export interface AuditEventPage {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditQuery {
  action: string | null;
  search: string;
  days: number | null;
  page: number;
}
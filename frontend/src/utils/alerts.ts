import type { RiskTier } from "../types/dashboard";
import type { QueueItem } from "../types/alerts";

export function queueKey(item: QueueItem): string {
  return `${item.student_id}-${item.unit_id}`;
}

export interface TemplateDraft {
  name: string;
  risk_tier: RiskTier;
  subject: string;
  body: string;
}

export const EMPTY_DRAFT: TemplateDraft = {
  name: "",
  risk_tier: "high_risk",
  subject: "",
  body: "",
};

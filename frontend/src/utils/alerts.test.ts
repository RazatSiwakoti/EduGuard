import { describe, expect, it } from "vitest";
import { EMPTY_DRAFT, queueKey } from "./alerts";
import type { QueueItem } from "../types/alerts";

describe("alert helpers", () => {
  it("creates a stable student/unit queue key", () => {
    const item: QueueItem = {
      student_id: 4,
      student_number: "S4",
      name: "Student",
      email: null,
      unit_id: 9,
      unit_code: "CS101",
      risk_tier: null,
      eligible: true,
      blocked_reason: null,
      blocked_detail: null,
      last_alert_at: null,
      last_alert_status: null,
    };
    expect(queueKey(item)).toBe("4-9");
  });

  it("provides an empty template draft", () => {
    expect(EMPTY_DRAFT).toEqual({
      name: "",
      risk_tier: "high_risk",
      subject: "",
      body: "",
    });
  });
});

import { describe, expect, it } from "vitest";
import { computeKpis, countByBucket, getBucket } from "./dashboardAggregations";
import type { DashboardFilters, DashboardStudent } from "../types/dashboard";

const student = (overrides: Partial<DashboardStudent> = {}): DashboardStudent => ({
  student_id: 1,
  student_number: "S1",
  name: "Student",
  email: null,
  program: null,
  gender: null,
  age: null,
  unit_id: 1,
  unit_code: "CS101",
  full_code: "CS101",
  analysed: true,
  final_tier: "safe",
  requires_review: false,
  is_missing_data: false,
  reason: null,
  checkpoint_week: 1,
  computed_at: null,
  rule_tier: "safe",
  rule_score: 0.9,
  ml_tier: "safe",
  ml_score: 0.9,
  is_incomplete: false,
  criteria: [],
  ...overrides,
});

const filters: DashboardFilters = { unitId: null, bucket: null };

describe("dashboard aggregations", () => {
  it("prioritises not analysed and review buckets", () => {
    expect(getBucket(student({ analysed: false }))).toBe("not_analysed");
    expect(getBucket(student({ requires_review: true }))).toBe("needs_review");
  });

  it("computes stable KPI counts and percentages", () => {
    const students = [
      student(),
      student({ student_id: 2, final_tier: "high_risk" }),
      student({ student_id: 3, analysed: false, final_tier: null }),
    ];
    expect(computeKpis(students, [], filters)).toEqual({
      totalStudents: 3,
      highRisk: 1,
      needsReview: 0,
      notAnalysed: 1,
      unitCount: 0,
      highRiskPercent: 50,
    });
    expect(countByBucket(students).map((item) => item.bucket)).toEqual([
      "high_risk",
      "safe",
      "not_analysed",
    ]);
  });
});

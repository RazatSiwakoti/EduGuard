import { describe, expect, it } from "vitest";
import { shapeTotal, validateShape, type ShapeRow } from "./unitShape";
import type { ShapeLimits } from "../types/unitShape";

const limits: ShapeLimits = {
  max_assessments: 3,
  max_total_percentage: 100,
  quiz_max_percentage: 20,
  tutorial_percentage: 10,
};

const row = (percentage: string, kind: ShapeRow["kind"] = "assignment"): ShapeRow => ({
  key: percentage,
  id: null,
  name: "Assessment",
  kind,
  percentage,
});

describe("unit shape validation", () => {
  it("includes the fixed tutorial share in the rounded total", () => {
    expect(shapeTotal([row("33.33"), row("33.33"), row("33.33")], true, limits)).toBe(109.99);
  });

  it("rejects quiz percentages above the server-provided limit", () => {
    const result = validateShape([row("21", "quiz")], false, limits);
    expect(result.valid).toBe(false);
    expect(result.rowErrors["21"]).toContain("quiz");
  });
});

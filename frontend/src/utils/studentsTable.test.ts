import { describe, expect, it } from "vitest";
import { countsByBucket, pageCount, pageSlice, searchStudents } from "./studentsTable";
import type { DashboardStudent } from "../types/dashboard";

const student = (id: number, name: string): DashboardStudent => ({
  student_id: id,
  student_number: `S${id}`,
  name,
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
});

describe("students table helpers", () => {
  it("searches names, numbers and unit codes", () => {
    expect(searchStudents([student(1, "Ada Lovelace")], "ada")).toHaveLength(1);
    expect(searchStudents([student(1, "Ada Lovelace")], "S1")).toHaveLength(1);
  });

  it("keeps pagination one-indexed and counts all buckets", () => {
    const rows = [student(1, "A"), student(2, "B")];
    expect(pageCount(17, 8)).toBe(3);
    expect(pageSlice(rows, 2, 1)).toEqual([rows[1]]);
    expect(countsByBucket(rows).safe).toBe(2);
  });
});

import { describe, expect, it } from "vitest";
import { usesLecturerSurface } from "./teaching";
import type { User } from "../types/auth";

const user = (role: User["role"], holds_units: boolean): User => ({
  id: 1,
  email: "test@example.com",
  full_name: "Test User",
  avatar: null,
  role,
  is_active: true,
  created_at: "",
  last_login: "",
  holds_units,
  preferences: {
    theme: "system",
    font_size: "default",
    reduce_motion: false,
    high_contrast: false,
    colourblind_safe: false,
  },
});

describe("usesLecturerSurface", () => {
  it("keeps lecturers on the lecturer surface even without units", () => {
    expect(usesLecturerSurface(user("lecturer", false))).toBe(true);
  });

  it("uses holds_units for admins", () => {
    expect(usesLecturerSurface(user("admin", true))).toBe(true);
    expect(usesLecturerSurface(user("admin", false))).toBe(false);
  });
});

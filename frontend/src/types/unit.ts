import type { User } from "./auth";

export type UnitStatus = "ASSIGNED" | "UNASSIGNED";

/**
 * Which of a subject's parallel classes a unit offering is.
 *
 * A LOCKED pair, not free text. KOI runs ICT730 as LA1, LA2 and NCLA in
 * the same trimester; letting a coordinator type the class themselves
 * would produce "LA1", "la1", "LA 1" and "Class 1" inside a month, and
 * every count grouped by class would quietly under-report from then on.
 */
export type ClassType = "LA" | "NCLA";

export const CLASS_TYPES: { value: ClassType; label: string; numbered: boolean }[] = [
  { value: "LA", label: "LA — on-campus class", numbered: true },
  // NCLA takes no number: one non-campus class runs per offering, so a
  // counter that can never reach 2 is noise in every label that prints it.
  { value: "NCLA", label: "NCLA — non-campus class", numbered: false },
];

export const UNIT_LEVELS = [
  { value: "diploma", label: "Diploma" },
  { value: "bachelor", label: "Bachelor" },
  { value: "masters", label: "Masters" },
] as const;

export const TEACHING_PERIODS = ["T1", "T2", "T3"] as const;

export type UnitLevel = (typeof UNIT_LEVELS)[number]["value"];

export interface Unit {
  id: number;
  /** The SUBJECT, e.g. "ICT730". Shared by every class of it. */
  unit_code: string;
  /** "LA1" | "NCLA" | "" when this unit has no class split. */
  class_code: string;
  class_type: ClassType | null;
  class_number: number | null;
  /** What a human calls this offering: "ICT730LA1". Print THIS. */
  full_code: string;
  unit_name: string;
  start_date: string;
  year: number | null;
  teaching_period: string | null;
  level: UnitLevel | null;
  lecturer_id: number | null;
  status: UnitStatus;
  is_active: boolean;
  lecturer: User | null;
  enrolled_count: number;
}

// Body for POST /admin/units
export interface CreateUnitRequest {
  unit_code: string;
  unit_name: string;
  start_date: string;
  year?: number | null;
  teaching_period?: string | null;
  level?: string | null;
  lecturer_id?: number | null;
  /** Omit both for a unit with no class split. */
  class_type?: ClassType | null;
  class_number?: number | null;
}

// Body for PATCH /admin/units/{id}
export interface UpdateUnitRequest {
  unit_name?: string;
  start_date?: string;
  year?: number | null;
  teaching_period?: string | null;
  level?: string | null;
  /**
   * Send BOTH or neither. A class code is a label rather than a rule —
   * it changes nothing about how a student is scored — so it stays
   * editable after creation, the same principle the criteria shape lock
   * uses for a rename. The server refuses a number without its type.
   */
  class_type?: ClassType | null;
  class_number?: number | null;
}
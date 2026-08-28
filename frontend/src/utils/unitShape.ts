import type { AssessmentKind, ShapeLimits } from "../types/unitShape";

/**
 * The client-side mirror of `unit_composition.validate_composition`.
 *
 * IT IS A MIRROR, NOT THE RULE. The server re-checks everything and is
 * the only thing standing between a bad shape and the database — this
 * exists so a coordinator sees "a quiz cannot be worth more than 20%"
 * next to the field they typed it in, rather than as a toast after a
 * round trip.
 *
 * The numbers come from the server's `limits` on every call. Nothing in
 * this file knows that the cap is 20 or that there are three slots: a
 * second hard-coded copy of a rule is a second place for it to be
 * wrong, and it is the copy nobody updates.
 */

/** One assessment row as the form holds it: percentages are text. */
export interface ShapeRow {
  /** Stable across re-orders. NOT the database id — a new row has none. */
  key: string;
  /** The stored row this edits, or null for a newly added one. */
  id: number | null;
  name: string;
  kind: AssessmentKind;
  /** Raw input text. "" is a row the coordinator has not filled in yet. */
  percentage: string;
}

export interface ShapeValidation {
  /** Keyed by `ShapeRow.key`. */
  rowErrors: Record<string, string>;
  /** A rule about the shape as a whole, e.g. the 100% budget. */
  formError: string | null;
  valid: boolean;
}

/**
 * Two decimal places, applied BEFORE any comparison against 100.
 *
 * Three items of 33.33 sum to 99.99000000000001 in binary floating
 * point, and an unrounded comparison refuses a shape that is visibly
 * under 100%. The server rounds for the same reason; if only one side
 * did, the form and the API would disagree about the same numbers.
 */
export function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

/** A row's percentage as a number, or null when it is blank or not a number. */
export function parsePercentage(raw: string): number | null {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}

/**
 * Assessments plus the fixed tutorial share.
 *
 * Attendance and Moodle are excluded on purpose: they are seeded, are
 * not marks, and sit outside the 100% budget entirely. The risk blend
 * weighs more than 100% as a result, which is correct — the rule engine
 * divides by the total weight it used, so weights are relative.
 */
export function shapeTotal(
  rows: ShapeRow[],
  tutorialsEnabled: boolean,
  limits: ShapeLimits
): number {
  const assessments = rows.reduce(
    (sum, row) => sum + (parsePercentage(row.percentage) ?? 0),
    0
  );
  return round2(assessments + (tutorialsEnabled ? limits.tutorial_percentage : 0));
}

export function validateShape(
  rows: ShapeRow[],
  tutorialsEnabled: boolean,
  limits: ShapeLimits
): ShapeValidation {
  const rowErrors: Record<string, string> = {};
  let formError: string | null = null;

  if (rows.length > limits.max_assessments) {
    formError = `A unit can have at most ${limits.max_assessments} assessments.`;
  }

  rows.forEach((row, index) => {
    const label = row.name.trim() || `Assessment ${index + 1}`;

    if (!row.name.trim()) {
      rowErrors[row.key] = `Assessment ${index + 1} needs a name.`;
      return;
    }

    const percentage = parsePercentage(row.percentage);
    if (percentage === null) {
      rowErrors[row.key] = `'${label}' needs a percentage.`;
      return;
    }
    if (percentage <= 0) {
      rowErrors[row.key] = `'${label}' must be worth more than 0% of the unit.`;
      return;
    }
    if (percentage > limits.max_total_percentage) {
      rowErrors[row.key] =
        `'${label}' cannot be worth more than ` +
        `${limits.max_total_percentage}% of the unit.`;
      return;
    }
    // The cap is on quizzes only. An assignment worth 60% is fine, and
    // the message says so rather than leaving the coordinator to guess
    // that the way out is changing the kind.
    if (row.kind === "quiz" && percentage > limits.quiz_max_percentage) {
      rowErrors[row.key] =
        `A quiz cannot be worth more than ${limits.quiz_max_percentage}% ` +
        `of the unit. Change it to an assignment if it is worth more.`;
    }
  });

  // Over 100% is refused; under 100% is accepted in silence. A unit
  // part-way through configuration is under 100% by definition, and a
  // unit can legitimately carry a component this system does not model.
  const total = shapeTotal(rows, tutorialsEnabled, limits);
  if (!formError && total > limits.max_total_percentage) {
    const tutorialNote = tutorialsEnabled
      ? ` (including ${limits.tutorial_percentage}% for weekly tutorials)`
      : "";
    formError =
      `The unit adds up to ${total}%${tutorialNote}, which is more than ` +
      `${limits.max_total_percentage}%. Reduce a percentage or remove an item.`;
  }

  return {
    rowErrors,
    formError,
    valid: formError === null && Object.keys(rowErrors).length === 0,
  };
}

/**
 * True when the shape — as opposed to the labels — differs from what
 * was loaded. Mirrors `unit_composition.classify_shape_change`.
 *
 * The form needs this for one reason: a locked unit still accepts a
 * rename and still accepts a save that changes nothing, so disabling
 * Save while locked would block two operations the server allows. Names
 * are therefore compared separately from everything else, exactly as
 * they are on the server.
 */
export function isShapeChanged(
  rows: ShapeRow[],
  tutorialsEnabled: boolean,
  originalRows: ShapeRow[],
  originalTutorials: boolean
): boolean {
  if (tutorialsEnabled !== originalTutorials) return true;
  if (rows.length !== originalRows.length) return true;

  return rows.some((row, index) => {
    const original = originalRows[index];
    return (
      row.kind !== original.kind ||
      round2(parsePercentage(row.percentage) ?? 0) !==
        round2(parsePercentage(original.percentage) ?? 0)
    );
  });
}
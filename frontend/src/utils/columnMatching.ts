/**
 * Heuristics that pre-fill the import wizard's column mapping.
 *
 * These are GUESSES, always overridable, and never silently applied to
 * anything ambiguous. The purpose is to spare a lecturer twenty
 * dropdown selections on a file whose columns are named exactly what
 * you would expect — not to be clever. When a guess is wrong the cost
 * is one correction; when a guess is missing the cost is one selection.
 * Both are cheap, which is why the patterns below stay conservative.
 */

import type { CriteriaCategory } from "../types/criteria";

/**
 * First column whose name matches any of the patterns, in pattern
 * order — so the most specific pattern should come first.
 */
function firstMatch(columns: string[], patterns: RegExp[]): string {
  for (const pattern of patterns) {
    const hit = columns.find((column) => pattern.test(column.trim()));
    if (hit) return hit;
  }
  return "";
}

/**
 * Guesses the six identity columns.
 *
 * Student number is tried before a bare "id" because a file often has
 * both a row id and a student id, and picking the row id would break
 * every enrolment — matching on the specific name first avoids that.
 */
export function guessIdentityColumns(columns: string[]) {
  return {
    student_number_col: firstMatch(columns, [
      /^student[\s_-]*(number|no|id)$/i,
      /student[\s_-]*(number|no|id)/i,
      /^(sid|s_id|studentid)$/i,
      /^id$/i,
    ]),
    name_col: firstMatch(columns, [
      /^(student[\s_-]*)?(full[\s_-]*)?name$/i,
      /name/i,
    ]),
    email_col: firstMatch(columns, [/e[\s_-]*mail/i]),
    program_col: firstMatch(columns, [/^(program|programme|course|degree)$/i, /program/i]),
    gender_col: firstMatch(columns, [/^(gender|sex)$/i]),
    age_col: firstMatch(columns, [/^age$/i]),
  };
}

/**
 * Pulls the week number out of a column name, or null if there isn't
 * one. Handles "W1", "Week 1", "week_3", "Tut Week 5", "Attendance W2".
 *
 * Anchored to a word boundary so "Week 12" does not read as week 1, and
 * so a column called "Assignment 1" is not mistaken for week 1 — the
 * caller only passes columns it already believes are weekly.
 */
export function extractWeekNumber(column: string): number | null {
  const match = column.trim().match(/\bw(?:ee)?k?\s*[_-]?\s*(\d{1,2})\b/i);
  if (!match) return null;

  const week = Number(match[1]);
  return Number.isFinite(week) ? week : null;
}

/**
 * Guesses the ordered weekly columns for attendance or tutorials.
 *
 * ORDER IS THE WHOLE POINT. The backend reads the returned list
 * positionally — index 0 is the first week of the window — and computes
 * the early-vs-late trend from those positions. So this returns columns
 * sorted by their detected week number, not by their order in the file.
 *
 * Returns an empty array unless EVERY week in the range was found.
 * A partial guess is worse than none: it would look mapped while
 * silently costing the student their trend value, which needs exactly
 * 7 attendance values or exactly 6 tutorial values to compute at all.
 *
 * @param startWeek attendance starts at 1; tutorials start at 2
 * @param count     attendance needs 7; tutorials need 6
 */
export function guessWeeklyColumns(
  columns: string[],
  category: CriteriaCategory,
  startWeek: number,
  count: number,
): string[] {
  // Tutorial columns must actually mention tutorials, otherwise a file
  // with a single W1..W7 attendance block would map those same columns
  // to tutorials as well.
  const candidates =
    category === "weekly_tut"
      ? columns.filter((c) => /tut/i.test(c))
      : columns.filter((c) => !/tut/i.test(c));

  const byWeek = new Map<number, string>();
  for (const column of candidates) {
    const week = extractWeekNumber(column);
    // First column wins for a given week — a duplicate is ambiguous and
    // guessing between them would be arbitrary.
    if (week !== null && !byWeek.has(week)) byWeek.set(week, column);
  }

  const ordered: string[] = [];
  for (let week = startWeek; week < startWeek + count; week += 1) {
    const column = byWeek.get(week);
    if (!column) return []; // Incomplete — see docstring.
    ordered.push(column);
  }

  return ordered;
}

/**
 * Guesses the single column for an assessment or Moodle criterion by
 * matching the criterion's own name against the column names.
 *
 * Exact match first, then a loose contains-match in either direction so
 * "Assignment 1" finds a column called "Assign1" and vice versa.
 * Punctuation and spacing are stripped from both sides before
 * comparing, since spreadsheets are inconsistent about them.
 */
export function guessColumnForCriterion(
  columns: string[],
  criterionName: string,
  category?: CriteriaCategory | null,
): string {
  const normalise = (value: string) => value.toLowerCase().replace(/[\s_-]+/g, "");
  const target = normalise(criterionName);

  if (target) {
    const exact = columns.find((column) => normalise(column) === target);
    if (exact) return exact;

    const partial = columns.find((column) => {
      const normalised = normalise(column);
      return normalised.includes(target) || target.includes(normalised);
    });
    if (partial) return partial;
  }

  // Category fallback. A criterion's NAME and its column's name often
  // describe the same thing differently - the seeded criterion is
  // called "Moodle Activity" while a typical export column is "Moodle
  // Logins", and neither string contains the other. Matching on the
  // category's own keyword catches that without loosening the name
  // match into something that would produce wrong guesses elsewhere.
  //
  // Only applied to single-column categories. Weekly ones are handled
  // by guessWeeklyColumns, which has ordering rules this cannot honour.
  if (category === "moodle") {
    const hit = columns.find((column) => /moodle|lms|login/i.test(column));
    if (hit) return hit;
  }

  return "";
}

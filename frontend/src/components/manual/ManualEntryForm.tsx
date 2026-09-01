import { useMemo, useState } from "react";
import { CircleAlert, Loader2, UserPlus } from "lucide-react";
import type { Criterion } from "../../types/criteria";
import { CATEGORY_COLUMN_COUNT, FIXED_CATEGORIES } from "../../types/criteria";
import type { ManualEntryCreate } from "../../types/ingestion";
import { ATTENDANCE_ABSENT } from "../../types/ingestion";
import { CATEGORY_LABELS } from "../../utils/dashboardAggregations";
import { useManualEntry } from "../../hooks/useIngestion";
import EngineVerdictPanel from "./EngineVerdictPanel";
import { WeeklyAttendanceInput, WeeklyTutorialInput } from "./WeeklyInputs";

interface ManualEntryFormProps {
  unitId: number;
  unitCode: string;
  criteria: Criterion[];
}

interface StudentFields {
  student_number: string;
  name: string;
  email: string;
  program: string;
  gender: string;
  age: string;
}

const EMPTY_STUDENT: StudentFields = {
  student_number: "",
  name: "",
  email: "",
  program: "",
  gender: "",
  age: "",
};

/**
 * Add one student and their scores by hand.
 *
 * For a late enrolment, a correction, or simply proving the pipeline
 * works end to end — this is the fastest path from typing numbers to
 * seeing both engines' verdicts.
 *
 * Goes through POST /units/{id}/ingest/manual, which uses the SAME
 * ingestion service as bulk upload. A student added here is
 * indistinguishable downstream from one that arrived in a spreadsheet:
 * same AssessmentEvent rows, same aggregation, same analysis.
 *
 * SCORES ARE ENTERED RAW, NOT AS PERCENTAGES
 * ------------------------------------------
 * An assignment marked out of 20 takes a value from 0 to 20 here, and
 * the backend validates against that criterion's max_score. Asking for
 * a percentage would push the conversion onto the lecturer, which is
 * exactly the class of mistake the max_score scale bug came from.
 */
export default function ManualEntryForm({
  unitId,
  unitCode,
  criteria,
}: ManualEntryFormProps) {
  const [student, setStudent] = useState<StudentFields>(EMPTY_STUDENT);
  const [scores, setScores] = useState<Record<number, string>>({});
  const [weekly, setWeekly] = useState<Record<number, string[]>>(() =>
    buildEmptyWeekly(criteria),
  );

  /**
   * Which weekly criteria the lecturer actually has data for.
   *
   * THIS EXISTS TO STOP THE FORM INVENTING FAILURE.
   *
   * A weekly input is never blank — attendance is present-or-absent and
   * a tutorial is always one of three states — so a freshly rendered
   * form already reads as "absent every week, submitted nothing". If
   * that were sent unconditionally, a lecturer who only wanted to
   * ENROL a student would silently record them at 0% attendance and 0%
   * tutorial completion, and both engines would correctly score that
   * fabricated data as high risk.
   *
   * Defaulting to unchecked means an unmarked student arrives as
   * genuinely unmarked: no AssessmentEvent, so the engines flag them
   * `is_incomplete` rather than failing them. Single-value criteria
   * need no equivalent, because an empty text field is already an
   * unambiguous "no data" and is skipped on submit.
   */
  const [includeWeekly, setIncludeWeekly] = useState<Record<number, boolean>>({});

  const mutation = useManualEntry(unitId);

  const active = useMemo(() => criteria.filter((c) => c.enabled), [criteria]);

  /**
   * Blocking problems, as sentences.
   *
   * Only student number is truly required by the backend, but a NEW
   * student also needs a name — Student.name is NOT NULL at the database
   * level, so omitting it fails the insert for anyone not already on
   * file. Requiring it up front turns a confusing 400 into a form hint.
   */
  const problems = useMemo(() => {
    const found: string[] = [];

    if (!student.student_number.trim()) found.push("Student number is required.");
    if (!student.name.trim()) found.push("Full name is required for a new student.");

    if (student.age.trim()) {
      const age = Number(student.age);
      if (!Number.isFinite(age) || age <= 0) found.push("Age must be a number.");

      const hasSingleValue = active.some((criterion) => {
      const raw = scores[criterion.id];
      return raw !== undefined && raw.trim() !== "";
      });

      const hasWeeklyValue = active.some(
        (criterion) => Boolean(includeWeekly[criterion.id]),
      );

      if (!hasSingleValue && !hasWeeklyValue) {
        found.push("At least one academic criterion must contain data.");
      }
    }

    for (const criterion of active) {
      const raw = scores[criterion.id];
      if (raw === undefined || raw === "") continue;

      const value = Number(raw);
      if (!Number.isFinite(value)) {
        found.push(`${criterion.name}: not a number.`);
      } else if (value < 0 || value > criterion.max_score) {
        // Mirrors validate_score() on the backend, so the lecturer sees
        // the problem before the round trip rather than after it.
        found.push(
          `${criterion.name}: must be between 0 and ${criterion.max_score}.`,
        );
      }
    }

    return found;
  }, [student, scores, active, includeWeekly]);

  function reset() {
    setStudent(EMPTY_STUDENT);
    setScores({});
    setWeekly(buildEmptyWeekly(criteria));
    setIncludeWeekly({});
    mutation.reset();
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (problems.length > 0) return;

    const numericScores: Record<number, number> = {};
    for (const [criteriaId, raw] of Object.entries(scores)) {
      if (raw === "") continue;
      const value = Number(raw);
      if (Number.isFinite(value)) numericScores[Number(criteriaId)] = value;
    }

    const payload: ManualEntryCreate = {
      student_number: student.student_number.trim(),
      name: student.name.trim() || null,
      // Empty string means "not provided"; the backend expects null so
      // it can distinguish absent from deliberately blank.
      email: student.email.trim() || null,
      program: student.program.trim() || null,
      gender: student.gender || null,
      age: student.age.trim() ? Number(student.age) : null,
      scores: numericScores,
      // Only the weekly criteria the lecturer explicitly opted into.
      // Omitting one means no AssessmentEvent is created for it, so the
      // engines see "no data yet" instead of a fabricated zero.
      weekly_scores: Object.fromEntries(
        Object.entries(weekly).filter(([criteriaId]) => includeWeekly[Number(criteriaId)]),
      ),
    };

    mutation.mutate(payload);
  }

  if (mutation.data) {
    return (
      <EngineVerdictPanel
        result={mutation.data}
        studentName={student.name}
        onAddAnother={reset}
      />
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <section className="rounded-lg border border-stone-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-stone-900">Student</h3>
        <p className="mt-0.5 text-xs leading-relaxed text-stone-500">
          Matched by student number. If they already exist, they're enrolled in{" "}
          {unitCode} without overwriting their existing details.
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field
            label="Student number"
            required
            value={student.student_number}
            onChange={(value) => setStudent({ ...student, student_number: value })}
          />
          <Field
            label="Full name"
            required
            value={student.name}
            onChange={(value) => setStudent({ ...student, name: value })}
          />
          <Field
            label="Email"
            type="email"
            value={student.email}
            onChange={(value) => setStudent({ ...student, email: value })}
          />
          <Field
            label="Program"
            value={student.program}
            onChange={(value) => setStudent({ ...student, program: value })}
          />

          <label className="block">
            <span className="block text-xs font-medium text-stone-700">Gender</span>
            <span className="mt-0.5 block text-[11px] text-stone-400">
              Used by the ML model as a feature
            </span>
            <select
              value={student.gender}
              onChange={(event) =>
                setStudent({ ...student, gender: event.target.value })
              }
              className="mt-1.5 w-full rounded-md border border-stone-200 bg-white px-2.5 py-1.5 text-sm text-stone-900 outline-none transition focus:border-stone-400"
            >
              <option value="">Not provided</option>
              <option value="M">M</option>
              <option value="F">F</option>
            </select>
          </label>

          <Field
            label="Age"
            type="number"
            hint="Used by the ML model as a feature"
            value={student.age}
            onChange={(value) => setStudent({ ...student, age: value })}
          />
        </div>
      </section>

      {active.map((criterion) => {
        const category = criterion.category;
        const columnCount = category ? CATEGORY_COLUMN_COUNT[category] : null;
        const isFixed = category ? FIXED_CATEGORIES.includes(category) : false;

        return (
          <section
            key={criterion.id}
            className="rounded-lg border border-stone-200 bg-white p-5"
          >
            <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-stone-900">
                  {criterion.name}
                </h3>
                <p className="mt-0.5 text-xs text-stone-500">
                  {category ? CATEGORY_LABELS[category] ?? category : "Uncategorised"}
                  {columnCount === null &&
                    ` · enter the raw mark out of ${criterion.max_score}`}
                  {isFixed && " · fixed criterion"}
                </p>
              </div>

              {/* Weekly criteria need an explicit opt-in, because their
                  inputs are never blank — see the includeWeekly note. */}
              {columnCount !== null && (
                <label className="flex cursor-pointer items-center gap-2 text-xs text-stone-600">
                  <input
                    type="checkbox"
                    checked={Boolean(includeWeekly[criterion.id])}
                    onChange={(event) =>
                      setIncludeWeekly((current) => ({
                        ...current,
                        [criterion.id]: event.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-stone-300 accent-stone-900"
                  />
                  I have {criterion.name.toLowerCase()} data
                </label>
              )}
            </header>

            {columnCount !== null && !includeWeekly[criterion.id] && (
              <p className="rounded-md bg-stone-50 px-3 py-2.5 text-[11px] leading-relaxed text-stone-500">
                Not recorded. The student will be scored without this, and flagged as
                having incomplete data — which is different from, and better than,
                recording them as having missed everything.
              </p>
            )}

            {category === "attendance" && includeWeekly[criterion.id] && (
              <WeeklyAttendanceInput
                values={weekly[criterion.id] ?? []}
                onChange={(index, value) =>
                  setWeekly((current) => replaceAt(current, criterion.id, index, value))
                }
              />
            )}

            {category === "weekly_tut" && includeWeekly[criterion.id] && (
              <WeeklyTutorialInput
                values={weekly[criterion.id] ?? []}
                onChange={(index, value) =>
                  setWeekly((current) => replaceAt(current, criterion.id, index, value))
                }
              />
            )}

            {columnCount === null && (
              <div className="max-w-xs">
                <Field
                  label={
                    category === "moodle"
                      ? "Login count"
                      : `Mark (0–${criterion.max_score})`
                  }
                  type="number"
                  hint={
                    category === "moodle"
                      ? "A raw count of logins, not a percentage"
                      : `Threshold for this criterion is ${criterion.threshold}%`
                  }
                  value={scores[criterion.id] ?? ""}
                  onChange={(value) =>
                    setScores((current) => ({ ...current, [criterion.id]: value }))
                  }
                />
              </div>
            )}
          </section>
        );
      })}

      {problems.length > 0 && (
        <div className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <CircleAlert
            className="mt-0.5 h-4 w-4 shrink-0 text-red-600"
            aria-hidden="true"
          />
          <div className="text-xs leading-relaxed text-red-900">
            <p className="font-medium">Fix these before saving</p>
            <ul className="mt-1.5 space-y-1">
              {problems.map((problem) => (
                <li key={problem}>· {problem}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 border-t border-stone-200 pt-4">
        <p className="text-[11px] leading-relaxed text-stone-400">
          Risk analysis runs immediately on save.
        </p>

        <button
          type="submit"
          disabled={problems.length > 0 || mutation.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800 disabled:opacity-40"
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Saving and analysing…
            </>
          ) : (
            <>
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Add to {unitCode}
            </>
          )}
        </button>
      </div>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

/**
 * Pre-fills every weekly criterion with a full-length array.
 *
 * Attendance defaults to absent and tutorials to not_submitted, which
 * matches the backend's own rule that an unmarked cell counts as zero
 * rather than as missing. Starting from a complete array also means the
 * wrong-length problem the CSV wizard has to guard against simply
 * cannot occur here.
 */
function buildEmptyWeekly(criteria: Criterion[]): Record<number, string[]> {
  const initial: Record<number, string[]> = {};

  for (const criterion of criteria) {
    if (!criterion.enabled || !criterion.category) continue;
    const count = CATEGORY_COLUMN_COUNT[criterion.category];
    if (count === null) continue;

    initial[criterion.id] = Array(count).fill(
      criterion.category === "attendance" ? ATTENDANCE_ABSENT : "not_submitted",
    );
  }

  return initial;
}

/** Immutably replaces one week's value inside one criterion's array. */
function replaceAt(
  current: Record<number, string[]>,
  criteriaId: number,
  index: number,
  value: string,
): Record<number, string[]> {
  const existing = current[criteriaId] ?? [];
  const next = [...existing];
  next[index] = value;
  return { ...current, [criteriaId]: next };
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  type?: string;
  hint?: string;
}

/** A labelled text input, matching ColumnSelect's shape and spacing. */
function Field({
  label,
  value,
  onChange,
  required = false,
  type = "text",
  hint,
}: FieldProps) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-stone-700">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </span>
      {hint && <span className="mt-0.5 block text-[11px] text-stone-400">{hint}</span>}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1.5 w-full rounded-md border border-stone-200 bg-white px-2.5 py-1.5 text-sm text-stone-900 outline-none transition focus:border-stone-400"
      />
    </label>
  );
}
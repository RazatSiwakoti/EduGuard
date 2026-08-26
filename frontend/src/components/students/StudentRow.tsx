import { CircleAlert } from "lucide-react";
import type { DashboardStudent, DashboardUnit } from "../../types/dashboard";
import { getBucket } from "../../utils/dashboardAggregations";
import {
  assessmentProgressOf,
  attendanceOf,
  tutorialOf,
} from "../../utils/studentsTable";
import BucketBadge from "../dashboard/BucketBadge";
import { BUCKET_STYLES } from "../dashboard/chartTheme";
import AssessmentCell from "./AssessmentCell";
import MetricCell from "./MetricCell";
import TrendCell from "./TrendCell";

interface StudentRowProps {
  student: DashboardStudent;
  /** This student's unit — supplies the assessment denominator. */
  unit: DashboardUnit | undefined;
  /**
   * Opens the student card. Optional so the table can still be rendered
   * inert (tests, or a future read-only view) without a dead click.
   */
  onSelect?: (student: DashboardStudent) => void;
  /** Whether the Weekly Tut column is being rendered at all. */
  showTutorial: boolean;
}

/** "Fatima Al-Hassan" → "FA". Hyphenated and single-word names both work. */
function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * One enrolment.
 *
 * ONE ROW IS A STUDENT IN A UNIT, not a student. Risk is computed per
 * unit, so the same person legitimately appears twice with different
 * verdicts — high risk in one unit, safe in another. The React key must
 * therefore be the (student_id, unit_id) pair, and the unit code sits
 * under the name so two rows for the same person are distinguishable.
 */
export default function StudentRow({
  student,
  unit,
  onSelect,
  showTutorial,
}: StudentRowProps) {
  const bucket = getBucket(student);
  const attendance = attendanceOf(student);
  const tutorial = tutorialOf(student);
  const assessments = assessmentProgressOf(student, unit);

  const interactive = onSelect !== undefined;

  return (
    <tr className="transition hover:bg-stone-50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <span
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold ring-1 ring-inset ${BUCKET_STYLES[bucket].pill}`}
            aria-hidden="true"
          >
            {initialsOf(student.name)}
          </span>

          {/* THE TRIGGER IS THE NAME, NOT THE ROW. A whole-row click
              makes selecting a student number impossible and leaves no
              obvious target; scoping it to the name also means a real
              <button> can be used. Wrapping a <tr> in a <button> is
              invalid HTML — browsers restructure the table around it —
              which is why the row-level version was dropped. */}
          <div className="min-w-0">
            {interactive ? (
              <button
                type="button"
                onClick={() => onSelect(student)}
                className="block max-w-full truncate text-left text-sm font-semibold text-stone-900 underline-offset-2 transition hover:text-blue-700 hover:underline focus:outline-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-stone-400"
              >
                {student.name}
                <span className="sr-only"> — open details</span>
              </button>
            ) : (
              <p className="truncate text-sm font-semibold text-stone-900">
                {student.name}
              </p>
            )}

            <p className="truncate text-xs text-stone-500">
              <span className="tabular-nums">{student.student_number}</span>
              <span className="mx-1 text-stone-300">·</span>
              {student.unit_code}
            </p>
          </div>

          {/* An incomplete score is shown, not hidden — but flagged.
              Suppressing it would mean the lecturer never learns the
              underlying data was patchy. */}
          {student.is_incomplete && (
            <span
              title="Scored with incomplete data — treat this verdict with caution"
              className="shrink-0 text-amber-500"
            >
              <CircleAlert className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">Incomplete data</span>
            </span>
          )}
        </div>
      </td>

      <td className="px-4 py-3">
        <MetricCell value={attendance} label="Attendance" />
      </td>

      <td className="px-4 py-3">
        {/* hasAnyData decides whether "0 marked" reads as a missed
            assessment or as an absence of data — see AssessmentCell. */}
        <AssessmentCell progress={assessments} hasAnyData={student.criteria.length > 0} />
      </td>

      {/* Rendered only when the column exists in the header, or the
          row's cells would shift one column left of their headings. */}
      {showTutorial && (
        <td className="px-4 py-3">
          <MetricCell value={tutorial} label="Weekly tutorials" hint="W2–W7 completion" />
        </td>
      )}

      <td className="px-4 py-3">
        <BucketBadge bucket={bucket} />
      </td>

      <td className="px-4 py-3">
        <TrendCell
          attendanceTrend={attendance?.trendValue ?? null}
          tutorialTrend={tutorial?.trendValue ?? null}
        />
      </td>
    </tr>
  );
}
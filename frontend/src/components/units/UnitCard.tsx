import { Link } from "react-router-dom";
import { ArrowRight, GraduationCap, Users } from "lucide-react";
import type { DashboardUnit } from "../../types/dashboard";

interface UnitCardProps {
  unit: DashboardUnit;
}

/**
 * One unit in the units list, linking into its workspace.
 *
 * The whole card is the link rather than a small "Open" button in the
 * corner — a card with one destination should have one large target,
 * and hunting for a 60px button inside a 300px card is needless work.
 *
 * Enrolment count is the headline figure because it answers the
 * question a lecturer actually opens this page with: has my cohort been
 * imported yet, or is this unit still empty?
 */
export default function UnitCard({ unit }: UnitCardProps) {
  // Both are nullable in the database - older units predate these
  // fields - so the offering line is assembled from whatever exists
  // rather than printing "null S1" or a stray separator.
  const offering = [unit.teaching_period, unit.year].filter(Boolean).join(" ");

  return (
    <Link
      to={`/units/${unit.id}`}
      className="group flex flex-col rounded-lg border border-stone-200 bg-white p-5 transition hover:border-stone-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-stone-900">{unit.unit_code}</p>
          <p className="mt-0.5 truncate text-sm text-stone-600">{unit.unit_name}</p>
        </div>

        <ArrowRight
          className="mt-0.5 h-4 w-4 shrink-0 text-stone-300 transition group-hover:translate-x-0.5 group-hover:text-stone-500"
          aria-hidden="true"
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-stone-500">
        <span className="inline-flex items-center gap-1.5">
          <Users className="h-3.5 w-3.5" aria-hidden="true" />
          {unit.enrolled_count} student{unit.enrolled_count === 1 ? "" : "s"}
        </span>

        {offering && <span>{offering}</span>}

        {unit.level && (
          <span className="inline-flex items-center gap-1.5 capitalize">
            <GraduationCap className="h-3.5 w-3.5" aria-hidden="true" />
            {unit.level}
          </span>
        )}
      </div>

      {/* An empty unit is the one state worth calling out here: it is
          the difference between "nothing to see" and "you have not
          imported your cohort yet", and only one of those is actionable. */}
      {unit.enrolled_count === 0 && (
        <p className="mt-3 rounded border border-dashed border-stone-200 px-3 py-2 text-xs text-stone-400">
          No students yet — import your cohort to start scoring risk.
        </p>
      )}
    </Link>
  );
}
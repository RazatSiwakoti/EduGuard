import { Link } from "react-router-dom";
import { ArrowRight, CalendarDays, GraduationCap, Users } from "lucide-react";
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
 *
 * THE CLASS IS SEPARATED FROM THE SUBJECT, VISUALLY.
 * `full_code` is one string — "ICT730LA1" — but printing it as one word
 * makes two classes of a subject look like two unrelated units at a
 * glance. The subject is set large and the class is a chip beside it,
 * so a lecturer holding LA1 and LA2 sees one subject twice rather than
 * two codes they have to read character by character to tell apart.
 */
export default function UnitCard({ unit }: UnitCardProps) {
  // Both are nullable in the database - older units predate these
  // fields - so the offering line is assembled from whatever exists
  // rather than printing "null S1" or a stray separator.
  const offering = [unit.teaching_period, unit.year].filter(Boolean).join(" ");
  const isEmpty = unit.enrolled_count === 0;

  return (
    <Link
      to={`/units/${unit.id}`}
      // The hover lift is 2px and the shadow does the rest. Anything
      // larger reads as the card being dragged rather than offered.
      className="group flex flex-col rounded-card border border-hairline bg-white p-5 shadow-card transition duration-200 ease-out hover:-translate-y-0.5 hover:shadow-card-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <p className="font-mono text-base font-bold tracking-tight text-brand">
              {unit.unit_code}
            </p>
            {/* Rendered only when there IS a class. A chip reading
                "no class" on every legacy unit would repeat the same
                words down the whole grid and stop being read. */}
            {unit.class_code && (
              <span className="rounded-full bg-brand-wash px-2 py-0.5 font-mono text-[11px] font-bold tracking-wide text-brand">
                {unit.class_code}
              </span>
            )}
          </div>
          <p className="mt-1 truncate text-sm font-medium text-stone-700">
            {unit.unit_name}
          </p>
        </div>

        <ArrowRight
          className="mt-1 h-4 w-4 shrink-0 text-stone-300 transition group-hover:translate-x-0.5 group-hover:text-brand"
          aria-hidden="true"
        />
      </div>

      {/* The detail strip: everything a lecturer would otherwise have to
          open the unit to find. Each fact gets an icon AND a word —
          colour and shape alone would leave a screen reader with a row
          of numbers and no idea what any of them counts. */}
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-stone-100 pt-4">
        <div>
          <dt className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-stone-400">
            <Users className="h-3 w-3" aria-hidden="true" />
            Enrolled
          </dt>
          <dd className="mt-0.5 font-mono text-lg font-semibold tabular-nums text-stone-900">
            {unit.enrolled_count}
          </dd>
        </div>

        <div>
          <dt className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-stone-400">
            <CalendarDays className="h-3 w-3" aria-hidden="true" />
            Offering
          </dt>
          <dd className="mt-0.5 truncate text-sm text-stone-700">
            {offering || <span className="text-stone-400">not recorded</span>}
          </dd>
        </div>

        {unit.level && (
          <div>
            <dt className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-stone-400">
              <GraduationCap className="h-3 w-3" aria-hidden="true" />
              Level
            </dt>
            <dd className="mt-0.5 text-sm capitalize text-stone-700">{unit.level}</dd>
          </div>
        )}

        {/* DELIBERATELY NOT a "Class: ICT730LA1" row. The header already
            reads ICT730 + LA1, so a full-code cell would print the
            subject a third time on one card and earn none of the space
            it takes. Caught by rendering the grid and counting how many
            times "ICT730" appeared. */}
      </dl>

      {/* An empty unit is the one state worth calling out here: it is
          the difference between "nothing to see" and "you have not
          imported your cohort yet", and only one of those is actionable. */}
      {isEmpty && (
        <p className="mt-4 rounded-lg border border-dashed border-amber-200 bg-amber-50/60 px-3 py-2 text-xs text-amber-800">
          No students yet — import your cohort to start scoring risk.
        </p>
      )}
    </Link>
  );
}
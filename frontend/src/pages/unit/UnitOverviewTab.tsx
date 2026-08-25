import { Link, useOutletContext } from "react-router-dom";
import { CircleAlert, Lock, Plus, Upload, UserPlus } from "lucide-react";
import type { UnitTabContext } from "../UnitWorkspace";
import { useUnitCriteria } from "../../hooks/useLecturerUnits";
import { CATEGORY_COLUMN_COUNT, FIXED_CATEGORIES } from "../../types/criteria";
import type { CriteriaCategory } from "../../types/criteria";
import { CATEGORY_LABELS } from "../../utils/dashboardAggregations";

/**
 * What this unit is marked on, and what to do next.
 *
 * The criteria list is the important half. Criteria are what CSV
 * columns get mapped TO during import, so a unit with only its two
 * seeded criteria literally cannot accept assignment or tutorial data
 * yet — there is nothing for those columns to map onto. Surfacing that
 * here means a lecturer finds out before they open the wizard, not
 * halfway through it.
 */
export default function UnitOverviewTab() {
  const { unit } = useOutletContext<UnitTabContext>();
  const { data: criteria, isLoading, isError } = useUnitCriteria(unit.id);

  const list = criteria ?? [];

  // Attendance and Moodle are seeded automatically by
  // seed_default_criteria(). Anything beyond those two had to be
  // created by a lecturer, which is exactly what "is this unit
  // configured yet" means.
  const custom = list.filter(
    (c) => !c.category || !FIXED_CATEGORIES.includes(c.category),
  );

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-stone-200 bg-white p-5">
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-stone-900">
              Assessment criteria
            </h2>
            <p className="mt-0.5 text-xs leading-relaxed text-stone-500">
              What this unit is scored on. Attendance and Moodle are fixed for every
              unit; anything else is yours to define.
            </p>
          </div>
        </header>

        {isLoading && (
          <div className="animate-pulse space-y-2">
            {[0, 1, 2].map((index) => (
              <div key={index} className="h-12 rounded bg-stone-100" />
            ))}
          </div>
        )}

        {isError && (
          <p className="py-4 text-center text-sm text-stone-500">
            Couldn't load this unit's criteria.
          </p>
        )}

        {!isLoading && !isError && (
          <>
            <ul className="divide-y divide-stone-100">
              {list.map((criterion) => {
                const category = criterion.category as CriteriaCategory | null;
                const columns = category ? CATEGORY_COLUMN_COUNT[category] : null;
                const isFixed = category ? FIXED_CATEGORIES.includes(category) : false;

                return (
                  <li
                    key={criterion.id}
                    className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="flex items-center gap-2 text-sm font-medium text-stone-900">
                        {criterion.name}
                        {isFixed && (
                          <span
                            title="Fixed for every unit — weight and threshold come from the risk engine's constants"
                            className="inline-flex items-center gap-1 rounded bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-500"
                          >
                            <Lock className="h-2.5 w-2.5" aria-hidden="true" />
                            Fixed
                          </span>
                        )}
                        {!criterion.enabled && (
                          <span className="rounded bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-400">
                            Disabled
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 text-xs text-stone-500">
                        {category ? CATEGORY_LABELS[category] ?? category : "Uncategorised"}
                        {/* Column count is the single most useful fact
                            here — it is what the lecturer must satisfy
                            in their spreadsheet, and getting it wrong
                            silently drops the trend value. */}
                        {columns
                          ? ` · needs exactly ${columns} columns`
                          : " · single column"}
                      </p>
                    </div>

                    <div className="flex shrink-0 gap-4 text-xs tabular-nums text-stone-500">
                      <span>Weight {criterion.weight}</span>
                      <span>Threshold {criterion.threshold}</span>
                    </div>
                  </li>
                );
              })}
            </ul>

            {/* The blocking condition for import, stated plainly. */}
            {custom.length === 0 && (
              <div className="mt-4 flex gap-3 rounded-md border border-dashed border-amber-300 bg-amber-50 p-4">
                <CircleAlert
                  className="mt-0.5 h-4 w-4 shrink-0 text-amber-600"
                  aria-hidden="true"
                />
                <div className="text-xs leading-relaxed text-amber-900">
                  <p className="font-medium">
                    No assignment or tutorial criteria defined yet.
                  </p>
                  <p className="mt-1">
                    This unit can currently only accept attendance and Moodle data. You
                    can create the missing criteria from your spreadsheet's columns
                    during import — the wizard offers it at the mapping step.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ActionCard
          to={`/units/${unit.id}/import`}
          icon={Upload}
          title="Import cohort data"
          description="Upload a CSV or Excel file and map its columns to this unit's criteria."
        />
        <ActionCard
          to={`/units/${unit.id}/add-student`}
          icon={UserPlus}
          title="Add a single student"
          description="Enter one student and their scores by hand, without a file."
        />
      </section>
    </div>
  );
}

interface ActionCardProps {
  to: string;
  icon: typeof Plus;
  title: string;
  description: string;
}

/** A next step, presented as a large target rather than a small button. */
function ActionCard({ to, icon: Icon, title, description }: ActionCardProps) {
  return (
    <Link
      to={to}
      className="flex gap-3 rounded-lg border border-stone-200 bg-white p-5 transition hover:border-stone-300 hover:shadow-sm"
    >
      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-stone-50 text-stone-500">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-stone-900">{title}</span>
        <span className="mt-1 block text-xs leading-relaxed text-stone-500">
          {description}
        </span>
      </span>
    </Link>
  );
}
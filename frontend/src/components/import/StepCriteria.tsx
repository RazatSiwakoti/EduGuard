import { CircleAlert, Lock } from "lucide-react";
import type { Criterion, CriteriaCategory } from "../../types/criteria";
import { CATEGORY_COLUMN_COUNT, FIXED_CATEGORIES } from "../../types/criteria";
import { CATEGORY_LABELS } from "../../utils/dashboardAggregations";
import ColumnSelect from "./ColumnSelect";

interface StepCriteriaProps {
  columns: string[];
  criteria: Criterion[];
  /** criteria_id -> one column, for single-value criteria. */
  singleMap: Record<number, string>;
  /** criteria_id -> ordered columns, for weekly criteria. */
  weeklyMap: Record<number, string[]>;
  onSingleChange: (criteriaId: number, column: string) => void;
  onWeeklyChange: (criteriaId: number, index: number, column: string) => void;
}

/** Which week number a category's first column represents. */
const CATEGORY_START_WEEK: Record<CriteriaCategory, number> = {
  attendance: 1, // weeks 1-7
  weekly_tut: 2, // weeks 2-7 — week 1 has no tutorial
  assessment: 1,
  moodle: 1,
};

/**
 * Step 3 — map spreadsheet columns to this unit's criteria.
 *
 * WEEKLY CRITERIA GET ONE DROPDOWN PER WEEK, NOT A MULTI-SELECT
 * -------------------------------------------------------------
 * Attendance needs exactly 7 values and tutorials exactly 6, and the
 * backend reads them POSITIONALLY to compute the early-vs-late trend.
 * A multi-select would capture the set but not the order, and getting
 * the order wrong produces a correct-looking percentage attached to a
 * meaningless trend.
 *
 * One labelled dropdown per week makes the order explicit and the count
 * impossible to get wrong — you cannot supply six attendance weeks when
 * there are seven boxes, and each box says which week it is.
 *
 * WHAT THIS STEP CANNOT DO YET
 * ----------------------------
 * It maps to criteria that ALREADY EXIST on the unit. Creating new ones
 * from unmapped columns is deliberately deferred until the threshold
 * model is settled — thresholds drive the rule engine and cannot be
 * chosen sensibly in passing. Until then a unit's assignment and
 * tutorial criteria are created through the API, and this step says so
 * plainly rather than pretending the columns are unmappable.
 */
export default function StepCriteria({
  columns,
  criteria,
  singleMap,
  weeklyMap,
  onSingleChange,
  onWeeklyChange,
}: StepCriteriaProps) {
  // Disabled criteria no longer contribute to a risk score, so offering
  // to import data against them would be misleading.
  const active = criteria.filter((c) => c.enabled);

  // Every column claimed by any criterion, for the "already used" flag.
  const allUsed = new Set<string>([
    ...Object.values(singleMap).filter(Boolean),
    ...Object.values(weeklyMap).flat().filter(Boolean),
  ]);

  const hasCustom = active.some(
    (c) => !c.category || !FIXED_CATEGORIES.includes(c.category),
  );

  return (
    <div className="space-y-4">
      {active.map((criterion) => {
        const category = criterion.category;
        const columnCount = category ? CATEGORY_COLUMN_COUNT[category] : null;
        const isWeekly = columnCount !== null;
        const isFixed = category ? FIXED_CATEGORIES.includes(category) : false;
        const startWeek = category ? CATEGORY_START_WEEK[category] : 1;

        return (
          <section
            key={criterion.id}
            className="rounded-lg border border-stone-200 bg-white p-5"
          >
            <header className="mb-4">
              <h3 className="flex flex-wrap items-center gap-2 text-sm font-semibold text-stone-900">
                {criterion.name}
                {isFixed && (
                  <span
                    title="Fixed for every unit — its weight and threshold come from the risk engine's constants"
                    className="inline-flex items-center gap-1 rounded bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-500"
                  >
                    <Lock className="h-2.5 w-2.5" aria-hidden="true" />
                    Fixed
                  </span>
                )}
              </h3>
              <p className="mt-0.5 text-xs text-stone-500">
                {category ? CATEGORY_LABELS[category] ?? category : "Uncategorised"}
                {isWeekly
                  ? ` · needs exactly ${columnCount} columns, in week order`
                  : ` · one column · marked out of ${criterion.max_score}`}
              </p>
            </header>

            {isWeekly ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
                {Array.from({ length: columnCount ?? 0 }, (_, index) => (
                  <ColumnSelect
                    key={index}
                    label={`Week ${startWeek + index}`}
                    value={weeklyMap[criterion.id]?.[index] ?? ""}
                    columns={columns}
                    onChange={(value) => onWeeklyChange(criterion.id, index, value)}
                    usedElsewhere={allUsed}
                  />
                ))}
              </div>
            ) : (
              <div className="max-w-sm">
                <ColumnSelect
                  label="Column"
                  hint={
                    category === "moodle"
                      ? "A raw login count, not a percentage"
                      : `Raw mark out of ${criterion.max_score}`
                  }
                  value={singleMap[criterion.id] ?? ""}
                  columns={columns}
                  onChange={(value) => onSingleChange(criterion.id, value)}
                  usedElsewhere={allUsed}
                />
              </div>
            )}

            {/* Partial weekly mappings are the silent failure mode this
                whole step is designed around, so they are called out
                per-criterion rather than only at submit. */}
            {isWeekly &&
              (() => {
                const filled = (weeklyMap[criterion.id] ?? []).filter(Boolean).length;
                if (filled === 0 || filled === columnCount) return null;
                return (
                  <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-[11px] leading-relaxed text-amber-900">
                    {filled} of {columnCount} weeks mapped. Map all {columnCount} or clear
                    them — a partial set still produces a percentage but loses the trend
                    value the momentum chart needs.
                  </p>
                );
              })()}
          </section>
        );
      })}

      {/* The consequence of deferring criteria creation, stated up front
          rather than left for the lecturer to discover. */}
      {!hasCustom && (
        <div className="flex gap-3 rounded-lg border border-dashed border-amber-300 bg-amber-50 p-4">
          <CircleAlert
            className="mt-0.5 h-4 w-4 shrink-0 text-amber-600"
            aria-hidden="true"
          />
          <div className="text-xs leading-relaxed text-amber-900">
            <p className="font-medium">
              This unit only has its two default criteria.
            </p>
            <p className="mt-1">
              Assignment and tutorial columns in your file have nothing to map to yet.
              You can still import attendance and Moodle data now — create the other
              criteria via <code className="rounded bg-amber-100 px-1">POST /units/{"{id}"}/criteria</code>{" "}
              and re-import to add them.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

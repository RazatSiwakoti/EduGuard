import { useMemo, useState } from "react";
import { CircleAlert, Info, Loader2, Lock, TriangleAlert } from "lucide-react";
import { useUnitShape, useUpdateThresholds, getThresholdErrorMessage } from "../../hooks/useUnitShape";
import ThresholdSlider from "./ThresholdSlider";
import { ADJUSTABLE_CATEGORIES } from "../../types/unitShape";
import type { CriterionShape, ThresholdUpdate } from "../../types/unitShape";
import { CATEGORY_LABELS } from "../../utils/dashboardAggregations";
import RunAnalysisButton from "../analysis/RunAnalysisButton";

interface UnitCompositionPanelProps {
  unitId: number;
}

/** The pass mark this criterion would have at a given bar. */
function passMarkAt(criterion: CriterionShape, threshold: number): number {
  return Math.round(((criterion.max_score ?? 0) * threshold) / 100 * 100) / 100;
}

/** Trims 9.20 to 9.2 and 10.00 to 10 without touching 9.25. */
function tidy(value: number): string {
  return String(Number(value.toFixed(2)));
}

/**
 * What the coordinator set, and the one number the lecturer owns.
 *
 * WHY THIS SCREEN IS MOSTLY READ-ONLY
 * -----------------------------------
 * Since section T2 a unit's composition — which assessments exist, what
 * each is worth — belongs to the coordinator, and the composition rules
 * (max 3 items, a 20% cap on quizzes, a 100% budget) are only checked
 * on their endpoint. So everything above the sliders is stated, not
 * offered: showing an editable field a lecturer's save would be refused
 * for is worse than showing none.
 *
 * The pass bar is theirs. `pass_mark = max_score × threshold ÷ 100`, so
 * the coordinator sets the scale and the lecturer draws the line
 * through it.
 *
 * WHY LOWERING THE BAR IS SPELT OUT RATHER THAN JUST ALLOWED
 * ----------------------------------------------------------
 * The intuition is that a lower bar means fewer at-risk students. It
 * does not. The bar feeds the RULE engine only; the ML model was
 * trained against fixed labels and does not move with it. Lowering the
 * bar therefore makes the two engines disagree MORE often, and the
 * hybrid layer sends a disagreement to Needs Review — not to Safe. A
 * lecturer expecting their at-risk list to shrink and finding their
 * review queue grown instead would reasonably conclude the feature is
 * broken, so the sentence is on screen before they drag anything.
 */
export default function UnitCompositionPanel({ unitId }: UnitCompositionPanelProps) {
  const { data: shape, isLoading, isError } = useUnitShape(unitId);
  const updateThresholds = useUpdateThresholds(unitId);

  // Only the sliders the lecturer has actually touched are held here.
  // Anything absent falls back to the server's value on every render,
  // so a background refetch cannot strand a slider on a stale number.
  const [draft, setDraft] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const groups = useMemo(
    () =>
      ADJUSTABLE_CATEGORIES.map((category) => shape?.thresholds?.[category]).filter(
        (group): group is NonNullable<typeof group> => Boolean(group?.adjustable),
      ),
    [shape],
  );

  if (isLoading) {
    return (
      <section className="rounded-lg border border-stone-200 bg-white p-5">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-48 rounded bg-stone-200" />
          <div className="h-24 rounded bg-stone-100" />
          <div className="h-20 rounded bg-stone-100" />
        </div>
      </section>
    );
  }

  if (isError || !shape) {
    return (
      <section className="rounded-lg border border-stone-200 bg-white p-5">
        <p className="text-sm text-stone-500">
          Couldn't load this unit's marking scheme.
        </p>
      </section>
    );
  }

  // A group whose rows disagree has no single stored value, so the
  // slider has to start somewhere. It starts at the LOWEST of them:
  // saving flattens the group, and flattening upward would raise a bar
  // a lecturer had deliberately lowered on one item.
  const valueFor = (category: string): number => {
    const group = shape.thresholds[category];
    if (draft[category] !== undefined) return draft[category];
    if (group?.value !== null && group?.value !== undefined) return group.value;
    return group?.values?.[0] ?? group?.default ?? 50;
  };

  // A MIXED group is dirty from the moment it loads, before anything is
  // touched. There is a real change waiting to be made — the rows
  // disagree and one slider governs them — and requiring the lecturer to
  // wiggle the control first would mean the only way to flatten a group
  // onto the value it already shows is to drag away from it and back.
  const dirty = groups.some(
    (group) =>
      group.mixed ||
      (draft[group.category] !== undefined && draft[group.category] !== group.value),
  );

  const handleSave = () => {
    const changes: ThresholdUpdate = {};
    for (const group of groups) {
      const touched = draft[group.category] !== undefined;
      if (!group.mixed && (!touched || draft[group.category] === group.value)) continue;
      // `valueFor` rather than `draft`: a mixed group can be saved
      // without ever being dragged, and it saves what the slider shows.
      changes[group.category as keyof ThresholdUpdate] = valueFor(group.category);
    }

    setError(null);
    setSaved(false);
    updateThresholds.mutate(changes, {
      onSuccess: () => {
        setDraft({});
        setSaved(true);
      },
      // Deliberately not a toast, matching the rest of this block. A
      // threshold refusal names a number the lecturer has to change,
      // and it has to stay on screen next to the control that produced
      // it rather than fading out while they hunt for the fix.
      onError: (mutationError) => setError(getThresholdErrorMessage(mutationError)),
    });
  };

  const items: CriterionShape[] = [
    ...shape.assessments,
    ...(shape.tutorial ? [shape.tutorial] : []),
  ];

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-stone-900">
            Marking scheme and pass marks
          </h2>
          {shape.lock.locked && (
            <span
              title={shape.lock.reasons.join(" ")}
              className="inline-flex items-center gap-1 rounded bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-500"
            >
              <Lock className="h-2.5 w-2.5" aria-hidden="true" />
              Composition locked
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs leading-relaxed text-stone-500">
          What this unit is worth is set by the unit coordinator. The pass mark
          for each category is yours.
        </p>
        </div>

        {/* Placed HERE rather than beside the import reference below it.
            Saving a pass mark tells the lecturer their results were
            computed against the old one and to re-run — so the button
            that does that has to be in the section that says it. */}
        <RunAnalysisButton unitId={unitId} label="Run analysis" variant="secondary" />
      </header>

      {!shape.configured ? (
        <div className="flex gap-3 rounded-md border border-dashed border-amber-300 bg-amber-50 p-4">
          <CircleAlert
            className="mt-0.5 h-4 w-4 shrink-0 text-amber-600"
            aria-hidden="true"
          />
          <div className="text-xs leading-relaxed text-amber-900">
            <p className="font-medium">This unit has no marking scheme yet.</p>
            <p className="mt-1">
              The unit coordinator sets the assessments and what each is worth.
              Until they do, this unit can only accept attendance and Moodle
              data, and there is no pass mark to adjust.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* "Marked out of" is the column that goes at a phone width,
              and it is the right one to lose: the pass mark is what a
              lecturer came here for, and the scale it is out of is
              repeated in full on every slider preview line below
              ("Quiz 1 - pass at 9.2 / 20"). Scrolling the table
              sideways instead would push the pass mark off screen
              entirely, with nothing to say it was there. */}
          <table className="w-full text-sm">
            <caption className="sr-only">
              Assessments in {shape.unit_code} and their pass marks
            </caption>
            <thead>
              <tr className="border-b border-stone-200 text-left text-xs font-medium text-stone-500">
                <th scope="col" className="pb-2">
                  Component
                </th>
                <th scope="col" className="pb-2 text-right">
                  Worth
                </th>
                <th scope="col" className="hidden pb-2 text-right sm:table-cell">
                  Marked out of
                </th>
                <th scope="col" className="pb-2 text-right">
                  Pass mark
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {items.map((criterion) => (
                <tr key={`${criterion.category}-${criterion.id}`}>
                  <td className="py-2.5">
                    <span className="font-medium text-stone-900">
                      {criterion.name}
                    </span>
                    {criterion.kind && (
                      <span className="ml-2 rounded bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-500">
                        {criterion.kind}
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 text-right tabular-nums text-stone-600">
                    {criterion.percentage}%
                  </td>
                  {/* The tutorial's max_score is 100 because its stored
                      score is already a completion percentage, not a
                      raw mark — so it is labelled, not left to read as
                      "marked out of 100". */}
                  <td className="hidden py-2.5 text-right tabular-nums text-stone-600 sm:table-cell">
                    {criterion.category === "weekly_tut"
                      ? "% completed"
                      : criterion.max_score}
                  </td>
                  <td className="py-2.5 text-right tabular-nums text-stone-900">
                    {criterion.pass_mark === null
                      ? "—"
                      : criterion.category === "weekly_tut"
                        ? `${tidy(criterion.pass_mark)}%`
                        : tidy(criterion.pass_mark)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-stone-200 text-xs text-stone-500">
                <td className="pt-2">
                  {shape.remaining_percentage > 0
                    ? `${shape.remaining_percentage}% of the unit is not accounted for here`
                    : "The unit is fully accounted for"}
                </td>
                <td className="pt-2 text-right font-medium tabular-nums text-stone-700">
                  {shape.total_percentage}%
                </td>
                <td className="hidden sm:table-cell" />
                <td />
              </tr>
            </tfoot>
          </table>

          {/* Stated in one line rather than given four table rows.
              Attendance and Moodle are scored for every unit, sit
              outside the 100%, and their thresholds are system
              constants — a slider for them would be a control
              guaranteed to be refused. */}
          <p className="mt-3 flex gap-2 text-xs leading-relaxed text-stone-500">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-400" aria-hidden="true" />
            <span>
              Attendance and Moodle activity are scored automatically for every
              unit, sit outside this 100%, and their pass marks are fixed by the
              risk engine.
            </span>
          </p>

          <div className="mt-6 border-t border-stone-200 pt-5">
            <h3 className="text-sm font-semibold text-stone-900">Pass marks</h3>

            <div className="mt-2 flex gap-2 rounded-md border border-stone-200 bg-stone-50 p-3">
              <TriangleAlert
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-500"
                aria-hidden="true"
              />
              <p className="text-xs leading-relaxed text-stone-600">
                <span className="font-medium text-stone-800">
                  Lowering a pass mark does not shorten your at-risk list.
                </span>{" "}
                It makes the rule engine kinder, but the ML model does not move
                with it — so the two disagree more often, and every student they
                disagree about goes to <strong>Needs Review</strong>, not to
                Safe. Your review queue grows; the at-risk list does not clear.
              </p>
            </div>

            {groups.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">
                There is nothing to adjust yet — this unit has no assessments or
                weekly tutorials.
              </p>
            ) : (
              <>
                <div className="mt-3 space-y-3">
                  {groups.map((group) => {
                    const value = valueFor(group.category);
                    const affected = items.filter(
                      (criterion) => criterion.category === group.category,
                    );
                    return (
                      <ThresholdSlider
                        key={group.category}
                        group={group}
                        label={CATEGORY_LABELS[group.category] ?? group.category}
                        value={value}
                        mixedUntouched={
                          group.mixed && draft[group.category] === undefined
                        }
                        disabled={updateThresholds.isPending}
                        onChange={(next) => {
                          setSaved(false);
                          setError(null);
                          setDraft((previous) => ({
                            ...previous,
                            [group.category]: next,
                          }));
                        }}
                        preview={affected.map((criterion) =>
                          criterion.category === "weekly_tut"
                            ? `${criterion.name} — pass at ${tidy(value)}% completed`
                            : `${criterion.name} — pass at ${tidy(
                                passMarkAt(criterion, value),
                              )} / ${criterion.max_score}`,
                        )}
                      />
                    );
                  })}
                </div>

                {error && (
                  <p
                    role="alert"
                    className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs leading-relaxed text-red-800"
                  >
                    {error}
                  </p>
                )}

                {saved && !dirty && (
                  <p className="mt-3 rounded border border-green-200 bg-green-50 px-3 py-2 text-xs leading-relaxed text-green-800">
                    Pass marks saved. Every risk result for this unit was
                    computed against the old ones — run the analysis again to
                    bring them up to date.
                  </p>
                )}

                <div className="mt-4 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={!dirty || updateThresholds.isPending}
                    className="inline-flex items-center gap-2 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-300"
                  >
                    {updateThresholds.isPending && (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    )}
                    Save pass marks
                  </button>
                  {dirty && !updateThresholds.isPending && (
                    <button
                      type="button"
                      onClick={() => {
                        setDraft({});
                        setError(null);
                      }}
                      className="text-sm text-stone-500 transition hover:text-stone-900"
                    >
                      Discard
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        </>
      )}
    </section>
  );
}